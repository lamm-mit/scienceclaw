#!/usr/bin/env python3
"""
Prompt engineering patterns tool - generate optimized LLM prompts for
scientific reasoning using chain-of-thought, ReAct, tree-of-thought,
few-shot, and self-consistency patterns.
"""

import argparse
import json
import sys

DOMAIN_PERSONAS = {
    "biology": (
        "You are an expert computational biologist with deep knowledge of molecular biology, "
        "genomics, proteomics, and bioinformatics. You reason rigorously using evidence from "
        "peer-reviewed literature and computational databases (UniProt, PDB, NCBI)."
    ),
    "chemistry": (
        "You are an expert computational chemist and medicinal chemist specializing in "
        "drug discovery, ADMET prediction, and cheminformatics. You reason using molecular "
        "properties, structure-activity relationships, and thermodynamic principles."
    ),
    "materials": (
        "You are an expert materials scientist with expertise in computational materials "
        "discovery, DFT calculations, and structure-property relationships. You reason "
        "using crystallographic data, electronic structure, and thermodynamic stability."
    ),
    "general": (
        "You are an expert scientific researcher with broad knowledge across biology, "
        "chemistry, and data science. You reason rigorously, cite evidence, and "
        "acknowledge uncertainty appropriately."
    ),
}

PATTERN_EXPLANATIONS = {
    "chain-of-thought": (
        "Chain-of-thought prompting elicits step-by-step reasoning, improving accuracy on "
        "complex scientific tasks by up to 40% compared to direct answering. Forces the model "
        "to externalize intermediate reasoning steps before reaching conclusions."
    ),
    "tree-of-thought": (
        "Tree-of-thought prompting explores multiple reasoning branches simultaneously, "
        "evaluating different hypotheses or approaches before selecting the most promising path. "
        "Particularly effective for problems with multiple plausible solutions."
    ),
    "few-shot": (
        "Few-shot prompting provides concrete examples of the desired reasoning pattern, "
        "strongly constraining the output format and reasoning style. Effective when "
        "a specific output structure is required."
    ),
    "react": (
        "ReAct (Reason + Act) prompting structures responses as interleaved Thought/Action/Observation "
        "cycles, designed for tool-using agents. Improves grounding by requiring the model to "
        "specify tool calls and interpret results before drawing conclusions."
    ),
    "self-consistency": (
        "Self-consistency prompting generates multiple independent reasoning chains and "
        "selects the most consistent answer via majority vote or synthesis. Reduces "
        "hallucination and improves reliability on factual scientific questions."
    ),
}


def build_chain_of_thought(task: str, domain: str) -> str:
    persona = DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])
    return f"""{persona}

Task: {task}

Let's think through this step by step:

Step 1 - Understand the problem: What exactly is being asked? What are the key entities, constraints, and goals?

Step 2 - Gather relevant knowledge: What do we know from literature, databases, and computational models that is directly relevant?

Step 3 - Formulate a hypothesis: Based on existing knowledge, what is the most parsimonious scientific hypothesis?

Step 4 - Identify evidence: What specific data points, experimental results, or computational predictions support or contradict this hypothesis?

Step 5 - Consider alternatives: What are the main competing hypotheses? What evidence would distinguish between them?

Step 6 - Draw conclusions: What can we conclude with high confidence? What remains uncertain? What are the next experimental or computational steps?

Now, apply this reasoning framework to the task:
{task}"""


def build_tree_of_thought(task: str, domain: str) -> str:
    persona = DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])
    return f"""{persona}

Task: {task}

Use tree-of-thought reasoning to explore multiple approaches:

Branch A - Mechanistic approach:
  Hypothesis A: [Propose a mechanistic explanation]
  Evidence for A: [List supporting evidence]
  Evidence against A: [List contradicting evidence]
  Confidence: [Low/Medium/High]

Branch B - Evolutionary/historical approach:
  Hypothesis B: [Propose an alternative explanation]
  Evidence for B: [List supporting evidence]
  Evidence against B: [List contradicting evidence]
  Confidence: [Low/Medium/High]

Branch C - Computational/data-driven approach:
  Hypothesis C: [Propose a data-driven explanation]
  Evidence for C: [List supporting evidence]
  Evidence against C: [List contradicting evidence]
  Confidence: [Low/Medium/High]

Evaluation:
  - Best supported branch: [A/B/C] because [reason]
  - Key uncertainties: [List]
  - Recommended next steps: [List]

Apply this tree-of-thought framework to: {task}"""


