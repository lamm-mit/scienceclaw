#!/usr/bin/env python3
"""
Post-Investigation Plot Agent

Inspired by the Sparks documentation.py approach (lamm-mit/Sparks):
  - LLM analyzes investigation results and decides what plots to generate
  - LLM writes matplotlib/seaborn Python code for each figure
  - Code is executed in a subprocess sandbox
  - Errors trigger a fix loop (up to MAX_FIX_ATTEMPTS)
  - A review pass proposes and applies improvements
  - Returns final list of saved figure paths

Usage (standalone):
    from autonomous.plot_agent import PlotAgent
    agent = PlotAgent(agent_name="CrazyChem")
    figures = agent.generate_figures(topic, investigation_results)

Usage (integrated — called automatically by run_deep_investigation):
    The function run_deep_investigation() appends figures to the
    returned content dict under the "figures" key.
"""

import json
import os
import re
import sys
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Prompt templates  (Sparks-style: system + user for each phase)
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
You are an expert scientific data visualisation specialist embedded in an \
autonomous AI research agent. Your role is to study the raw investigation \
results produced by a multi-tool scientific investigation and design a \
precise, information-rich figure suite that would belong in a high-impact \
peer-reviewed paper.

Rules:
- Propose 2–5 distinct figures. Each figure should illuminate a different \
  aspect of the data (temporal trends, property distributions, ADMET \
  predictions, protein annotations, comparative rankings, etc.).
- Only propose a figure if the data to support it is actually present in \
  the investigation results supplied.
- Be specific: name the exact data fields (e.g. papers[].year, \
  compounds[].molecular_weight, computational.predictions[].result) that \
  each figure will use.
- Output valid JSON only — no prose outside the JSON block.
"""

PLANNER_PROMPT = """\
Investigation topic: {topic}

Investigation results (JSON):
{results_json}

Design a figure suite for these results. Return a JSON array where each \
element is an object with:
  "figure_id"   : short snake_case identifier  (e.g. "pub_timeline")
  "title"       : descriptive plot title
  "plot_type"   : one of bar | line | scatter | histogram | heatmap | radar | pie
  "description" : one sentence explaining the scientific insight this figure conveys
  "data_fields" : list of dot-paths into the results JSON used as data sources
  "x_label"     : x-axis label (if applicable, else null)
  "y_label"     : y-axis label (if applicable, else null)

Return only the JSON array, nothing else.
"""

CODER_SYSTEM = """\
You are a scientific Python programmer. You write clean, self-contained \
matplotlib/seaborn scripts that generate publication-quality figures and \
save them to disk.

Rules:
- The script must be completely self-contained (no external data files).
- All data is hard-coded from the investigation results provided to you.
- Save the figure to the exact path stored in the variable OUTPUT_PATH.
- Use matplotlib with a clean style (prefer seaborn-v0_8-whitegrid or \
  ggplot; fall back to default if unavailable).
- Set figure DPI ≥ 150 and tight_layout().
- Do NOT call plt.show().
- Print "SAVED: <path>" to stdout when the file is written successfully.
- Handle the case where the dataset is too small (< 2 data points) by \
  printing "SKIP: insufficient data" and exiting with code 0.
- Output only the Python script — no markdown fences, no explanations.
"""

CODER_PROMPT = """\
Generate a Python script that produces the following figure and saves it to \
the path contained in the variable  OUTPUT_PATH = "{output_path}".

Figure specification:
{figure_spec_json}

Investigation data available for this figure:
{data_subset_json}

Full investigation results (for additional context if needed):
{results_json}

Write the complete, runnable Python script now.
"""

REVIEWER_SYSTEM = """\
You are a critical scientific figure reviewer. Examine the Python plotting \
script and identify any correctness issues, misleading representations, or \
missed opportunities to improve scientific clarity. Be concise and \
actionable.
"""

REVIEWER_PROMPT = """\
Review the following plotting script for figure "{figure_id}".

Script:
{script}

Identify up to 3 specific improvements (axis labels, colour encoding, \
annotations, regression lines, error bars, etc.) and rewrite the improved \
script in full. Output only the improved Python script — no prose.
"""

FIX_SYSTEM = """\
You are a Python debugging expert. Fix the provided script so it runs \
without errors. Output only the corrected Python script, no explanations.
"""

FIX_PROMPT = """\
The following Python script raised an error when executed.

