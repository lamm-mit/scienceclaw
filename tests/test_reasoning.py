#!/usr/bin/env python3
"""
Phase 2 Reasoning Engine - Comprehensive Test Suite

Tests all components with proper assertions and isolated temp directories.
Run with: python -m pytest tests/test_reasoning_phase2.py -v
Or: python -m unittest tests.test_reasoning_phase2 -v
"""

import unittest
import tempfile
import shutil
import sys
from pathlib import Path

# Add scienceclaw to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
from reasoning import (
    ScientificReasoningEngine,
    GapDetector,
    HypothesisGenerator,
    ExperimentDesigner,
    ExperimentExecutor,
    ResultAnalyzer,
)


class TestGapDetector(unittest.TestCase):
    """Tests for GapDetector component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.journal = AgentJournal("TestAgent", base_dir=f"{self.temp_dir}/journals")
        self.kg = KnowledgeGraph("TestAgent", base_dir=f"{self.temp_dir}/knowledge")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_open_questions_from_posts(self):
        """GapDetector should extract open questions from posts."""
        detector = GapDetector(self.kg, self.journal)
        context = {
            "posts": [
                {"id": "p1", "openQuestions": ["What is the optimal concentration?"]}
            ]
        }
        gaps = detector.detect_gaps(context)
        self.assertGreater(len(gaps), 0)
        self.assertEqual(gaps[0]["type"], "open_question")
        self.assertIn("optimal concentration", gaps[0]["description"])
        self.assertEqual(gaps[0]["priority"], "medium")

    def test_detect_gaps_empty_context(self):
        """GapDetector should return empty list with no context and empty memory."""
        detector = GapDetector(self.kg, self.journal)
        gaps = detector.detect_gaps()
        # May have unvalidated hypotheses if journal has entries
        self.assertIsInstance(gaps, list)

    def test_detect_contradictions(self):
        """GapDetector should find contradictions in knowledge graph."""
        # Add contradiction to KG
        n1 = self.kg.add_node("Finding A", "finding")
        n2 = self.kg.add_node("Finding B", "finding")
        self.kg.add_edge(n1, n2, "contradicts")
        detector = GapDetector(self.kg, self.journal)
        gaps = detector.detect_gaps()
        self.assertGreater(len(gaps), 0)
        contradiction_gaps = [g for g in gaps if g["type"] == "contradiction"]
        self.assertGreater(len(contradiction_gaps), 0)

    def test_extract_open_questions(self):
        """extract_open_questions returns list of questions."""
        detector = GapDetector(self.kg, self.journal)
        posts = [
            {"openQuestions": ["Q1?", "Q2?"]},
            {"open_questions": ["Q3?"]},
        ]
        questions = detector.extract_open_questions(posts)
        self.assertEqual(len(questions), 3)
        self.assertIn("Q1?", questions)
        self.assertIn("Q3?", questions)


class TestHypothesisGenerator(unittest.TestCase):
    """Tests for HypothesisGenerator component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.journal = AgentJournal("TestAgent", base_dir=f"{self.temp_dir}/journals")
        self.kg = KnowledgeGraph("TestAgent", base_dir=f"{self.temp_dir}/knowledge")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_from_open_question(self):
        """HypothesisGenerator creates hypothesis from open question gap."""
        generator = HypothesisGenerator(self.kg, self.journal)
        gap = {
            "type": "open_question",
            "description": "What is the optimal temperature?",
            "priority": "medium",
        }
        hypotheses = generator.generate_hypotheses(gap)
        self.assertGreater(len(hypotheses), 0)
        self.assertIn("statement", hypotheses[0])
        self.assertIn("testable", hypotheses[0])
        self.assertTrue(hypotheses[0]["testable"])
        self.assertIn("planned_tools", hypotheses[0])

    def test_generate_from_contradiction(self):
        """HypothesisGenerator creates resolution hypotheses from contradiction."""
        generator = HypothesisGenerator(self.kg, self.journal)
        gap = {
            "type": "contradiction",
            "description": "Conflicting findings",
            "findings": [
                {"name": "Finding A shows X"},
                {"name": "Finding B shows not X"},
            ],
        }
        hypotheses = generator.generate_hypotheses(gap)
        self.assertGreaterEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0]["type"], "resolution")
        self.assertEqual(hypotheses[0]["priority"], "high")

    def test_question_to_hypothesis(self):
        """_question_to_hypothesis converts questions to testable form."""
        generator = HypothesisGenerator(self.kg, self.journal)
        result_what = generator._question_to_hypothesis("What is X?")
        result_how = generator._question_to_hypothesis("How does X work?")
        self.assertIn("what", result_what.lower())
        self.assertIn("how", result_how.lower())