def build_few_shot(task: str, domain: str) -> str:
    persona = DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])
    return f"""{persona}

Below are examples of high-quality scientific reasoning for similar tasks.

---
Example 1:
Task: Predict whether compound X inhibits kinase Y.
Reasoning: Compound X contains a Type II DFG-out binding motif (urea warhead). Kinase Y has a DFG-Asp that can adopt the out conformation (confirmed by PDB 4ABC). The compound's predicted IC50 (TDC: 45 nM) and logP (2.8) suggest good potency and cell permeability. Conclusion: High probability of inhibition via DFG-out mechanism.

Example 2:
Task: Identify the rate-limiting step in pathway Z.
Reasoning: From KEGG data, pathway Z has 6 enzymatic steps. Flux control analysis (metabolic control theory) assigns the highest flux control coefficient (FCC=0.72) to step 3 (catalyzed by enzyme E3). Literature (PMID:12345678) confirms E3 as allosterically regulated. Conclusion: E3 is the rate-limiting enzyme.
---

Now apply the same rigorous reasoning approach to:
Task: {task}
Reasoning:"""


def build_react(task: str, domain: str) -> str:
    persona = DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])
    return f"""{persona}

You have access to the following scientific tools:
- pubmed_search(query) - Search PubMed for relevant literature
- uniprot_lookup(protein_id) - Get protein sequence and function data
- pubchem_search(compound) - Get molecular properties and bioassays
- blast_search(sequence) - Find homologous sequences
- tdc_predict(smiles, model) - Predict ADMET properties
- materials_search(formula) - Query Materials Project database

Use the ReAct format: alternate Thought, Action, and Observation steps.

Task: {task}

Thought 1: [What do I need to find out first?]
Action 1: [tool_name(parameters)]
Observation 1: [What would this tool return?]

Thought 2: [Based on the observation, what is my next step?]
Action 2: [tool_name(parameters)]
Observation 2: [Expected result]

Thought 3: [Synthesize findings]
Action 3: [Final analysis or additional lookup]
Observation 3: [Final data]

Final Answer: [Synthesized conclusion with confidence level and caveats]

Begin:"""


def build_self_consistency(task: str, domain: str) -> str:
    persona = DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])
    return f"""{persona}

Task: {task}

Generate THREE independent reasoning chains, then synthesize to the most consistent conclusion.

Reasoning Chain 1 (Focus: mechanistic evidence):
[Reason through the task using mechanistic/structural arguments]
Tentative conclusion 1: [...]

Reasoning Chain 2 (Focus: empirical/database evidence):
[Reason through the task using experimental data and database information]
Tentative conclusion 2: [...]

Reasoning Chain 3 (Focus: computational predictions):
[Reason through the task using computational methods and models]
Tentative conclusion 3: [...]

Synthesis:
- Points of agreement across all three chains: [...]
- Points of disagreement: [...]
- Most consistent conclusion: [...]
- Confidence level: [Low/Medium/High]
- Key assumptions: [...]
- Limitations: [...]"""


BUILDERS = {
    "chain-of-thought": build_chain_of_thought,
    "tree-of-thought": build_tree_of_thought,
    "few-shot": build_few_shot,
    "react": build_react,
    "self-consistency": build_self_consistency,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate optimized LLM prompts for scientific reasoning tasks"
    )
    parser.add_argument("--task", required=True, help="The scientific task to create a prompt for")
    parser.add_argument(
        "--pattern",
        choices=list(BUILDERS.keys()),
        default="chain-of-thought",
        help="Prompt engineering pattern to use (default: chain-of-thought)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Scientific domain (e.g. biology, chemistry, materials)",
    )
    args = parser.parse_args()

    domain = args.domain or "general"

    try:
        builder = BUILDERS[args.pattern]
        optimized_prompt = builder(args.task, domain)
    except Exception as e:
        result = {"error": str(e), "pattern": args.pattern, "task": args.task}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    result = {
        "pattern": args.pattern,
        "task": args.task,
        "domain": domain,
        "optimized_prompt": optimized_prompt,
        "explanation": PATTERN_EXPLANATIONS[args.pattern],
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
