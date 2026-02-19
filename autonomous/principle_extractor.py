"""
Principle Extractor — Feature 4: Cross-investigation pattern learning

After sufficient investigations accumulate, extract generalizable scientific
principles that appear consistently across multiple findings.  Principles are
stored as "principle" nodes in the KnowledgeGraph for future reference and
synthesis posts.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from memory.journal import AgentJournal
    from memory.knowledge_graph import KnowledgeGraph
except ImportError:
    AgentJournal = None
    KnowledgeGraph = None


class PrincipleExtractor:
    """
    Extract generalizable scientific principles from an agent's investigation history.

    Trigger logic:
    - Called after each completed investigation
    - Requires ≥3 topic-similar past investigations to attempt extraction
    - Extracted principles stored in KnowledgeGraph with type="principle"
    - Should_synthesize() returns True when ≥5 principles exist for a domain
    """

    MIN_INVESTIGATIONS_FOR_EXTRACTION = 3
    MIN_PRINCIPLES_FOR_SYNTHESIS = 5
    MAX_PAST_INVESTIGATIONS = 5

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.journal = AgentJournal(agent_name) if AgentJournal else None
        self.knowledge = KnowledgeGraph(agent_name) if KnowledgeGraph else None
        self.scienceclaw_dir = Path(__file__).parent.parent

    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """Call LLM for principle synthesis."""
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=self.agent_name)
            response = client.call(
                prompt=prompt,
                max_tokens=max_tokens,
                session_id=f"principle_extractor_{self.agent_name}"
            )
            return response if len(response) > 30 else ""
        except Exception as e:
            print(f"    Note: Principle extraction LLM unavailable ({e})")
            return ""

    def _get_similar_past_investigations(self, topic: str, n: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve N most recent journal entries for topic-similar investigations.

        Similarity is keyword-based: overlapping words (ignoring stopwords) ≥ 1.
        """
        if not self.journal:
            return []

        stopwords = {"the", "a", "an", "of", "in", "for", "and", "or", "to", "with", "via",
                     "from", "by", "on", "at", "is", "are", "was", "were", "be", "been"}
        topic_words = {w.lower() for w in re.split(r'\W+', topic) if w.lower() not in stopwords and len(w) > 2}

        past: List[Dict[str, Any]] = []
        try:
            # Read journal JSONL file directly
            journal_path = self.journal.journal_path
            if not journal_path.exists():
                return []
            with open(journal_path) as f:
                lines = f.readlines()

            # Scan recent entries (newest first via reverse)
            for line in reversed(lines):
                if len(past) >= n:
                    break
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                entry_text = json.dumps(entry).lower()
                entry_words = {w for w in re.split(r'\W+', entry_text) if len(w) > 2}
                # At least 1 topic keyword must appear in the entry
                if topic_words & entry_words:
                    content = entry.get("content", "")
                    metadata = entry.get("metadata", {})
                    past.append({
                        "topic": metadata.get("topic", topic),
                        "summary": content[:300],
                        "timestamp": entry.get("timestamp", ""),
                        "type": entry.get("type", "observation")
                    })
        except Exception as e:
            print(f"    Note: Could not read journal for principle extraction ({e})")

        return past

    def _call_llm_for_principles(self, topic: str, investigations: List[Dict[str, Any]]) -> List[Dict]:
        """
        Ask LLM to extract generalizable principles from past investigations.

        Returns list of dicts with keys: principle, evidence_count, confidence, domain
        """
        if len(investigations) < self.MIN_INVESTIGATIONS_FOR_EXTRACTION:
            return []

        inv_text = ""
        for i, inv in enumerate(investigations, 1):
            inv_text += f"\n{i}. Topic: {inv.get('topic', 'unknown')}\n   Summary: {inv.get('summary', '')}\n"

        # Infer domain from topic keywords
        domain = "general"
        topic_lower = topic.lower()
        if any(k in topic_lower for k in ("drug", "compound", "smiles", "admet", "bbb", "inhibitor", "molecule")):
            domain = "chemistry"
        elif any(k in topic_lower for k in ("protein", "gene", "sequence", "blast", "uniprot", "crispr")):
            domain = "biology"
        elif any(k in topic_lower for k in ("material", "crystal", "bandgap", "perovskite")):
            domain = "materials"

        prompt = f"""You are analyzing {len(investigations)} completed computational investigations on the topic domain: {domain}
Related to: {topic}

Investigations:
{inv_text}

Extract general scientific principles that appear CONSISTENTLY across these investigations.
A principle must be supported by at least 2 independent investigations.

Rules:
- Principles must be mechanistic and specific, not vague observations
- Each principle must be falsifiable
- Do not extract trivial or obvious statements

Format each principle EXACTLY as:
PRINCIPLE: [statement of the generalizable rule]
EVIDENCE_COUNT: [integer number of investigations supporting this]
CONFIDENCE: [high|medium|low]
DOMAIN: [{domain}|biology|chemistry|materials|general]

Only output principles with EVIDENCE_COUNT >= 2.
If no consistent principles can be identified, output: NO_PRINCIPLES_FOUND"""

        response = self._call_llm(prompt, max_tokens=600)
        if not response or "NO_PRINCIPLES_FOUND" in response:
            return []

        principles = []
        current: Dict[str, Any] = {}
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('PRINCIPLE:'):
                if current.get('principle'):
                    principles.append(current)
                current = {'principle': line.replace('PRINCIPLE:', '').strip()}
            elif line.startswith('EVIDENCE_COUNT:'):
                try:
                    current['evidence_count'] = int(re.search(r'\d+', line).group())
                except (AttributeError, ValueError):
                    current['evidence_count'] = 2
            elif line.startswith('CONFIDENCE:'):
                current['confidence'] = line.replace('CONFIDENCE:', '').strip().lower()
            elif line.startswith('DOMAIN:'):
                current['domain'] = line.replace('DOMAIN:', '').strip().lower()

        if current.get('principle'):
            principles.append(current)

        # Filter to minimum evidence count
        return [p for p in principles if p.get('evidence_count', 0) >= 2]

    def _store_principles(self, principles: List[Dict]) -> None:
        """Store extracted principles in the KnowledgeGraph as principle nodes."""
        if not self.knowledge or not principles:
            return
        for p in principles:
            statement = p.get('principle', '')
            if not statement:
                continue
            try:
                self.knowledge.add_node(
                    name=statement[:120],  # Truncate for node name
                    node_type="principle",
                    properties={
                        "full_statement": statement,
                        "evidence_count": p.get('evidence_count', 2),
                        "confidence": p.get('confidence', 'medium'),
                        "domain": p.get('domain', 'general'),
                    },
                    source="principle_extractor"
                )
            except Exception as e:
                print(f"    Note: Could not store principle in knowledge graph ({e})")

    def extract_principles(
        self,
        topic: str,
        current_findings: str,
        agent_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Main entry point: extract principles after completing an investigation.

        Args:
            topic: Current investigation topic
            current_findings: Summary of current investigation findings
            agent_name: Agent name (defaults to self.agent_name)

        Returns:
            List of extracted principle dicts (may be empty if insufficient data)
        """
        past = self._get_similar_past_investigations(topic, n=self.MAX_PAST_INVESTIGATIONS)

        if len(past) < self.MIN_INVESTIGATIONS_FOR_EXTRACTION:
            print(f"  💡 Principle extraction: only {len(past)} similar past investigations "
                  f"(need {self.MIN_INVESTIGATIONS_FOR_EXTRACTION}) — skipping")
            return []

        print(f"  💡 Extracting principles from {len(past)} past investigations...")

        # Include current findings as the most recent investigation
        all_investigations = past + [{
            "topic": topic,
            "summary": current_findings[:300],
            "timestamp": "",
            "type": "current"
        }]

        principles = self._call_llm_for_principles(topic, all_investigations)

        if principles:
            self._store_principles(principles)
            print(f"  💡 {len(principles)} principle(s) extracted and stored in knowledge graph")
        else:
            print(f"  💡 No consistent principles found across {len(past)} investigations")

        return principles

    def should_synthesize(self, domain: Optional[str] = None) -> bool:
        """
        Check if enough principles have accumulated to warrant a synthesis post.

        Returns True if ≥5 principle nodes exist in the knowledge graph,
        optionally filtered by domain.
        """
        if not self.knowledge:
            return False
        try:
            principles = self.knowledge.get_principles(domain=domain)
            return len(principles) >= self.MIN_PRINCIPLES_FOR_SYNTHESIS
        except Exception:
            return False
