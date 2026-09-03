import sys
import uuid
from app.database import SessionLocal, engine
from app.dependencies import get_search_service
from app.models.dataset import Dataset
from app.models.asset import Asset

def test():
    db = SessionLocal()
    search_svc = get_search_service()
    
    # Just grab any workspace that has a dataset
    dataset = db.query(Dataset).first()
    if not dataset:
        print("No datasets found in DB.")
        return
        
    workspace_id = dataset.workspace_id
    print(f"Using workspace: {workspace_id}")
    
    try:
        res = search_svc.discover_datasets(db, workspace_id, "")
        print("Empty query result:", res)
    except Exception as e:
        print("Empty query ERROR:", e)
        
    try:
        res = search_svc.discover_datasets(db, workspace_id, "test")
        print("Test query result:", res)
    except Exception as e:
        print("Test query ERROR:", e)

if __name__ == "__main__":
    test()
