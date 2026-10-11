import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.models.dataset import Dataset
from app.models.folder import Folder
from app.models.asset import Asset
from app.services.orchestrator.context import ScopeContext

logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """Raised when a tool fails in a way the LLM should know about."""
    pass


class WorkspaceTools:
    """Registry of bounded capabilities for the AI Orchestrator."""

    def __init__(self, db: Session, engine, scope: ScopeContext, search_service, asset_service):
        self.db = db
        self.engine = engine
        self.scope = scope
        self.search_service = search_service
        self.asset_service = asset_service

    def get_workspace_structure(self) -> str:
        """Returns the high-level folder structure of the workspace."""
        # Query folders directly for the workspace
        folders = self.db.query(Folder).filter(Folder.workspace_id == self.scope.workspace_id).all()
        if not folders:
            return "No folders found in this workspace."
        
        result = "Workspace Folders:\n"
        for f in folders:
            result += f"- {f.name} (ID: {f.id})\n"
        return result

    def get_folder_contents(self, target_folder_id: str = None) -> str:
        """Returns the files inside a specific folder."""
        f_id = target_folder_id or (str(self.scope.folder_id) if self.scope.folder_id else None)
        
        query = self.db.query(Asset).filter(Asset.workspace_id == self.scope.workspace_id)
        if f_id:
            try:
                folder_uuid = uuid.UUID(f_id)
                query = query.filter(Asset.folder_id == folder_uuid)
            except ValueError:
                return "Invalid folder_id format."
        else:
            query = query.filter(Asset.folder_id == None) # root files
            
        assets = query.all()
        if not assets:
            return "No files found in this location."
            
        result = "Files:\n"
        for a in assets:
            result += f"- {a.filename} (Type: {a.document_type}, Asset ID: {a.id})\n"
        return result

    def get_file_metadata(self, asset_id: str) -> str:
        """Returns metadata about a specific file, such as size, chunk count, processing status."""
        try:
            a_id = uuid.UUID(asset_id)
        except ValueError:
            return "Invalid asset_id format."
            
        asset = self.db.query(Asset).filter(
            Asset.id == a_id,
            Asset.workspace_id == self.scope.workspace_id
        ).first()
        
        if not asset:
            return f"Asset {asset_id} not found or access denied."
            
        return f"File Metadata:\nFilename: {asset.filename}\nType: {asset.document_type}\nSize: {asset.file_size} bytes\nStatus: {asset.processing_status}\nChunks: {asset.chunk_count}"

    def discover_datasets(self, query: str) -> str:
        """Discovers structured datasets relevant to a query using metadata/semantic matching."""
        datasets = self.search_service.discover_datasets(
            db=self.db,
            workspace_id=self.scope.workspace_id,
            query=query,
            folder_id=self.scope.folder_id,
            asset_id=self.scope.asset_id,
            top_k=5
        )
        if not datasets:
            return "No structured datasets found matching the query."
            
        res = "Relevant Datasets Found:\n"
        for ds in datasets:
            res += f"- Dataset ID: {ds['dataset_id']} | File: {ds['filename']} | Table: {ds['table_name']} | Relevance: {ds['similarity_score']:.2f}\n"
        return res

    def get_dataset_schema(self, dataset_id: str) -> str:
        """Returns the exact SQL schema definition for a dataset ID."""
        try:
            d_id = uuid.UUID(dataset_id)
        except ValueError:
            return "Invalid dataset_id format."
            
        # Scope enforcement
        query = self.db.query(Dataset).filter(Dataset.id == d_id, Dataset.workspace_id == self.scope.workspace_id)
        if self.scope.folder_id:
            query = query.filter(Dataset.folder_id == self.scope.folder_id)
        if self.scope.asset_id:
            query = query.filter(Dataset.asset_id == self.scope.asset_id)
            
        ds = query.first()
        if not ds:
            return f"Dataset {dataset_id} not found or access denied. Ensure you are using the exact Dataset ID returned by discover_datasets."
            
        return f"Table Name: {ds.table_name}\nSchema: {json.dumps(ds.schema_definition)}"

    def get_dataset_profile(self, dataset_id: str) -> str:
        """Returns a high-level statistical overview of the dataset without generating SQL."""
        try:
            d_id = uuid.UUID(dataset_id)
        except ValueError:
            return "Invalid dataset_id format."
            
        # Scope enforcement
        query = self.db.query(Dataset).filter(Dataset.id == d_id, Dataset.workspace_id == self.scope.workspace_id)
        if self.scope.folder_id:
            query = query.filter(Dataset.folder_id == self.scope.folder_id)
        if self.scope.asset_id:
            query = query.filter(Dataset.asset_id == self.scope.asset_id)
            
        ds = query.first()
        if not ds:
            return f"Dataset {dataset_id} not found or access denied. Ensure you are using the exact Dataset ID returned by discover_datasets."
            
        return f"Dataset Profile Overview:\nTable: {ds.table_name}\nRow Count: {ds.row_count}\nSchema Profile:\n{json.dumps(ds.schema_definition)}"

    def search_documents(self, query: str, top_k: int = 5) -> str:
        """Performs semantic RAG search across documents to answer unstructured conceptual questions. Increase top_k if you need more exhaustive lists or context."""
        results = self.search_service.search_documents(
            db=self.db,
            workspace_id=self.scope.workspace_id,
            query=query,
            folder_id=self.scope.folder_id,
            asset_id=self.scope.asset_id,
            top_k=top_k
        )
        if not results:
            return "No relevant text documents found."
            
        res = "Relevant Document Excerpts:\n\n"
        for i, r in enumerate(results):
            res += f"[Source: {r['filename']}, Page: {r.get('page_number', 'N/A')}]\n{r['chunk_text']}\n\n"
        return res
        
    def analyze_vision(self, query: str, asset_id: str) -> str:
        """Analyzes an image or diagram structurally."""
        try:
            a_id = uuid.UUID(asset_id)
        except ValueError:
            return "Invalid asset_id format."
            
        # Scope enforcement check!
        query_check = self.db.query(Asset).filter(
            Asset.id == a_id,
            Asset.workspace_id == self.scope.workspace_id
        )
        if self.scope.folder_id:
            query_check = query_check.filter(Asset.folder_id == self.scope.folder_id)
        # We don't check scope.asset_id here, because if the user is in Folder scope, they can pass ANY asset_id inside that folder.
        # But if they are in Asset scope, they can ONLY pass that exact asset_id.
        if self.scope.asset_id:
            if str(self.scope.asset_id) != str(a_id):
                return "Access denied: You are scoped to a different asset."
                
        asset = query_check.first()
        if not asset:
            return "Access denied: Asset not found in active scope."
            
        return f"[Source: {asset.filename}]\nVisual inspection is currently unavailable in this environment. Do not pretend to have seen the diagram. Explicitly state that visual inspection of the image/diagram failed or is unsupported."

    def web_search(self, query: str) -> str:
        """Retrieves external information from the web when workspace info is insufficient or web search is explicitly requested. DO NOT use this if the user says 'answer only from uploaded documents'."""
        try:
            from duckduckgo_search import DDGS
            import time
            
            results = []
            with DDGS() as ddgs:
                raw_results = ddgs.text(query, max_results=3)
                
            for r in raw_results:
                results.append(
                    f"Title: {r.get('title', 'No Title')}\n"
                    f"URL: {r.get('href', 'No URL')}\n"
                    f"Snippet: {r.get('body', 'No Snippet')}\n"
                )
                
            if not results:
                return f"No web search results found for: {query}"
                
            return f"[Source: Web Search]\nSearched for: {query}\n\nResults:\n" + "\n---\n".join(results)
            
        except ImportError:
            return "Web search is currently disabled (duckduckgo-search not installed)."
        except Exception as e:
            return f"Web search failed due to a timeout or error: {e}. Do not try searching again unless explicitly requested."

    def query_dataset(self, sql_query: str) -> str:
        """Generates and executes analytical SQL on structured tables. ONLY use valid PostgreSQL."""
        # 1. Fetch allowed table names for this scope
        dataset_query = self.db.query(Dataset.table_name).filter(Dataset.workspace_id == self.scope.workspace_id)
        if self.scope.folder_id:
            dataset_query = dataset_query.filter(Dataset.folder_id == self.scope.folder_id)
        if self.scope.asset_id:
            dataset_query = dataset_query.filter(Dataset.asset_id == self.scope.asset_id)
        
        allowed_tables = {row[0] for row in dataset_query.all()}
        if not allowed_tables:
            return "No structured datasets available in this scope."

        # 2. Validate SQL with sqlglot
        try:
            parsed = sqlglot.parse(sql_query, read="postgres")
            if not parsed:
                return "Error: Failed to parse SQL statement."
            
            if len(parsed) > 1:
                return "Error: Multiple SQL statements are not allowed."
            ast = parsed[0]

            if not isinstance(ast, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
                return "Error: Only SELECT statements are allowed. DML/DDL is strictly forbidden."

            found_tables = set()
            for table_node in ast.find_all(exp.Table):
                found_tables.add(table_node.name)

            for table in found_tables:
                if table not in allowed_tables:
                    return f"Error: Unauthorized or unknown table referenced: {table}"

            if not ast.args.get("limit"):
                ast = ast.limit(100)
            else:
                limit_val = ast.args.get("limit").expression
                if isinstance(limit_val, exp.Literal) and limit_val.is_int:
                    if int(limit_val.name) > 100:
                        ast.set("limit", exp.Limit(expression=exp.Literal.number(100)))

            validated_sql = ast.sql(dialect="postgres")
        except ParseError as e:
            return f"Error: Generated SQL is syntactically invalid. Details: {e}"
        except Exception as e:
            return f"Error: Validation failed. Details: {e}"

        # 3. Execute SQL
        from sqlalchemy import text
        try:
            with self.engine.begin() as conn:
                try:
                    conn.execute(text("SET LOCAL ROLE rag_readonly;"))
                except Exception:
                    pass
                conn.execute(text("SET TRANSACTION READ ONLY;"))
                conn.execute(text("SET statement_timeout = '5s';"))
                
                result = conn.execute(text(validated_sql))
                
                rows = []
                for idx, row in enumerate(result.mappings()):
                    if idx >= 1000:
                        break
                    rows.append(dict(row))
                    
                if not rows:
                    return "Query executed successfully but returned 0 rows."
                    
                # Handle empty aggregation (1 row, all values None)
                if len(rows) == 1 and all(val is None for val in rows[0].values()):
                    return "Query executed successfully but no matching records were found (aggregation returned NULL)."
                    
                return f"SQL Executed:\n{validated_sql}\n\nResults (JSON):\n{json.dumps(rows, default=str)}"
        except Exception as e:
            return f"Error: Database execution failed. Details: {e}"
