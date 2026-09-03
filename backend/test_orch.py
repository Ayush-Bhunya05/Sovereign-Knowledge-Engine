import sys
import uuid
from app.database import SessionLocal, engine
from app.dependencies import get_agentic_orchestrator_service, get_search_service, get_asset_service
from app.services.orchestrator.context import ScopeContext
from app.services.orchestrator.tools import WorkspaceTools

def test():
    db = SessionLocal()
    workspace_id = uuid.UUID("48d2f8c6-9816-4ba6-9e9e-4b7197114831")
    search_svc = get_search_service()
    asset_svc = get_asset_service()
    orch_svc = get_agentic_orchestrator_service()
    
    scope = ScopeContext(workspace_id=workspace_id, folder_id=None, asset_id=None)
    tools = WorkspaceTools(db, engine, scope, search_svc, asset_svc)
    
    # query = "what files are there in this workspace"
    query = "okay now tell me about the rows in this file"
    
    print("Testing discover_datasets...")
    try:
        print(tools.discover_datasets("rows in this file"))
    except Exception as e:
        print("discover_datasets ERROR:", e)

    print("Testing orchestrator loop...")
    res = orch_svc.ask(query, tools)
    print("RESULT:", res)

if __name__ == "__main__":
    test()
