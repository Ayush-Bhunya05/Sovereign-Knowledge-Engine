import logging
from typing import Literal, Any
import json
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class QueryPlannerError(Exception):
    pass

class QueryPlannerService:
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    def route_query(self, query: str) -> Literal["SQL", "RAG", "HYBRID", "AMBIGUOUS"]:
        """Determine the best strategy for a user query."""
        prompt = PromptTemplate(
            input_variables=["query"],
            template='''You are an AI router for a document and dataset query system. Given the user query, determine the required data source strategy.
Output ONLY one of the following exact words:
- SQL: If the query asks for aggregations, counting, filtering tabular data, rows, columns, or structured metrics (e.g. "What is the average score?", "tell me about the rows...").
- RAG: If the query asks for concepts, text explanations, summaries, or unstructured information from documents (e.g. "What does the policy say about X?").
- HYBRID: If the query requires BOTH unstructured text and structured data to answer.
- AMBIGUOUS: Only if the query is a greeting, completely unclear, makes no sense, or is impossible to interpret (e.g. "hey", "asdf"). Do NOT output AMBIGUOUS for minor typos.

User Query: {query}
Routing Decision:'''
        )
        try:
            chain = prompt | self.llm
            response = chain.invoke({"query": query})
            content = response.content
            if isinstance(content, list):
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
            result = content.strip().upper()
            logger.info(f"LLM Routing Output for '{query}': {result}")
            if result in ["SQL", "RAG", "HYBRID", "AMBIGUOUS"]:
                return result
            logger.warning("Unrecognized routing result '%s', defaulting to AMBIGUOUS", result)
            return "AMBIGUOUS"
        except Exception as e:
            logger.error("LLM routing failed: %s", e)
            return "AMBIGUOUS"

    def generate_sql(self, query: str, datasets: list[dict[str, Any]]) -> str:
        """Generate PostgreSQL using Gemini."""
        if not datasets:
            raise QueryPlannerError("No relevant datasets found for SQL generation.")

        schema_texts = []
        for ds in datasets:
            schema_texts.append(f"Table Name: {ds['table_name']}\nColumns: {json.dumps(ds['schema_definition'])}")
        schema_context = "\n\n".join(schema_texts)

        prompt = PromptTemplate(
            input_variables=["query", "schema_context"],
            template='''You are a PostgreSQL expert. Write a valid PostgreSQL query to answer the user's question.
You MUST ONLY use the tables and columns provided in the schema context below.
Do not use Markdown formatting for the output, just output the raw SQL query.
Do NOT include semicolons at the end of the query.

SCHEMA CONTEXT:
{schema_context}

USER QUESTION: {query}

RAW SQL QUERY:'''
        )
        try:
            chain = prompt | self.llm
            response = chain.invoke({"query": query, "schema_context": schema_context})
            content = response.content
            if isinstance(content, list):
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
            result = content.strip()
            # Clean up markdown formatting if the LLM disobeyed
            if result.startswith("```sql"):
                result = result[6:]
            if result.endswith("```"):
                result = result[:-3]
            return result.strip()
        except Exception as e:
            logger.error("LLM SQL generation failed: %s", e)
            raise QueryPlannerError(f"Failed to generate SQL: {e}")

    def validate_sql(self, sql: str, allowed_tables: set[str]) -> str:
        """Parse AST with sqlglot and enforce strict security constraints."""
        try:
            parsed = sqlglot.parse(sql, read="postgres")
            if not parsed:
                raise QueryPlannerError("Failed to parse SQL statement.")
            
            # Enforce single statement
            if len(parsed) > 1:
                raise QueryPlannerError("Multiple SQL statements are not allowed.")
            ast = parsed[0]

            # 1. Enforce SELECT only
            if not isinstance(ast, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
                raise QueryPlannerError("Only SELECT statements are allowed. DML/DDL is strictly forbidden.")

            # 2. Recursive Table Whitelist Validation (checks subqueries, CTEs, UNIONs)
            found_tables = set()
            for table_node in ast.find_all(exp.Table):
                found_tables.add(table_node.name)

            for table in found_tables:
                if table not in allowed_tables:
                    raise QueryPlannerError(f"Unauthorized or unknown table referenced: {table}")

            # 3. Limit Enforcement
            # Ensure there is a LIMIT to prevent massive result sets
            if not ast.args.get("limit"):
                # Append LIMIT 100
                ast = ast.limit(100)
            else:
                # Cap existing LIMIT to 100
                limit_val = ast.args.get("limit").expression
                if isinstance(limit_val, exp.Literal) and limit_val.is_int:
                    if int(limit_val.name) > 100:
                        ast.set("limit", exp.Limit(expression=exp.Literal.number(100)))

            return ast.sql(dialect="postgres")

        except ParseError as e:
            logger.error("SQL Parse error: %s", e)
            raise QueryPlannerError("Generated SQL is syntactically invalid.")

    def execute_sql(self, sql: str, engine) -> list[dict[str, Any]]:
        """Execute the validated SQL using a read-only transaction and role."""
        from sqlalchemy import text
        try:
            with engine.begin() as conn:
                # 1. Set role to rag_readonly for strict permissions
                conn.execute(text("SET LOCAL ROLE rag_readonly;"))
                # 2. Enforce read-only transaction
                conn.execute(text("SET TRANSACTION READ ONLY;"))
                # 3. Enforce statement timeout (e.g. 5 seconds)
                conn.execute(text("SET statement_timeout = '5s';"))
                
                result = conn.execute(text(sql))
                
                # 4. Result size limit check on Python side
                rows = []
                for idx, row in enumerate(result.mappings()):
                    if idx >= 1000:
                        logger.warning("Query returned more than 1000 rows, truncating.")
                        break
                    rows.append(dict(row))
                    
                return rows
        except Exception as e:
            logger.error("SQL execution failed: %s", e)
            raise QueryPlannerError(f"Failed to execute query: {e}")

    def synthesize_hybrid(self, query: str, sql_results: list[dict[str, Any]], text_chunks: list[dict[str, Any]]) -> str:
        """Synthesize final answer using SQL results and text chunks, with citations."""
        context_parts = []
        if sql_results:
            context_parts.append("DATABASE QUERY RESULTS:\n" + json.dumps(sql_results[:50], default=str))
        
        if text_chunks:
            chunk_texts = []
            for i, chunk in enumerate(text_chunks):
                chunk_texts.append(f"[Document {i+1}: {chunk.get('filename', 'Unknown')}]\n{chunk.get('chunk_text', '')}")
            context_parts.append("TEXT DOCUMENT EXCERPTS:\n" + "\n\n".join(chunk_texts))
            
        context_str = "\n\n".join(context_parts)
        
        prompt = PromptTemplate(
            input_variables=["query", "context_str"],
            template='''You are an AI data analyst. Answer the user's question using ONLY the context provided.
The context may contain structured database query results and unstructured text document excerpts.

If the answer is not contained in the context, say "I don't have enough information to answer that."

IMPORTANT RULES FOR CITATIONS:
- Whenever you state a fact from the context, you MUST provide a citation.
- For structured data, cite the table or dataset conceptually if apparent.
- For text documents, cite the document name using brackets, e.g., [Document 1: file.pdf].
- Do not make up citations.

CONTEXT:
{context_str}

USER QUESTION: {query}

FINAL ANSWER:'''
        )
        try:
            chain = prompt | self.llm
            response = chain.invoke({"query": query, "context_str": context_str})
            content = response.content
            if isinstance(content, list):
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
            result = content.strip()
            return result
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            return "Failed to synthesize answer."
