"""
ScienceClaw Core - Skill Discovery and Execution System

Provides:
- SkillRegistry: Discover and catalog all available skills
- SkillExecutor: Universal execution engine for any skill type
- LLMSkillSelector: Intelligent skill selection using LLM reasoning
- LLMTopicAnalyzer: LLM-powered topic analysis (replaces hardcoded keywords)
- DependencyGraph / SkillNode: DAG-based skill orchestration (AgentSkillOS-inspired)
- SkillTreeSearcher: Hierarchical tree search for skill discovery (AgentSkillOS-inspired)
"""

from .skill_registry import SkillRegistry, get_registry
from .skill_executor import SkillExecutor, get_executor
try:
    from .skill_selector import LLMSkillSelector, get_selector
except Exception:  # Optional dependency chain (e.g., pydantic) may be unavailable.
    LLMSkillSelector = None
    get_selector = None
try:
    from .topic_analyzer import LLMTopicAnalyzer, get_analyzer
except Exception:
    LLMTopicAnalyzer = None
    get_analyzer = None
from .skill_dag import (
    DependencyGraph, SkillNode, ExecutionPhase,
    NodeStatus, NodeFailureReason, SkillType,
    build_graph_from_plan,
)
from .skill_tree_searcher import (
    SkillTreeSearcher, Skill, TreeNode, SearchResult,
    build_capability_tree, search_skills_for_topic,
)

__all__ = [
    # Existing
    'SkillRegistry',
    'SkillExecutor',
    'LLMSkillSelector',
    'LLMTopicAnalyzer',
    'get_registry',
    'get_executor',
    'get_selector',
    'get_analyzer',
    # DAG
    'DependencyGraph',
    'SkillNode',
    'ExecutionPhase',
    'NodeStatus',
    'NodeFailureReason',
    'SkillType',
    'build_graph_from_plan',
    # Tree searcher
    'SkillTreeSearcher',
    'Skill',
    'TreeNode',
    'SearchResult',
    'build_capability_tree',
    'search_skills_for_topic',
]