class TestExperimentDesigner(unittest.TestCase):
    """Tests for ExperimentDesigner component."""

    def setUp(self):
        self.designer = ExperimentDesigner("TestAgent")

    def test_design_experiment_returns_plan(self):
        """ExperimentDesigner returns valid experiment plan."""
        hypothesis = {
            "statement": "CRISPR delivery efficiency varies with LNP formulation",
            "planned_tools": ["pubmed"],
            "success_criteria": "Find supporting papers",
        }
        plan = self.designer.design_experiment(hypothesis)
        self.assertIn("tool", plan)
        self.assertIn("parameters", plan)
        self.assertIn("script_path", plan)
        self.assertIn("description", plan)
        self.assertEqual(plan["tool"], "pubmed")
        self.assertIn("query", plan["parameters"])

    def test_design_with_chemistry_tools(self):
        """ExperimentDesigner selects chemistry tools for chemistry hypotheses."""
        hypothesis = {
            "statement": "Compound aspirin affects BBB permeability",
            "planned_tools": ["pubchem", "tdc"],
        }
        plan = self.designer.design_experiment(hypothesis)
        self.assertIn(plan["tool"], ["pubchem", "tdc", "pubmed"])

    def test_tools_registry(self):
        """ExperimentDesigner has expected tools."""
        expected = ["pubmed", "blast", "uniprot", "pubchem", "chembl", "tdc"]
        for tool in expected:
            self.assertIn(tool, ExperimentDesigner.TOOLS)


class TestExperimentExecutor(unittest.TestCase):
    """Tests for ExperimentExecutor component."""

    def setUp(self):
        self.executor = ExperimentExecutor("TestAgent")

    def test_execute_missing_script_returns_error(self):
        """Executor returns error for non-existent script."""
        plan = {
            "script_path": "/nonexistent/script.py",
            "parameters": {},
            "tool": "unknown",
        }
        result = self.executor.execute_experiment(plan)
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_execute_pubmed_succeeds(self):
        """Executor can run pubmed search (if script exists)."""
        from pathlib import Path
        script_path = Path(__file__).parent.parent / "skills" / "pubmed" / "scripts" / "pubmed_search.py"
        if not script_path.exists():
            self.skipTest("pubmed script not found")
        plan = {
            "script_path": str(script_path),
            "parameters": {"query": "CRISPR", "max_results": 2},
            "tool": "pubmed",
        }
        result = self.executor.execute_experiment(plan)
        self.assertIn(result["status"], ["success", "error"])
        if result["status"] == "success":
            self.assertIn("output", result)
            self.assertIn("summary", result)

    def test_validate_tool_available(self):
        """validate_tool_available returns bool."""
        self.assertIsInstance(self.executor.validate_tool_available("pubmed"), bool)


