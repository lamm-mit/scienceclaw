"""
ScienceClaw Agent Setup

Agent initialization and configuration management.

Components:
- soul_generator: Generate SOUL.md for agent
"""

from .soul_generator import generate_soul_md, save_soul_md

__all__ = [
    'generate_soul_md',
    'save_soul_md',
]
