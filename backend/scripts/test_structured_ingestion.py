import uuid
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.dependencies import get_ingestion_orchestrator
from app.models.asset import Asset
from app.models.workspace import Workspace

def test():
    db = SessionLocal()
    try:
        # Create dummy workspace
        ws_id = uuid.uuid4()
        ws = Workspace(id=ws_id, name="Test WS")
        db.add(ws)
        db.commit()

        # Create dummy CSV file
        test_file = Path("test_data.csv")
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "score": [90.5, 88.0, 95.2]})
        df.to_csv(test_file, index=False)

        # Create asset
        asset_id = uuid.uuid4()
        asset = Asset(
            id=asset_id,
            workspace_id=ws_id,
            filename="test_data.csv",
            asset_type="structured",
            document_type="CSV",
            mime_type="text/csv",
            file_size=os.path.getsize(test_file),
            processing_status="pending",
            storage_path=str(test_file.absolute()),
            chunk_count=0,
            has_ocr=False
        )
        db.add(asset)
        db.commit()

        # Run ingestion
        orchestrator = get_ingestion_orchestrator()
        orchestrator.process_asset(db, asset_id)

        # Verify
        db.refresh(asset)
        print("Asset status:", asset.processing_status)
        
        from app.models.dataset import Dataset
        dataset = db.query(Dataset).filter(Dataset.asset_id == asset_id).first()
        if dataset:
            print("Dataset created:", dataset.table_name)
            print("Row count:", dataset.row_count)
            print("Schema:", dataset.schema_definition)
            print("Stats:", dataset.column_stats)
            
            # Check physical table
            with engine.begin() as conn:
                res = conn.execute(text(f'SELECT count(*) FROM "{dataset.table_name}"')).scalar()
                print(f"Physical table row count: {res}")
        else:
            print("Dataset NOT created!")

    finally:
        db.rollback()
        db.close()
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    test()