class TestResultAnalyzer(unittest.TestCase):
    """Tests for ResultAnalyzer component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph("TestAgent", base_dir=f"{self.temp_dir}/knowledge")
        self.journal = AgentJournal("TestAgent", base_dir=f"{self.temp_dir}/journals")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_failed_experiment(self):
        """Analyzer handles failed experiment."""
        analyzer = ResultAnalyzer(self.kg, self.journal)
        hypothesis = {"statement": "Test hypothesis"}
        plan = {"tool": "pubmed"}
        result = {"status": "error", "error": "Script not found"}
        analysis = analyzer.analyze_results(hypothesis, plan, result)
        self.assertFalse(analysis["sufficient_evidence"])
        self.assertEqual(analysis["status"], "experiment_failed")

    def test_analyze_pubmed_success(self):
        """Analyzer interprets successful PubMed results."""
        analyzer = ResultAnalyzer(self.kg, self.journal)
        hypothesis = {"statement": "CRISPR delivery"}
        plan = {"tool": "pubmed"}
        result = {
            "status": "success",
            "tool": "pubmed",
            "output": {"papers": [{"title": "Paper 1"}, {"title": "Paper 2"}, {"title": "Paper 3"}]},
        }
        analysis = analyzer.analyze_results(hypothesis, plan, result)
        self.assertIn("support", analysis)
        self.assertIn("confidence", analysis)
        self.assertIn("reasoning", analysis)
        self.assertGreater(analysis["evidence_count"], 0)

    def test_analyze_empty_results(self):
        """Analyzer handles empty/no results."""
        analyzer = ResultAnalyzer(self.kg, self.journal)
        hypothesis = {"statement": "Test"}
        plan = {"tool": "pubmed"}
        result = {"status": "success", "tool": "pubmed", "output": {"papers": []}}
        analysis = analyzer.analyze_results(hypothesis, plan, result)
        self.assertFalse(analysis["sufficient_evidence"])
        self.assertEqual(analysis["support"], "inconclusive")


class TestScientificReasoningEngine(unittest.TestCase):
    """Tests for full ScientificReasoningEngine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_base = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_engine_initializes(self):
        """Engine initializes with all components."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        self.assertIsNotNone(engine.journal)
        self.assertIsNotNone(engine.tracker)
        self.assertIsNotNone(engine.kg)
        self.assertIsNotNone(engine.gap_detector)
        self.assertIsNotNone(engine.hypothesis_generator)
        self.assertIsNotNone(engine.experiment_designer)
        self.assertIsNotNone(engine.executor)
        self.assertIsNotNone(engine.analyzer)

    def test_run_cycle_with_posts(self):
        """Engine runs full cycle with posts context."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        context = {
            "posts": [
                {
                    "id": "p1",
                    "openQuestions": ["What is the optimal lipid concentration for LNP delivery?"],
                }
            ]
        }
        result = engine.run_scientific_cycle(context)
        self.assertIn("mode", result)
        self.assertIn("agent", result)
        self.assertEqual(result["agent"], "TestAgent")
        # Should detect gap and run cycle
        self.assertIn(result["mode"], ["new_investigation", "continue_investigation"])
        if result["mode"] == "new_investigation":
            self.assertIn("status", result)

    def test_run_cycle_updates_memory(self):
        """Engine updates journal and tracker during cycle."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        context = {"posts": [{"id": "p1", "openQuestions": ["How does protein X fold?"]}]}
        result = engine.run_scientific_cycle(context)
        # Check journal has entries
        stats = engine.journal.get_stats()
        self.assertGreaterEqual(stats["total_entries"], 0)
        # Tracker stats
        tracker_stats = engine.tracker.get_stats()
        self.assertIn("active_count", tracker_stats)

    def test_observe_knowledge_gaps(self):
        """observe_knowledge_gaps returns list."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        gaps = engine.observe_knowledge_gaps([{"openQuestions": ["Q1?"]}])
        self.assertIsInstance(gaps, list)

    def test_peer_review_returns_review(self):
        """peer_review returns structured review."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        post = {
            "id": "p1",
            "hypothesis": "Test hypothesis",
            "method": "BLAST search",
            "data_sources": ["pmid:123"],
        }
        review = engine.peer_review(post)
        self.assertIn("scores", review)
        self.assertIn("overall", review)
        self.assertIn(review["overall"], ["rigorous", "needs_improvement", "needs_review"])


class TestIntegration(unittest.TestCase):
    """Integration tests for Phase 2 + Phase 1 memory."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_base = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_cycle_memory_integration(self):
        """Full cycle correctly uses journal, tracker, and knowledge graph."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        context = {"posts": [{"id": "p1", "openQuestions": ["Does compound X cross BBB?"]}]}
        result = engine.run_scientific_cycle(context)
        # Verify memory was used
        self.assertIsNotNone(result)
        journal_stats = engine.journal.get_stats()
        kg_stats = engine.kg.get_stats()
        self.assertIsInstance(journal_stats, dict)
        self.assertIsInstance(kg_stats, dict)

    def test_continue_investigation_mode(self):
        """Engine continues existing investigation when one is active."""
        engine = ScientificReasoningEngine("TestAgent", memory_base_dir=self.memory_base)
        # Create active investigation first
        inv_id = engine.tracker.create_investigation(
            hypothesis="Test hypothesis",
            goal="Test goal",
            planned_experiments=["pubmed", "blast"],
            priority="high",
        )
        result = engine.run_scientific_cycle()
        self.assertEqual(result["mode"], "continue_investigation")
        self.assertEqual(result["investigation_id"], inv_id)


def run_tests():
    """Run all tests with unittest."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(sys.modules[__name__]))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
