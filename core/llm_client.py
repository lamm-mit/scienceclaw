"""
Unified LLM Client for ScienceClaw

Supports multiple LLM backends:
- Anthropic API (default) - direct Claude API calls
- OpenAI API - direct GPT API calls
- Hugging Face - models via Hugging Face Inference API or local deployment
- Gemini (Google AI Studio) - via Gemini's OpenAI-compatible endpoint; free tier works

Configuration via environment variables or config file:
- LLM_BACKEND: openai (default), anthropic, gemini, huggingface
- OPENAI_API_KEY: for OpenAI backend (default)
- ANTHROPIC_API_KEY: for Anthropic backend
- GEMINI_API_KEY (or GOOGLE_API_KEY): for Gemini backend
- GEMINI_MODEL: Gemini model ID (default: gemini-3.6-flash)
- GEMINI_REASONING_EFFORT: low (default) | medium | high — caps "thinking" tokens
- GEMINI_THINKING_HEADROOM: extra output tokens reserved for Gemini thinking (default: 4096)
- HF_API_KEY or HUGGINGFACE_API_KEY: for Hugging Face backend
- HF_MODEL: Hugging Face model ID
- HF_ENDPOINT: Optional custom endpoint for self-hosted models
- LLM_TIMEOUT: Timeout in seconds for LLM calls (default: 180 for HF, 60 for others)
"""

import os
import json
import re
from typing import Optional, Dict, Any
from pathlib import Path


# Gemini's OpenAI-compatible endpoint (Google AI Studio keys)
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"

# Gemini-specific system prompt. Gemini models tend to wrap structured output in
# markdown fences and add preamble; ScienceClaw's callers parse raw JSON/sections,
# so steer the model toward the exact requested format.
GEMINI_SYSTEM_PROMPT = (
    "You are the reasoning engine of ScienceClaw, an autonomous scientific research agent. "
    "Follow the user's requested output format exactly. When asked for JSON, return only "
    "valid JSON with no markdown code fences and no commentary before or after it. "
    "When asked for prose or sections, return them directly without preamble. "
    "Be specific, quantitative, and cite concrete evidence from the provided context."
)


