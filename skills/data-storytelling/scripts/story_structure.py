#!/usr/bin/env python3
"""
Data storytelling tool - transform scientific findings into compelling
research narratives for papers, grants, conferences, and public communication.
"""

import argparse
import json
import re
import sys


def extract_key_messages(findings: str, n: int = 5) -> list:
    """Extract key messages as bullet points from the findings string."""
    # Split on common delimiters: commas, semicolons, 'and', numbers+periods
    parts = re.split(r"[,;]|\band\b", findings)
    messages = []
    for part in parts:
        part = part.strip()
        # Filter out very short fragments
        if len(part) > 15:
            # Capitalize first letter
            msg = part[0].upper() + part[1:] if part else part
            messages.append(msg)
    return messages[:n] if messages else [findings]


def word_count(text: str) -> int:
    return len(text.split())


# ---- Narrative templates per (audience, format) ----

def build_academic_abstract(findings: str) -> str:
    return (
        "Background: The molecular mechanisms underlying this phenomenon remain incompletely understood, "
        "limiting the development of targeted therapeutic strategies.\n\n"
        "Objective: To characterize the key molecular determinants and evaluate their functional significance "
        "using computational approaches.\n\n"
        "Methods: We employed a multi-modal computational investigation integrating structural bioinformatics, "
        "cheminformatics, and machine learning-based predictive modeling.\n\n"
        f"Results: {findings}\n\n"
        "Conclusion: These findings provide mechanistic insight and identify promising targets for "
        "further computational validation and experimental follow-up. Future work will focus on "
        "structural optimization and selectivity profiling."
    )


def build_academic_introduction(findings: str) -> str:
    return (
        "The field has long sought to elucidate the fundamental molecular mechanisms governing this "
        "biological process. Despite substantial progress, critical gaps remain in our mechanistic "
        "understanding, particularly regarding the interplay between structural determinants and "
        "functional outcomes.\n\n"
        "Computational approaches have emerged as powerful tools for hypothesis generation and "
        "mechanistic investigation at scale. Here, we present evidence that addresses these gaps:\n\n"
        f"{findings}\n\n"
        "Together, these observations motivate a systematic investigation of the molecular basis "
        "and its therapeutic implications."
    )


def build_academic_discussion(findings: str) -> str:
    return (
        "The present computational investigation yields several mechanistically significant observations. "
        f"Specifically, {findings.lower() if findings else findings}\n\n"
        "These findings are consistent with the emerging consensus in the field and extend prior work "
        "by revealing previously uncharacterized molecular determinants. Importantly, the observed "
        "effects are unlikely to reflect methodological artifact, as orthogonal computational approaches "
        "converge on consistent conclusions.\n\n"
        "Limitations include the inherent constraints of in silico modeling, which requires experimental "
        "validation. Additionally, the generalizability of these findings across biological contexts "
        "warrants further investigation.\n\n"
        "In summary, this work advances mechanistic understanding and provides a computational framework "
        "for targeted hypothesis testing."
    )


def build_academic_press_release(findings: str) -> str:
    return (
        f"SCIENTIFIC FINDING SUMMARY\n\n"
        f"Researchers report: {findings}\n\n"
        "This work was conducted using advanced computational methods including structural bioinformatics "
        "and machine learning. The findings contribute to the fundamental scientific understanding of "
        "this area and may have implications for future research directions."
    )


def build_general_abstract(findings: str) -> str:
    return (
        "Scientists have made an important discovery that could help us better understand and address "
        "a significant challenge.\n\n"
        f"The key finding: {findings}\n\n"
        "This work was carried out using powerful computer-based tools that can analyze vast amounts "
        "of biological and chemical data. The researchers believe this discovery opens new doors for "
        "future investigation."
    )


def build_general_introduction(findings: str) -> str:
    return (
        "Every year, millions of people are affected by conditions that scientists are still working "
        "to fully understand. Making progress requires new tools, new data, and new ways of thinking "
        "about complex biological problems.\n\n"
        f"Our latest work has uncovered something important: {findings}\n\n"
        "To achieve this, our team used cutting-edge computational methods - essentially using powerful "
        "computers to analyze the building blocks of life at a molecular level."
    )