Script:
{script}

Error output:
{error}

Provide the corrected script that saves the figure to OUTPUT_PATH = \
"{output_path}". Output only the corrected Python script.
"""

# ---------------------------------------------------------------------------
# PlotAgent
# ---------------------------------------------------------------------------

MAX_FIX_ATTEMPTS = 3
SCRIPT_TIMEOUT = 45  # seconds per figure script


class PlotAgent:
    """
    Generates a publication-quality figure suite after a deep investigation.

    Workflow (Sparks-inspired):
      1. PLAN  – LLM decides which figures are warranted by the data
      2. CODE  – LLM writes a standalone matplotlib script per figure
      3. RUN   – Execute script in subprocess sandbox
      4. FIX   – On error, ask LLM to fix (up to MAX_FIX_ATTEMPTS)
      5. REVIEW– LLM reviews and rewrites the working script for quality
      6. RUN   – Execute improved script; keep whichever file was saved
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.scienceclaw_dir = Path(__file__).parent.parent
        self.figures_dir = Path.home() / ".scienceclaw" / "figures"
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_figures(
        self,
        topic: str,
        investigation_results: Dict,
        max_figures: int = 5,
    ) -> List[str]:
        """
        Main entry point.  Returns list of absolute paths to saved PNG files.
        """
        print("  🎨 PlotAgent: designing figure suite…")
        figure_specs = self._plan_figures(topic, investigation_results)
        if not figure_specs:
            print("  🎨 PlotAgent: no figures planned (insufficient data)")
            return []

        figure_specs = figure_specs[:max_figures]
        print(f"  🎨 PlotAgent: {len(figure_specs)} figures planned")

        saved_paths: List[str] = []
        ts = int(time.time())
        topic_slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]

        for spec in figure_specs:
            fig_id = spec.get("figure_id", f"figure_{len(saved_paths)}")
            out_path = str(
                self.figures_dir / f"{topic_slug}_{ts}_{fig_id}.png"
            )
            print(f"    📊 Generating: {fig_id} → {Path(out_path).name}")
            path = self._generate_one_figure(
                spec, investigation_results, out_path
            )
            if path:
                saved_paths.append(path)
                print(f"    ✅ Saved: {path}")
            else:
                print(f"    ⚠️  Skipped: {fig_id}")

        print(
            f"  🎨 PlotAgent: {len(saved_paths)}/{len(figure_specs)} figures saved"
        )
        return saved_paths

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        system_msg: str,
        user_msg: str,
        max_tokens: int = 2000,
        session_id: Optional[str] = None,
    ) -> str:
        """Call LLM via the shared client used by the rest of the stack."""
        try:
            from core.llm_client import get_llm_client

            client = get_llm_client(agent_name=self.agent_name)
            prompt = f"SYSTEM:\n{system_msg}\n\nUSER:\n{user_msg}"
            sid = session_id or f"plot_agent_{self.agent_name}"
            return client.call(prompt=prompt, max_tokens=max_tokens, session_id=sid)
        except Exception as e:
            print(f"    ⚠️  LLM unavailable ({e})")
            return ""

    def _plan_figures(
        self, topic: str, investigation_results: Dict
    ) -> List[Dict]:
        """Ask the LLM which figures the data supports."""
        # Trim results to avoid huge context
        slim = self._slim_results(investigation_results)
        results_json = json.dumps(slim, indent=2)[:6000]

        prompt = PLANNER_PROMPT.format(
            topic=topic, results_json=results_json
        )
        raw = self._call_llm(
            PLANNER_SYSTEM, prompt, max_tokens=1200, session_id="plot_planner"
        )
        if not raw:
            return []

        # Extract JSON array from response
        try:
            # Strip any markdown fences
            clean = re.sub(r"```[a-z]*\n?", "", raw).strip()
            specs = json.loads(clean)
            if isinstance(specs, list):
                return specs
        except json.JSONDecodeError:
            # Try to find array inside response
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        return []

    def _generate_one_figure(
        self,
        spec: Dict,
        investigation_results: Dict,
        out_path: str,
    ) -> Optional[str]:
        """Generate, execute, fix, and review a single figure. Returns path or None."""
        data_subset = self._extract_data_subset(spec, investigation_results)
        script = self._write_script(spec, data_subset, investigation_results, out_path)
        if not script:
            return None

        # Execute → fix loop
        script, success = self._execute_with_fix_loop(script, out_path, spec)
        if not success:
            return None

        # Review pass (best-effort)
        improved = self._review_script(spec, script, out_path)
        if improved and improved != script:
            _, review_ok = self._execute_with_fix_loop(
                improved, out_path, spec, max_attempts=1
            )
            if not review_ok:
                pass  # Keep the original successful version

        return out_path if Path(out_path).exists() else None

    def _write_script(
        self,
        spec: Dict,
        data_subset: Dict,
        investigation_results: Dict,
        out_path: str,
    ) -> str:
        """Ask LLM to write a matplotlib script for one figure."""
        slim = self._slim_results(investigation_results)
        prompt = CODER_PROMPT.format(
            output_path=out_path,
            figure_spec_json=json.dumps(spec, indent=2),
            data_subset_json=json.dumps(data_subset, indent=2)[:3000],
            results_json=json.dumps(slim, indent=2)[:4000],
        )
        return self._call_llm(
            CODER_SYSTEM, prompt, max_tokens=2000, session_id="plot_coder"
        )

    def _execute_with_fix_loop(
        self,
        script: str,
        out_path: str,
        spec: Dict,
        max_attempts: int = MAX_FIX_ATTEMPTS,
    ):
        """Try to execute script; on error ask LLM to fix. Returns (final_script, success)."""
        current_script = script
        for attempt in range(max_attempts):
            ok, error = self._run_script(current_script, out_path)
            if ok:
                return current_script, True
            if attempt < max_attempts - 1:
                print(
                    f"      🔧 Fix attempt {attempt + 1}/{max_attempts - 1}…"
                )
                fixed = self._fix_script(current_script, error, out_path)
                if fixed:
                    current_script = fixed
        return current_script, False

    def _review_script(self, spec: Dict, script: str, out_path: str) -> str:
        """Ask LLM to review and improve the script."""
        prompt = REVIEWER_PROMPT.format(
            figure_id=spec.get("figure_id", "figure"),
            script=script,
        )
        return self._call_llm(
            REVIEWER_SYSTEM,
            prompt,
            max_tokens=2000,
            session_id="plot_reviewer",
        )

    def _fix_script(self, script: str, error: str, out_path: str) -> str:
        """Ask LLM to fix a broken script."""
        prompt = FIX_PROMPT.format(
            script=script, error=error[:1500], output_path=out_path
        )
        return self._call_llm(
            FIX_SYSTEM, prompt, max_tokens=2000, session_id="plot_fixer"
        )

    def _run_script(self, script: str, out_path: str) -> tuple:
        """
        Execute a Python script in a subprocess.
        Returns (success: bool, error_output: str).
        """
        # Strip markdown fences if LLM wrapped the code
        code = re.sub(r"^```[a-z]*\n?|```$", "", script.strip(), flags=re.MULTILINE)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="plotagent_"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            env = os.environ.copy()
            env["MPLBACKEND"] = "Agg"  # Non-interactive backend

            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=SCRIPT_TIMEOUT,
                cwd=str(self.scienceclaw_dir),
                env=env,
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if "SKIP:" in stdout:
                return True, ""  # Graceful skip counts as success

            if result.returncode == 0 and Path(out_path).exists():
                return True, ""

            error = stderr or stdout or f"returncode={result.returncode}"
            return False, error

        except subprocess.TimeoutExpired:
            return False, f"Script timed out after {SCRIPT_TIMEOUT}s"
        except Exception as e:
            return False, str(e)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _slim_results(self, results: Dict) -> Dict:
        """Return a trimmed version of results to keep prompts manageable."""
        slim = {}
        for key in ("topic", "tools_used", "insights"):
            if key in results:
                slim[key] = results[key]

        if "papers" in results:
            slim["papers"] = [
                {k: v for k, v in p.items() if k in ("title", "year", "pubdate", "pub_year", "pmid", "journal", "source")}
                for p in results["papers"][:15]
            ]

        if "proteins" in results:
            slim["proteins"] = [
                {k: v for k, v in p.items() if k in ("name", "id", "organism", "function", "source")}
                for p in results["proteins"][:10]
            ]

        if "compounds" in results:
            slim["compounds"] = [
                {k: v for k, v in c.items() if k in ("name", "smiles", "molecular_weight", "mw", "MW", "logp", "chembl_id", "source")}
                for c in results["compounds"][:15]
            ]

        if "computational" in results:
            comp = results["computational"]
            slim["computational"] = {
                "predictions": [
                    {k: v for k, v in p.items() if k in ("tool", "model", "smiles", "result")}
                    for p in comp.get("predictions", [])[:20]
                ],
                "properties": [
                    {k: v for k, v in p.items() if k in ("tool", "smiles", "result")}
                    for p in comp.get("properties", [])[:20]
                ],
            }

        return slim

    def _extract_data_subset(self, spec: Dict, results: Dict) -> Dict:
        """
        Extract just the data fields mentioned in spec["data_fields"].
        Falls back to returning slim results if field paths are not resolvable.
        """
        subset = {}
        for field_path in spec.get("data_fields", []):
            parts = field_path.split(".")
            try:
                val = results
                for part in parts:
                    # Handle array notation like papers[].year
                    part = part.rstrip("]").split("[")[0]
                    if isinstance(val, dict):
                        val = val.get(part)
                    elif isinstance(val, list):
                        val = [item.get(part) if isinstance(item, dict) else item for item in val]
                    if val is None:
                        break
                if val is not None:
                    subset[field_path] = val
            except Exception:
                pass

        return subset if subset else self._slim_results(results)


