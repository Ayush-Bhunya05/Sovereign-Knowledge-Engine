"""Structured Data Ingestion Service — handles CSV and XLSX."""

import logging
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.dataset import Dataset
from app.models.asset import Asset
from app.database import engine
from app.services.embedding_service import EmbeddingService
from app.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)

class StructuredDataService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        milvus_service: MilvusService,
    ):
        self.embedding = embedding_service
        self.milvus = milvus_service

    def _sanitize_table_name(self, name: str) -> str:
        """Create a safe PostgreSQL identifier."""
        # Replace non-alphanumeric with underscore
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        # Remove consecutive underscores
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        # Ensure it doesn't start with a number
        if clean_name and clean_name[0].isdigit():
            clean_name = 't_' + clean_name
        return clean_name or 'dataset'

    def _generate_column_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate deterministic stats for the dataset columns."""
        stats = {}
        for col in df.columns:
            series = df[col]
            col_stats = {
                "type": str(series.dtype),
                "null_count": int(series.isna().sum())
            }
            # Only do unique count if not a float type and not all unique
            if not pd.api.types.is_float_dtype(series):
                nunique = series.nunique()
                col_stats["unique_count"] = int(nunique)
                
            if pd.api.types.is_numeric_dtype(series) and not series.empty:
                col_stats["min"] = float(series.min()) if pd.notnull(series.min()) else None
                col_stats["max"] = float(series.max()) if pd.notnull(series.max()) else None
                
            stats[str(col)] = col_stats
        return stats

    def _generate_schema_definition(self, df: pd.DataFrame) -> Dict[str, str]:
        """Map pandas dtypes to generic SQL types for the LLM."""
        schema = {}
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                schema[col] = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                schema[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                schema[col] = "date/time"
            elif pd.api.types.is_bool_dtype(dtype):
                schema[col] = "boolean"
            else:
                schema[col] = "text"
        return schema

    def _generate_summary(self, name: str, row_count: int, schema: Dict[str, str]) -> str:
        """Generate deterministic text summary for Milvus embedding."""
        cols_text = ", ".join([f"{col} -> {typ}" for col, typ in schema.items()])
        return f"Dataset: {name} | Rows: {row_count} | Columns: {cols_text}"

    def process_structured_asset(self, db: Session, asset_id: uuid.UUID) -> None:
        """Ingest a CSV or XLSX into a physical PostgreSQL table and register it as a Dataset."""
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.error("Asset %s not found for structured ingestion.", asset_id)
            return

        file_path = Path(asset.storage_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("Starting structured ingestion for asset %s", asset_id)
        
        # 1. Parse File
        ext = file_path.suffix.lower()
        dfs = {} # dict of sheet_name -> DataFrame
        parser_metadata = {"engine": "pandas"}

        try:
            if ext == ".csv":
                df = pd.read_csv(file_path)
                dfs["Sheet1"] = df
                asset.document_type = "CSV"
            elif ext == ".xlsx":
                # openpyxl data_only=True ensures we read calculated values, not formula text
                xls = pd.ExcelFile(file_path, engine="openpyxl")
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    dfs[sheet_name] = df
                parser_metadata["engine"] = "pandas/openpyxl (data_only=True behavior via openpyxl evaluation if cached)"
                asset.document_type = "Excel"
            else:
                raise ValueError(f"Unsupported structured file type: {ext}")
        except Exception as e:
            logger.exception("Failed to parse structured file %s", file_path)
            raise e

        # 2. Process each dataset (sheet/file)
        for sheet_name, df in dfs.items():
            if df.empty:
                logger.warning("Sheet %s is empty, skipping.", sheet_name)
                continue

            # Clean column names (strip whitespace, lowercase, replace spaces)
            df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
            
            # Generate identifiers
            short_id = str(asset_id)[:8]
            base_name = asset.filename.split('.')[0]
            sanitized_base = self._sanitize_table_name(base_name)
            sanitized_sheet = self._sanitize_table_name(sheet_name)
            
            # Form: structured_{short_id}_{sanitized_base}_{sanitized_sheet}
            # Limit length to prevent PostgreSQL identifier truncation (max 63)
            table_name = f"structured_{short_id}_{sanitized_base}_{sanitized_sheet}"[:60]
            dataset_name = f"{base_name} - {sheet_name}" if len(dfs) > 1 else base_name

            row_count = len(df)
            col_count = len(df.columns)
            
            schema_def = self._generate_schema_definition(df)
            col_stats = self._generate_column_stats(df)
            summary = self._generate_summary(dataset_name, row_count, schema_def)

            dataset_id = uuid.uuid4()
            dataset = Dataset(
                id=dataset_id,
                asset_id=asset.id,
                workspace_id=asset.workspace_id,
                folder_id=asset.folder_id,
                name=dataset_name,
                table_name=table_name,
                source_type=ext.replace(".", ""),
                source_sheet=sheet_name if ext == ".xlsx" else None,
                row_count=row_count,
                column_count=col_count,
                schema_definition=schema_def,
                column_stats=col_stats,
                summary=summary,
                parser_metadata=parser_metadata
            )

            # 3. Create physical table & ingest data
            try:
                # Use engine to write to DB, replace if exists (for re-runs)
                df.to_sql(table_name, con=engine, if_exists="replace", index=False)
                
                # 4. Apply read_only permissions explicitly (if role exists)
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f'GRANT SELECT ON TABLE "{table_name}" TO rag_readonly;'))
                except Exception as perm_err:
                    logger.warning("Could not grant SELECT to rag_readonly: %s", perm_err)
                
                # Register dataset
                db.add(dataset)
                db.commit()
            except Exception as e:
                logger.exception("Failed to write physical table or register dataset: %s", table_name)
                db.rollback()
                # Rollback physical table if it failed halfway
                with engine.begin() as conn:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'))
                raise e

            # 5. Embed summary to Milvus
            try:
                emb_res = self.embedding.embed_texts([summary])
                if emb_res.vectors:
                    self.milvus.insert_vectors(
                        chunk_ids=[str(dataset_id)], # Use dataset_id as chunk_id for direct tracing
                        asset_id=str(asset_id),
                        vectors=emb_res.vectors
                    )
            except Exception as e:
                logger.exception("Failed to embed dataset summary into Milvus for %s", dataset_id)
                db.rollback()
                with engine.begin() as conn:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'))
                db.delete(dataset)
                db.commit()
                self.milvus.delete_asset_vectors(str(asset_id))
                raise e

        # Final asset update
        # Compile a markdown summary for the UI to display in the Extracted Text tab
        extracted_text_lines = ["# Structured Dataset Metadata\n"]
        created_datasets = db.query(Dataset).filter(Dataset.asset_id == asset_id).all()
        for dataset in created_datasets:
            extracted_text_lines.append(f"### {dataset.name}")
            extracted_text_lines.append(f"- **Table Name:** `{dataset.table_name}`")
            extracted_text_lines.append(f"- **Row Count:** {dataset.row_count}")
            extracted_text_lines.append(f"- **Column Count:** {dataset.column_count}")
            extracted_text_lines.append("\n**Schema Definition:**")
            for col, typ in dataset.schema_definition.items():
                extracted_text_lines.append(f"- `{col}`: {typ}")
            extracted_text_lines.append("\n---\n")
            
        asset.extracted_text = "\n".join(extracted_text_lines)
        asset.chunk_count = len(created_datasets)
        asset.processing_status = "completed"
        db.commit()
        logger.info("Structured ingestion completed for asset %s", asset_id)
