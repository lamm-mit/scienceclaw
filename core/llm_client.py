"""
Unified LLM Client for ScienceClaw

Supports multiple LLM backends:
- Anthropic API (default) - direct Claude API calls
- OpenAI API - direct GPT API calls
- Hugging Face - models via Hugging Face Inference API or local deployment

Configuration via environment variables or config file:
- LLM_BACKEND: openai (default), anthropic, huggingface
- OPENAI_API_KEY: for OpenAI backend (default)
- ANTHROPIC_API_KEY: for Anthropic backend
- OPENAI_API_KEY: for OpenAI backend
- HF_API_KEY or HUGGINGFACE_API_KEY: for Hugging Face backend
- HF_MODEL: Hugging Face model ID
- HF_ENDPOINT: Optional custom endpoint for self-hosted models
- LLM_TIMEOUT: Timeout in seconds for LLM calls (default: 180 for HF, 60 for others)
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path


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
            backend: LLM backend to use (openai, anthropic, huggingface)
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
        elif self.backend == "huggingface":
            self._init_huggingface()
        elif self.backend == "openclaw":
            raise ValueError(
                "OpenClaw backend has been removed. "
                "Set LLM_BACKEND=anthropic (or openai/huggingface) and provide the corresponding API key."
            )
    
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
        self.anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        
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
            self.openai_client = openai.OpenAI(api_key=self.openai_key)
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
        if self.backend == "anthropic":
            return self._call_anthropic(prompt, max_tokens, temperature)
        elif self.backend == "openai":
            return self._call_openai(prompt, max_tokens, temperature)
        elif self.backend == "huggingface":
            return self._call_huggingface(prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
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
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
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
        backend: LLM backend (anthropic, openai, huggingface)
        
    Returns:
        LLMClient instance
    """
    global _client
    if _client is None or _client.agent_name != agent_name or (backend and _client.backend != backend):
        _client = LLMClient(agent_name=agent_name, backend=backend)
    return _client
