"""Search endpoints v2."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_search_service
from app.schemas.search import SearchQuery, SearchResultItem
from app.services.search_service import SearchService
from app.services.workspace_service import workspace_service
from app.services.folder_service import folder_service
from app.services.asset_service import AssetService
from app.dependencies import get_asset_service, get_query_planner_service, get_agentic_orchestrator_service

router = APIRouter(prefix="/workspaces/{workspace_id}/search", tags=["Search (v2)"])


@router.post("", response_model=list[SearchResultItem])
def search_workspace(
    workspace_id: uuid.UUID,
    query: SearchQuery,
    db: Session = Depends(get_db),
    search_svc: SearchService = Depends(get_search_service),
    asset_svc: AssetService = Depends(get_asset_service),
):
    """Semantic search across a workspace. Optionally restricted to folder or asset."""
    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")

    if query.folder_id and not folder_service.get(db, workspace_id, query.folder_id):
        raise HTTPException(status_code=404, detail="Folder not found in workspace")

    if query.asset_id:
        asset = asset_svc.get(db, query.asset_id)
        if not asset or asset.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Asset not found in workspace")

    try:
        # Note: the existing UI might expect SearchResultItem which matches AssetChunk response
        results = search_svc.search(
            db=db,
            workspace_id=workspace_id,
            query=query.query,
            folder_id=query.folder_id,
            asset_id=query.asset_id,
            top_k=query.top_k,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask_legacy")
def ask_question_legacy(
    workspace_id: uuid.UUID,
    query: SearchQuery,
    db: Session = Depends(get_db),
    search_svc: SearchService = Depends(get_search_service),
    asset_svc: AssetService = Depends(get_asset_service),
    query_planner = Depends(get_query_planner_service)
):
    """Hybrid RAG + SQL Synthesis endpoint."""
    from app.database import engine
    from app.services.query_planner_service import QueryPlannerService, QueryPlannerError
    
    qp_svc: QueryPlannerService = query_planner

    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")

    if query.folder_id and not folder_service.get(db, workspace_id, query.folder_id):
        raise HTTPException(status_code=404, detail="Folder not found in workspace")

    if query.asset_id:
        asset = asset_svc.get(db, query.asset_id)
        if not asset or asset.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Asset not found in workspace")

    try:
        # 1. Route the query
        strategy = qp_svc.route_query(query.query)
        if strategy == "AMBIGUOUS":
            return {
                "answer": "Your query is too ambiguous or unclear. Could you please provide more details?",
                "strategy": strategy,
                "citations": []
            }

        # 2. Scope Enforcement & Semantic Discovery (Hybrid Discovery)
        search_results = search_svc.search_hybrid(
            db=db,
            workspace_id=workspace_id,
            query=query.query,
            folder_id=query.folder_id,
            asset_id=query.asset_id,
            top_k=query.top_k
        )
        chunks = search_results["chunks"]
        datasets = search_results["datasets"]

        sql_results = []
        sql_query = None
        
        # 3. SQL Generation & Execution
        if strategy in ["SQL", "HYBRID"] and datasets:
            try:
                allowed_tables = {ds["table_name"] for ds in datasets}
                generated_sql = qp_svc.generate_sql(query.query, datasets)
                sql_query = qp_svc.validate_sql(generated_sql, allowed_tables)
                sql_results = qp_svc.execute_sql(sql_query, engine)
            except QueryPlannerError as e:
                # If SQL fails, we gracefully fall back to RAG if strategy is HYBRID
                if strategy == "SQL":
                    return {
                        "answer": f"I couldn't safely generate or execute a query for this question: {e}",
                        "strategy": strategy,
                        "citations": []
                    }

        # 4. Final Synthesis
        answer = qp_svc.synthesize_hybrid(query.query, sql_results, chunks)
        
        return {
            "answer": answer,
            "strategy": strategy,
            "sql_query": sql_query,
            "sql_results": sql_results[:10] if sql_results else None, # Return sample for UI
            "citations": {
                "datasets": [ds["filename"] for ds in datasets],
                "documents": [c["filename"] for c in chunks]
            }
        }
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Ask legacy endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
def ask_question_orchestrated(
    workspace_id: uuid.UUID,
    query: SearchQuery,
    db: Session = Depends(get_db),
    search_svc: SearchService = Depends(get_search_service),
    asset_svc: AssetService = Depends(get_asset_service),
    orchestrator = Depends(get_agentic_orchestrator_service)
):
    """General Workspace Intelligence endpoint using Bounded Tool Loop."""
    from app.services.orchestrator.engine import AgenticOrchestratorService
    from app.services.orchestrator.tools import WorkspaceTools
    from app.services.orchestrator.context import ScopeContext
    from app.database import engine
    
    orch_svc: AgenticOrchestratorService = orchestrator

    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")

    if query.folder_id and not folder_service.get(db, workspace_id, query.folder_id):
        raise HTTPException(status_code=404, detail="Folder not found in workspace")

    if query.asset_id:
        asset = asset_svc.get(db, query.asset_id)
        if not asset or asset.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Asset not found in workspace")

    try:
        # Create strict scope boundary for this request
        scope = ScopeContext(
            workspace_id=workspace_id,
            folder_id=query.folder_id,
            asset_id=query.asset_id
        )
        
        # Instantiate tools properly bound to the active scope
        tools = WorkspaceTools(
            db=db,
            engine=engine,
            scope=scope,
            search_service=search_svc,
            asset_service=asset_svc
        )

        # Execute orchestrator
        return orch_svc.ask(query.query, tools)

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Ask orchestrator endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))

