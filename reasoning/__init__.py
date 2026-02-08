"""
ScienceClaw Scientific Reasoning Engine

Implements autonomous scientific method:
- Observe knowledge gaps
- Generate hypotheses
- Design experiments
- Execute experiments
- Analyze results
- Draw conclusions
- Peer review
"""

from .scientific_engine import ScientificReasoningEngine
from .gap_detector import GapDetector
from .hypothesis_generator import HypothesisGenerator
from .experiment_designer import ExperimentDesigner
from .executor import ExperimentExecutor
from .analyzer import ResultAnalyzer

__all__ = [
    'ScientificReasoningEngine',
    'GapDetector',
    'HypothesisGenerator',
    'ExperimentDesigner',
    'ExperimentExecutor',
    'ResultAnalyzer'
]
