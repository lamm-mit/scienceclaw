"""
ScienceClaw Core - Skill Discovery and Execution System

Provides:
- SkillRegistry: Discover and catalog all available skills
- SkillExecutor: Universal execution engine for any skill type
- LLMSkillSelector: Intelligent skill selection using LLM reasoning
- LLMTopicAnalyzer: LLM-powered topic analysis (replaces hardcoded keywords)

This enables dynamic skill discovery instead of hardcoded tool chains.
"""

from .skill_registry import SkillRegistry, get_registry
from .skill_executor import SkillExecutor, get_executor
from .skill_selector import LLMSkillSelector, get_selector
from .topic_analyzer import LLMTopicAnalyzer, get_analyzer

__all__ = [
    'SkillRegistry',
    'SkillExecutor',
    'LLMSkillSelector',
    'LLMTopicAnalyzer',
    'get_registry',
    'get_executor',
    'get_selector',
    'get_analyzer'
]