class LLMClient:
    """
    Unified client for calling LLMs from multiple backends.
    
    Usage:
        client = LLMClient(agent_name="MyAgent")
        response = client.call(prompt="What is 2+2?", max_tokens=100)
    """
    
    def __init__(self, agent_name: str = "Agent", backend: Optional[str] = None):
        """
        Initialize LLM client.
        
        Args:
            agent_name: Name of the agent (for session tracking)
            backend: LLM backend to use (openai, anthropic, gemini, huggingface)
                    If None, reads from LLM_BACKEND env var or defaults to openai
        """
        self.agent_name = agent_name
        self.backend = backend or os.environ.get("LLM_BACKEND", "openai")
        
        # Load configuration
        self._load_config()
        
        # Initialize backend-specific clients
        if self.backend == "anthropic":
            self._init_anthropic()
        elif self.backend == "openai":
            self._init_openai()
        elif self.backend == "gemini":
            self._init_gemini()
        elif self.backend == "huggingface":
            self._init_huggingface()
    
    def _load_config(self):
        """Load configuration from environment or config file."""
        # API keys
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.hf_key = os.environ.get("HF_API_KEY") or os.environ.get("HUGGINGFACE_API_KEY")
        
        # Hugging Face specific
        self.hf_model = os.environ.get("HF_MODEL", "moonshotai/Kimi-K2.5")
        self.hf_endpoint = os.environ.get("HF_ENDPOINT")  # For self-hosted models
        
        # Model names for each backend
        self.anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
        # Optional base URL override for local/compatible servers (e.g. vLLM)
        self.openai_base_url = os.environ.get("OPENAI_BASE_URL")

        # Gemini (Google AI Studio) via the OpenAI-compatible endpoint.
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.gemini_model = os.environ.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)
        self.gemini_base_url = os.environ.get("GEMINI_BASE_URL", GEMINI_OPENAI_BASE_URL)
        # Gemini "thinking" tokens count against max_tokens: a small max_tokens yields an
        # empty answer (finish_reason=length, content=None). Reserve headroom for thinking
        # and cap reasoning effort to keep free-tier quota usage low.
        # reasoning_effort: low | medium | high (Gemini rejects "none"); "" disables the param.
        self.gemini_reasoning_effort = os.environ.get("GEMINI_REASONING_EFFORT", "low")
        self.gemini_thinking_headroom = int(os.environ.get("GEMINI_THINKING_HEADROOM", "4096"))
        self.gemini_max_retries = int(os.environ.get("GEMINI_MAX_RETRIES", "4"))
        self.gemini_system_prompt = os.environ.get("GEMINI_SYSTEM_PROMPT", GEMINI_SYSTEM_PROMPT)
        
        # Timeout (seconds) - loose defaults for slow models like Kimi-K2.5
        timeout_env = os.environ.get("LLM_TIMEOUT")
        self.timeout = int(timeout_env) if timeout_env else 180  # 3 min default
        
        # Try loading from config file
        config_file = Path.home() / ".scienceclaw" / "llm_config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                    self.backend = config.get("backend", self.backend)
                    self.anthropic_key = config.get("anthropic_api_key", self.anthropic_key)
                    self.openai_key = config.get("openai_api_key", self.openai_key)
                    self.hf_key = config.get("hf_api_key", self.hf_key)
                    self.hf_model = config.get("hf_model", self.hf_model)
                    self.hf_endpoint = config.get("hf_endpoint", self.hf_endpoint)
                    self.anthropic_model = config.get("anthropic_model", self.anthropic_model)
                    self.openai_model = config.get("openai_model", self.openai_model)
                    self.openai_base_url = config.get("openai_base_url", self.openai_base_url)
                    self.gemini_key = config.get("gemini_api_key", self.gemini_key)
                    self.gemini_model = config.get("gemini_model", self.gemini_model)
                    self.gemini_base_url = config.get("gemini_base_url", self.gemini_base_url)
                    self.gemini_reasoning_effort = config.get("gemini_reasoning_effort", self.gemini_reasoning_effort)
                    self.gemini_system_prompt = config.get("gemini_system_prompt", self.gemini_system_prompt)
                    if "gemini_thinking_headroom" in config:
                        self.gemini_thinking_headroom = int(config["gemini_thinking_headroom"])
                    if "gemini_max_retries" in config:
                        self.gemini_max_retries = int(config["gemini_max_retries"])
                    if "timeout" in config:
                        self.timeout = int(config["timeout"])
            except Exception:
                pass  # Use env vars
    
    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            if not self.anthropic_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            if not self.openai_key:
                raise ValueError("OPENAI_API_KEY not set")
            kwargs = {"api_key": self.openai_key}
            if self.openai_base_url:
                kwargs["base_url"] = self.openai_base_url
            self.openai_client = openai.OpenAI(**kwargs)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _init_gemini(self):
        """Initialize Gemini client (OpenAI-compatible endpoint, so no extra dependency)."""
        try:
            import openai
            if not self.gemini_key:
                raise ValueError(
                    "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey"
                )
            self.gemini_client = openai.OpenAI(
                api_key=self.gemini_key,
                base_url=self.gemini_base_url,
                timeout=self.timeout,
                max_retries=0,  # we handle rate-limit retries ourselves (free-tier friendly)
            )
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def _init_huggingface(self):
        """Initialize Hugging Face client."""
        try:
            from huggingface_hub import InferenceClient
            
            # Loose timeout for slow models like Kimi-K2.5
            hf_timeout = self.timeout
            # Use custom endpoint if provided, otherwise use HF Inference API
            if self.hf_endpoint:
                self.hf_client = InferenceClient(base_url=self.hf_endpoint, timeout=hf_timeout)
            else:
                if not self.hf_key:
                    print("Warning: HF_API_KEY not set. Using public Inference API (rate limited).")
                self.hf_client = InferenceClient(
                    model=self.hf_model,
                    token=self.hf_key,
                    timeout=hf_timeout
                )
        except ImportError:
            raise ImportError("huggingface_hub package not installed. Run: pip install huggingface_hub")
    
    def call(self,
             prompt: str,
             max_tokens: int = 1000,
             temperature: float = 1.0,
             timeout: Optional[int] = None,
             session_id: Optional[str] = None) -> str:
        """
        Call the LLM with a prompt.

        If Coherence Shield is enabled, routes through the Shield proxy
        for hallucination filtering and PQC attestation of responses.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            timeout: Timeout in seconds
            session_id: Optional session ID for tracking

        Returns:
            LLM response text
        """
        t = timeout if timeout is not None else self.timeout

        # Coherence Shield: route through Paraxiom's trust proxy if enabled
        if self._coherence_shield_enabled():
            result = self._call_coherence_shield(prompt, max_tokens, temperature)
            if result is not None:
                return result
            # Fall through to direct call if Shield is unavailable

        if self.backend == "anthropic":
            return self._call_anthropic(prompt, max_tokens, temperature)
        elif self.backend == "openai":
            return self._call_openai(prompt, max_tokens, temperature)
        elif self.backend == "gemini":
            return self._call_gemini(prompt, max_tokens, temperature)
        elif self.backend == "huggingface":
            return self._call_huggingface(prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _coherence_shield_enabled(self) -> bool:
        """Check if Coherence Shield proxy is configured."""
        try:
            from paraxiom_trust.config import ParaxiomTrustConfig
            config = ParaxiomTrustConfig.load()
            return config.coherence_shield_enabled
        except Exception:
            return False

    def _call_coherence_shield(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """
        Route LLM call through Paraxiom Coherence Shield.

        The Shield is an OpenAI-compatible proxy that:
        1. Applies toroidal logit bias to reduce hallucination
        2. Attests every response with PQC signatures
        3. Logs the interaction for audit

        Falls back to None if Shield is unavailable.
        """
        try:
            from paraxiom_trust.config import ParaxiomTrustConfig
            config = ParaxiomTrustConfig.load()
            shield_url = config.coherence_shield_url

            import openai
            shield_client = openai.OpenAI(
                api_key=self.openai_key or self.anthropic_key or self.gemini_key or "shield-local",
                base_url=f"{shield_url}/shield/v1",
            )

            response = shield_client.chat.completions.create(
                model=self.openai_model if self.backend == "openai" else "coherence-shield",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content or ""
            if text:
                return text
            return None
        except Exception as e:
            # Shield unavailable — fall through to direct call
            if os.environ.get("DEBUG_LLM_TOPIC"):
                print(f"    [DEBUG] Coherence Shield unavailable: {e}")
            return None
    
    def _call_anthropic(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Call Anthropic Claude API."""
        try:
            message = self.anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return ""
    
    def _call_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Call OpenAI GPT API."""
        def _wants_max_completion_tokens(model: str) -> bool:
            m = (model or "").strip().lower()
            # GPT-5 family (and some newer models) use `max_completion_tokens`.
            if m.startswith("gpt-5"):
                return True
            # Be conservative: some "o*" models also moved parameters.
            if re.match(r"^o\\d", m):
                return True
            return False

        def _extract_text(resp) -> str:
            try:
                return resp.choices[0].message.content or ""
            except Exception:
                return ""

        base_kwargs = {
            "model": self.openai_model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        # First attempt: pick the parameter by model family.
        try:
            kwargs = dict(base_kwargs)
            if _wants_max_completion_tokens(self.openai_model):
                kwargs["max_completion_tokens"] = int(max_tokens)
            else:
                kwargs["max_tokens"] = int(max_tokens)
            response = self.openai_client.chat.completions.create(**kwargs)
            return _extract_text(response)
        except Exception as e:
            msg = str(e)
            # Retry on the specific mismatch error seen with newer models.
            try:
                if "max_tokens" in msg and "max_completion_tokens" in msg:
                    kwargs = dict(base_kwargs)
                    kwargs["max_completion_tokens"] = int(max_tokens)
                    response = self.openai_client.chat.completions.create(**kwargs)
                    return _extract_text(response)
            except Exception:
                pass
            print(f"OpenAI API error: {e}")
            return ""
    
    # ── Gemini ───────────────────────────────────────────────────────────────

    @staticmethod
    def _gemini_retry_delay(err_msg: str, attempt: int) -> float:
        """Pick a backoff delay for a Gemini 429, honouring the server's hint if present."""
        m = re.search(r"retry(?:Delay|\s+in)[\"':\s]*([0-9.]+)\s*s", err_msg, re.IGNORECASE)
        if m:
            try:
                return min(float(m.group(1)) + 1.0, 120.0)
            except ValueError:
                pass
        return float(min(10 * (2 ** attempt), 90))

    @staticmethod
    def _strip_wrapping_code_fence(text: str) -> str:
        """If the whole response is a single ```lang ... ``` block, unwrap it."""
        stripped = text.strip()
        m = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(.*)\n```$", stripped, re.DOTALL)
        return m.group(1).strip() if m else text

    def _call_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Call Gemini through its OpenAI-compatible endpoint with Gemini-specific handling:

        - Prepends a system prompt steering Gemini to the exact requested format.
        - Adds thinking headroom to max_tokens (Gemini bills thinking tokens against
          max_tokens; too small a budget yields finish_reason=length and empty content).
        - Caps reasoning effort (default "low") to conserve free-tier quota.
        - Retries empty/truncated responses with a larger budget, and 429 rate limits
          with backoff — the free tier is ~10-15 requests/min.
        - Unwraps a response that is entirely a markdown code fence.
        """
        import time

        messages = []
        if self.gemini_system_prompt:
            messages.append({"role": "system", "content": self.gemini_system_prompt})
        messages.append({"role": "user", "content": prompt})

        reasoning_effort = (self.gemini_reasoning_effort or "").strip().lower() or None
        headroom = max(0, int(self.gemini_thinking_headroom))
        budget = int(max_tokens) + headroom
        debug = bool(os.environ.get("DEBUG_LLM_TOPIC"))

        attempt = 0
        last_error = None
        while attempt <= self.gemini_max_retries:
            kwargs: Dict[str, Any] = {
                "model": self.gemini_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": budget,
            }
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            try:
                response = self.gemini_client.chat.completions.create(**kwargs)
                choice = response.choices[0] if response.choices else None
                text = (choice.message.content if choice and choice.message else None) or ""
                finish = getattr(choice, "finish_reason", None) if choice else None
                if text.strip():
                    return self._strip_wrapping_code_fence(text)
                # Empty answer: thinking consumed the budget — grow it and retry.
                if finish == "length" and attempt < self.gemini_max_retries:
                    budget = budget * 2 if budget else 2048
                    if debug:
                        print(f"    [DEBUG] Gemini returned empty content (finish_reason=length); "
                              f"retrying with max_tokens={budget}")
                    attempt += 1
                    continue
                if debug:
                    print(f"    [DEBUG] Gemini returned empty content (finish_reason={finish})")
                return ""
            except Exception as e:
                last_error = e
                msg = str(e)
                status = getattr(e, "status_code", None)
                is_rate_limit = status == 429 or "RESOURCE_EXHAUSTED" in msg or "429" in msg[:40]
                # 503 "high demand" / UNAVAILABLE is transient on the free tier — treat like a rate limit
                is_unavailable = status in (502, 503, 504) or "UNAVAILABLE" in msg or "high demand" in msg
                is_bad_request = status == 400 or "INVALID_ARGUMENT" in msg
                if (is_rate_limit or is_unavailable) and attempt < self.gemini_max_retries:
                    delay = self._gemini_retry_delay(msg, attempt)
                    why = "rate limit hit (free tier)" if is_rate_limit else "temporarily unavailable (high demand)"
                    print(f"Gemini {why}; retrying in {delay:.0f}s "
                          f"(attempt {attempt + 1}/{self.gemini_max_retries})...")
                    time.sleep(delay)
                    attempt += 1
                    continue
                if is_bad_request and reasoning_effort and attempt < self.gemini_max_retries:
                    # Some Gemini models reject reasoning_effort values — retry without it.
                    if debug:
                        print(f"    [DEBUG] Gemini rejected reasoning_effort={reasoning_effort}; retrying without it")
                    reasoning_effort = None
                    attempt += 1
                    continue
                break
        print(f"Gemini API error: {last_error}")
        return ""

    def _call_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Call Hugging Face models using the most general syntax.
        
        Strategy:
        - Prefer `text_generation`, which works for most HF models.
        - If that fails with a task error, fall back to `chat_completion`
          for chat-style models that support it.
        """
        try:
            # 1) Try generic text generation first (most widely supported)
            try:
                response = self.hf_client.text_generation(
                    prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    return_full_text=False,
                )
                return str(response) if response else ""
            except ValueError as ve:
                # Model doesn't support text_generation; try chat_completion
                if "not supported for task" not in str(ve):
                    raise
                if os.environ.get("DEBUG_LLM_TOPIC"):
                    print("    [DEBUG] HF text_generation not supported for this model, trying chat_completion...")

            # 2) Fallback: chat_completion for chat/instruct models
            try:
                response = self.hf_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = None
                if hasattr(response, "choices") and len(response.choices) > 0:
                    content = response.choices[0].message.content
                elif isinstance(response, dict) and "choices" in response:
                    content = response["choices"][0]["message"]["content"]
                else:
                    content = str(response) if response else ""
                if content is None or (isinstance(content, str) and not content.strip()):
                    if os.environ.get("DEBUG_LLM_TOPIC"):
                        print("    [DEBUG] Hugging Face returned empty content in chat_completion.")
                return content or ""
            except Exception as inner_e:
                # If chat_completion also fails, surface a single clear error
                if os.environ.get("DEBUG_LLM_TOPIC"):
                    print(f"    [DEBUG] HF chat_completion failed: {inner_e}")
                raise
        except Exception as e:
            print(f"Hugging Face API error: {e}")
            return ""


# Global client instance (lazy initialization)
_client: Optional[LLMClient] = None


def get_llm_client(agent_name: str = "Agent", backend: Optional[str] = None) -> LLMClient:
    """
    Get or create the global LLM client.
    
    Args:
        agent_name: Name of the agent
        backend: LLM backend (anthropic, openai, gemini, huggingface)
        
    Returns:
        LLMClient instance
    """
    global _client
    if _client is None or _client.agent_name != agent_name or (backend and _client.backend != backend):
        _client = LLMClient(agent_name=agent_name, backend=backend)
    return _client
