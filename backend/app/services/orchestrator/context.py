from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass
class ScopeContext:
    """Security boundaries enforced by the Orchestrator."""
    workspace_id: UUID
    folder_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
