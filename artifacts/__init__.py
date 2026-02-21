"""
Artifact layer for scienceclaw agent system.

Wraps every skill output in a versioned, addressable artifact and enforces
domain gating so agents can only claim findings grounded in artifacts from
their skill domain.
"""

from artifacts.artifact import Artifact, ArtifactStore, SKILL_DOMAIN_MAP, ArtifactDomainError

__all__ = ["Artifact", "ArtifactStore", "SKILL_DOMAIN_MAP", "ArtifactDomainError"]
