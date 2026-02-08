"""
ScienceClaw Autonomous Control Loop

This package contains the autonomous loop controller that orchestrates the
agent's scientific investigation cycles.

Components:
- LoopController: Main orchestrator for autonomous investigation cycles
"""

from .loop_controller import AutonomousLoopController

__all__ = ['AutonomousLoopController']