def build_general_discussion(findings: str) -> str:
    return (
        f"What does this mean? In simple terms: {findings}\n\n"
        "Think of it like finding a key that fits a very specific lock. By understanding this molecular "
        "mechanism, scientists can design better approaches targeted at the root cause rather than "
        "just the symptoms.\n\n"
        "Of course, there is still more work to do. Laboratory experiments will be needed to confirm "
        "these computer-based predictions. But this is an exciting step forward."
    )


def build_general_press_release(findings: str) -> str:
    return (
        "FOR IMMEDIATE RELEASE\n\n"
        "SCIENTISTS MAKE BREAKTHROUGH DISCOVERY\n\n"
        f"In a new study, researchers have discovered that {findings.lower() if findings else findings}. "
        "This finding could have important implications for future treatments and our understanding "
        "of the underlying biology.\n\n"
        '"This is an exciting step forward," said the research team. "These computational results '
        'give us new directions to explore."\n\n'
        "The study used advanced computer modeling to analyze molecular data at unprecedented scale. "
        "Results are currently being prepared for peer review and publication.\n\n"
        "###"
    )


def build_grant_abstract(findings: str) -> str:
    return (
        "SIGNIFICANCE: This proposal addresses a critical unmet need in the field. Current approaches "
        "are limited by insufficient mechanistic understanding, leading to high failure rates and "
        "significant unmet clinical need.\n\n"
        "INNOVATION: Our preliminary computational data demonstrate a novel and unexpected mechanism:\n"
        f"{findings}\n\n"
        "APPROACH: We will employ a rigorous multi-stage computational strategy to validate and "
        "extend these findings, culminating in actionable targets for downstream investigation.\n\n"
        "IMPACT: Successful completion will establish a new mechanistic framework with direct "
        "translational relevance, positioning the field for accelerated progress."
    )


def build_grant_introduction(findings: str) -> str:
    return (
        "The proposed research addresses a significant gap in our mechanistic understanding with "
        "direct translational relevance. Despite decades of investigation, the field lacks "
        "actionable molecular targets with validated mechanisms of action.\n\n"
        "Our preliminary computational data provide compelling justification for this proposal. "
        f"Specifically: {findings}\n\n"
        "These observations are highly significant because they: (1) identify a tractable molecular "
        "target, (2) provide mechanistic rationale for intervention, and (3) suggest a clear "
        "computational validation strategy with defined milestones.\n\n"
        "The proposed research is innovative, rigorously designed, and has high probability of "
        "producing impactful, reproducible results."
    )


def build_grant_discussion(findings: str) -> str:
    return (
        "Our preliminary data strongly support the central hypothesis of this proposal. "
        f"Key findings include: {findings}\n\n"
        "Potential challenges include the complexity of the biological system and inherent "
        "limitations of computational modeling. We have designed rigorous controls and "
        "alternative approaches to address each potential pitfall (see Approach section).\n\n"
        "The expected outcomes of this research will: (1) fill a critical knowledge gap, "
        "(2) establish novel mechanistic principles applicable across related systems, and "
        "(3) provide a validated computational framework for future translational work.\n\n"
        "Timeline: Year 1 - validation studies; Year 2 - mechanistic dissection; "
        "Year 3 - translational application and dissemination."
    )


def build_grant_press_release(findings: str) -> str:
    return (
        "FUNDING IMPACT STATEMENT\n\n"
        "This research program addresses a high-priority scientific challenge with direct "
        "translational implications.\n\n"
        f"Key scientific advances enabled by this funding: {findings}\n\n"
        "The outcomes of this work will establish a new mechanistic framework, train the next "
        "generation of computational scientists, and accelerate the development of targeted "
        "interventions. Return on investment includes publications in high-impact journals, "
        "intellectual property generation, and positioning for follow-on funding."
    )