# ---------------------------------------------------------------------------
# Standalone entry point for testing
# ---------------------------------------------------------------------------

def run_plot_agent(
    agent_name: str,
    topic: str,
    investigation_results: Dict,
    max_figures: int = 5,
) -> List[str]:
    """
    Convenience function matching the pattern of run_deep_investigation().

    Args:
        agent_name: Authenticated agent name
        topic: Investigation topic
        investigation_results: Dict returned by DeepInvestigator.run_tool_chain()
        max_figures: Maximum number of figures to generate

    Returns:
        List of absolute paths to saved PNG files
    """
    agent = PlotAgent(agent_name=agent_name)
    return agent.generate_figures(topic, investigation_results, max_figures=max_figures)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PlotAgent – standalone test")
    parser.add_argument("--agent", default="TestAgent")
    parser.add_argument("--topic", default="Alzheimer's disease drug targets")
    parser.add_argument("--results", help="Path to investigation_results JSON file")
    args = parser.parse_args()

    if args.results:
        with open(args.results) as f:
            inv_results = json.load(f)
    else:
        # Minimal synthetic results for smoke-testing
        inv_results = {
            "topic": args.topic,
            "tools_used": ["pubmed", "uniprot"],
            "papers": [
                {"title": "APP cleavage in AD", "year": "2020", "pmid": "12345"},
                {"title": "BACE1 inhibitors", "year": "2021", "pmid": "23456"},
                {"title": "Tau phosphorylation", "year": "2022", "pmid": "34567"},
                {"title": "Neuroinflammation in AD", "year": "2023", "pmid": "45678"},
                {"title": "Amyloid clearance", "year": "2024", "pmid": "56789"},
            ],
            "compounds": [
                {"name": "Donepezil", "smiles": "COc1ccc2c(c1OC)C(CC1CCN(Cc3ccccc3)CC1)=CC2=O", "molecular_weight": 379.5},
                {"name": "Memantine", "smiles": "CC12CC(CC(C)(C1)N)(C2)C", "molecular_weight": 179.3},
                {"name": "Aducanumab", "molecular_weight": 145800.0},
                {"name": "Lecanemab", "molecular_weight": 146000.0},
            ],
            "proteins": [
                {"name": "APP", "id": "P05067", "organism": "Homo sapiens"},
                {"name": "BACE1", "id": "P56817", "organism": "Homo sapiens"},
                {"name": "PSEN1", "id": "P49768", "organism": "Homo sapiens"},
            ],
        }

    paths = run_plot_agent(args.agent, args.topic, inv_results)
    print(f"\nGenerated {len(paths)} figures:")
    for p in paths:
        print(f"  {p}")