def build_conference_abstract(findings: str) -> str:
    return (
        f"We present computational evidence that {findings.lower() if findings else findings}. "
        "Using an integrated multi-tool pipeline combining structural bioinformatics, cheminformatics, "
        "and predictive modeling, we systematically characterized the molecular determinants of this "
        "phenomenon. Our results reveal a previously unappreciated mechanism with implications for "
        "target identification and lead optimization. We will discuss these findings in the context "
        "of the broader field and outline key open questions for community investigation."
    )


def build_conference_introduction(findings: str) -> str:
    return (
        "Good morning / afternoon. Thank you for the opportunity to present our recent work.\n\n"
        "The central question driving our research is: [how/why/what]?\n\n"
        "To motivate this question, consider the following: despite significant effort, the field "
        "has lacked a clear mechanistic framework. Our computational work now provides one.\n\n"
        f"The headline result: {findings}\n\n"
        "In the next [X] minutes, I will walk you through how we got here, what it means, "
        "and where we think the field should go next."
    )


def build_conference_discussion(findings: str) -> str:
    return (
        "To summarize, our data support the following model:\n\n"
        f"{findings}\n\n"
        "The key mechanistic insight is [X], which was not previously appreciated in the field. "
        "This changes how we should think about [Y].\n\n"
        "Open questions: [1] How does this mechanism interact with [Z]? "
        "[2] Is this conserved across related systems? [3] What are the therapeutic implications?\n\n"
        "We welcome collaboration and discussion. Our data and code are available at [repository link].\n\n"
        "Thank you. I am happy to take questions."
    )


def build_conference_press_release(findings: str) -> str:
    return (
        "CONFERENCE PRESENTATION HIGHLIGHT\n\n"
        f"Researchers will present new findings showing: {findings}\n\n"
        "This work will be presented at [Conference Name], [Date], [Session].\n\n"
        "The team used computational biology approaches to reach these conclusions and is "
        "seeking collaborators for follow-up experimental validation."
    )


TEMPLATES = {
    ("academic", "abstract"): build_academic_abstract,
    ("academic", "introduction"): build_academic_introduction,
    ("academic", "discussion"): build_academic_discussion,
    ("academic", "press-release"): build_academic_press_release,
    ("general", "abstract"): build_general_abstract,
    ("general", "introduction"): build_general_introduction,
    ("general", "discussion"): build_general_discussion,
    ("general", "press-release"): build_general_press_release,
    ("grant", "abstract"): build_grant_abstract,
    ("grant", "introduction"): build_grant_introduction,
    ("grant", "discussion"): build_grant_discussion,
    ("grant", "press-release"): build_grant_press_release,
    ("conference", "abstract"): build_conference_abstract,
    ("conference", "introduction"): build_conference_introduction,
    ("conference", "discussion"): build_conference_discussion,
    ("conference", "press-release"): build_conference_press_release,
}


def main():
    parser = argparse.ArgumentParser(
        description="Transform scientific findings into audience-appropriate research narratives"
    )
    parser.add_argument(
        "--findings",
        required=True,
        help="The scientific findings to structure into a narrative",
    )
    parser.add_argument(
        "--audience",
        choices=["academic", "general", "grant", "conference"],
        default="academic",
        help="Target audience (default: academic)",
    )
    parser.add_argument(
        "--format",
        choices=["abstract", "introduction", "discussion", "press-release"],
        default="abstract",
        help="Document section format (default: abstract)",
    )
    args = parser.parse_args()

    try:
        builder = TEMPLATES.get((args.audience, args.format))
        if builder is None:
            raise ValueError(
                f"No template for audience='{args.audience}', format='{args.format}'"
            )
        narrative = builder(args.findings)
        key_messages = extract_key_messages(args.findings)
    except Exception as e:
        result = {
            "error": str(e),
            "audience": args.audience,
            "format": args.format,
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    result = {
        "audience": args.audience,
        "format": args.format,
        "narrative": narrative,
        "key_messages": key_messages,
        "word_count": word_count(narrative),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
