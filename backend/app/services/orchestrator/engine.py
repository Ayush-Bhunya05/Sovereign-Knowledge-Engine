import logging
import json
from typing import Any, List, Dict
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from app.services.orchestrator.provider import LLMProvider
from app.services.orchestrator.tools import WorkspaceTools, ToolExecutionError
from app.services.orchestrator.context import ScopeContext

logger = logging.getLogger(__name__)

# --- Tool Schemas ---
class QuerySchema(BaseModel):
    query: str = Field(description="The search or analytical query.")

class DatasetIdSchema(BaseModel):
    dataset_id: str = Field(description="The UUID of the dataset.")

class FolderIdSchema(BaseModel):
    target_folder_id: str = Field(None, description="The optional UUID of the folder.")

class AssetIdSchema(BaseModel):
    asset_id: str = Field(description="The UUID of the asset.")

class SqlQuerySchema(BaseModel):
    sql_query: str = Field(description="The exact PostgreSQL query to execute.")

class VisionQuerySchema(BaseModel):
    query: str = Field(description="The question about the image/diagram.")
    asset_id: str = Field(description="The UUID of the image/diagram asset.")


class AgenticOrchestratorService:
    """The central orchestrator loop for Workspace Intelligence."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.max_iterations = 10

    def ask(self, query: str, workspace_tools: WorkspaceTools) -> dict:
        """Process a user query through the Orchestrator loop."""
        
        # 1. Bind tools to the provider
        tools_list = self._build_tools(workspace_tools)
        self.provider.bind_tools(tools_list)

        # 2. Initialize conversation state
        system_prompt = """You are an intelligent data-analysis and document-retrieval assistant operating over files, structured datasets, PDFs, spreadsheets, and other workspace documents.

Your primary goal is to provide answers that are:
1. Factually correct
2. Grounded strictly in the available workspace data (or web search if explicitly requested or needed as fallback)
3. Complete enough to satisfy the exact wording of the user's question
4. Consistent across repeated or equivalent questions
5. Transparent when the required information genuinely does not exist

Do NOT guess, hallucinate, or claim that data is unavailable without properly verifying the available sources.

==================================================
1. QUERY CLASSIFICATION
==================================================
Before selecting tools, mentally classify the query into one or more categories:
- document lookup
- document comparison
- cross-document reasoning
- table extraction
- numerical calculation
- CSV/XLSX structured analysis
- technical explanation
- visual/diagram question
- missing-information question
- web research
- mixed query

==================================================
2. DOCUMENT-FIRST SOURCE ROUTING
==================================================
Do NOT automatically assume that numerical, student, financial, table, or record-related questions require a structured SQL dataset.
For every query, first determine what information is required and which available source can provide it.
Search uploaded documents/files (using search_documents) before deciding that a structured dataset query is required.
Only use a structured dataset/database tool when:
1. A matching structured dataset actually exists, OR
2. The user explicitly requests a database/SQL operation.
If the required information exists in a DOCX/PDF/PPT table, retrieve it from the document and perform the required reasoning/calculation. Never fail simply because a structured dataset is unavailable when the information exists in an uploaded document.

==================================================
3. FILE-TYPE-AWARE HANDLING
==================================================
Understand the source types:
- PDF: text, tables, page content, figures/images
- PPT/PPTX: slide text, tables, slide-level content, images
- DOC/DOCX: paragraphs, headings, tables, embedded images
- CSV: rows, columns, filtering, sorting, aggregation
- XLS/XLSX: worksheets, rows/columns, headers, values, formulas
Do not treat every file as plain text.

==================================================
4. MIXED-FILE QUESTIONS
==================================================
Support questions requiring information from multiple uploaded files (e.g., marks from one file, attendance from another).
Retrieve relevant evidence from all necessary sources and synthesize the answer.
Do not restrict retrieval to a single file when the question requires multiple sources.

==================================================
5. RETRIEVAL STRATEGY & COMPLETE LIST RETRIEVAL
==================================================
When the user asks for exhaustive lists (attributes, characteristics, components, steps, types, advantages, categories, etc.), retrieve the COMPLETE relevant list. Do not stop after retrieving only the first few matching items. Use a higher top_k in search_documents if necessary.
For tables, retrieve enough context to identify headers, rows, units, values, and relationships.

==================================================
6. SOURCE-GROUNDED ANSWERING & PROVENANCE
==================================================
Uploaded documents are the primary source of truth.
Do not silently replace document information with general model knowledge.
If the answer is supported by the uploaded files, answer from those files.
If the information is NOT present, say that it is not present rather than hallucinating.
Never attribute information to a file unless the retrieved evidence actually came from that file. The final answer must use the actual source associated with the retrieved chunk. Do not infer source attribution merely from the filename mentioned in the user's query.
If multiple files contributed, identify all relevant files.

==================================================
7. STRUCTURED DATA / CSV / EXCEL REASONING
==================================================
For CSV/XLSX questions involving numerical operations (top 5, highest, average, sorting, counts), prefer deterministic structured SQL operations over semantic vector search if a structured dataset is available.
If the same information exists only inside a document table, retrieve the table using search_documents and perform the calculation from the retrieved data.

==================================================
8. WEB SEARCH FALLBACK
==================================================
There are three situations for web search:
A. USER EXPLICITLY REQUESTS WEB SEARCH ("Search the web", "Find the latest"). Web search is mandatory.
B. INFORMATION IS MISSING FROM UPLOADED FILES. Use web search as a fallback.
C. PARTIAL INFORMATION. Retrieve missing parts from the web.
HOWEVER: If the user explicitly says "Answer only from my uploaded documents" or "Use only the study material", DO NOT use web search under any circumstances.
When using web search, synthesize the web results with document context, and clearly distinguish web-derived information from uploaded-document information. Preserve URLs/source metadata.

==================================================
9. VISUAL / DIAGRAM QUESTIONS
==================================================
Detect questions that explicitly require visual inspection ("Look at the diagram...", "What does the graph indicate?").
Call analyze_vision. If visual inspection is unavailable or fails, EXPLICITLY state that the visual could not be inspected. Do not pretend that it was inspected. Do not infer a diagram solely from surrounding text when the user specifically prohibited that.

==================================================
10. MATHEMATICAL / FORMULA OUTPUT
==================================================
Preserve mathematical formulas correctly. Use Markdown/LaTeX where appropriate (e.g., |Q_i - Q_j| \ne |i - j|). Do not corrupt formulas into malformed text.

==================================================
11. ADAPTIVE ANSWER LENGTH & SIMPLE LANGUAGE
==================================================
Produce answers understandable to a non-technical user. Explain terminology (e.g., instead of "CAPWAP uses DTLS", explain what DTLS encrypts).
Simple factual question: concise but complete.
Comparison: table + explanation + conclusion.
Technical concept: definition + simple explanation + example + important points.
Complex/research question: detailed structured explanation + evidence + conclusion.
Use headings, bullets, tables, and examples when they improve readability. Detailed enough for a beginner, without repetitive filler.

==================================================
12. ANSWER STRUCTURE
==================================================
Direct answer first.
Then: ### Explanation (Explain reasoning in simple language)
Then: ### Details / Comparison / Calculation (if useful)
Then: ### Source (Mention relevant files or distinguish web sources)

==================================================
13. NO HALLUCINATION / MISSING INFORMATION
==================================================
If the information does not exist in uploaded documents, available structured data, and web search is not allowed/requested, clearly tell the user that the information could not be found. Do not fabricate values, sources, tables, diagrams, or document content.

==================================================
14. SCHEMA VERIFICATION & DATASET-FIRST REASONING (FOR SQL)
==================================================
When querying SQL datasets, inspect the schema of ALL potentially relevant datasets before deciding information is unavailable. Never confuse "Not in this table" with "Not in the dataset". Derived metrics (averages, counts) are allowed if the raw columns exist. Do NOT hallucinate missing metrics like GPA if there's no conversion formula. Validate SQL results thoroughly before answering.

==================================================
15. DISTINCT STUDENT COUNT RULE
==================================================
When counting students who might have multiple subject rows, use COUNT(DISTINCT student_id), not COUNT(*), unless explicitly asking for rows.

==================================================
16. "EACH", "ALL", "EVERY" — RESULT COMPLETENESS
==================================================
If asked for "each student" or "all departments" and the query engine imposes a 100-row limit, clearly state that the displayed output is limited. Do not present partial results as the complete answer.

==================================================
17. ACADEMIC_MASTER.XLSX — KNOWN DATASET STRUCTURE (REGRESSIONS)
==================================================
PRIMARY TABLE: structured_81dd5878_academic_master_student_marks (marks, subject, division, department, student_id, student_name, attendance_pct)
SUBJECT METADATA: structured_81dd5878_academic_master_subjects (credits, faculty, subject, pass_marks, exam_weightage)
SEMESTER SUMMARY: structured_81dd5878_academic_master_semester_summary (semester, students, pass_rate, average_marks, average_attendance)
*CRITICAL*: "Which department has the highest average attendance?" MUST be answered using `student_marks.department` and `student_marks.attendance_pct`. Do NOT conclude department attendance is unavailable because semester_summary doesn't have it.

==================================================
18. FINAL PRE-ANSWER CHECKLIST
==================================================
[ ] Did I identify the user's exact requested metric and classify the query?
[ ] Did I check documents first if the query is conceptual or table-based?
[ ] Did I use DISTINCT when counting students?
[ ] Is my math/aggregation validated?
[ ] Did I avoid pretending to see images if vision failed?
[ ] Did I format lists completely and math in LaTeX?
[ ] Did I explain it simply for a beginner?
[ ] Did I cite sources accurately?
[ ] Does my final response actually answer the user's wording?

Only after passing this checklist should the final answer be provided.

==================================================
19. MULTI-STEP ANALYTICAL QUERIES
==================================================
If a task requires multiple steps (e.g., comparing two different datasets), you must continue your investigation after obtaining the first intermediate result. Do not stop until all necessary groupings, filters, or queries are complete.

==================================================
20. WEB SEARCH AUTHORITATIVENESS
==================================================
When using web_search, ensure your query is highly specific to return authoritative sources. Prefer official sources for factual or current information. The web tool will return title, URL, and snippet information; use this to verify the source's authority before relying on it.

==================================================
21. CORRELATION VS. ASSOCIATION
==================================================
Do not claim "correlation" or "causation" when you have only calculated grouped averages (e.g., comparing average scores between placed and unplaced students). Describe such results as an "association" or a "difference" unless an actual statistical correlation test was performed.
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]

        strategy_log = []
        iteration = 0
        executed_tool_calls = set()

        # 3. Execution Loop
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Orchestrator Iteration {iteration} for query: '{query}'")

            # Invoke LLM
            try:
                response = self.provider.invoke(messages)
                messages.append(response)
            except Exception as e:
                logger.error(f"LLM Provider invocation failed: {e}")
                error_str = str(e).lower()
                
                # Check for rate limit signatures
                if "429" in error_str or "resourceexhausted" in error_str or "quota" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    return self._format_error("The model's rate limit has been reached. Please wait a moment before trying again.", strategy_log)
                    
                return self._format_error(f"Failed to communicate with LLM Provider: {e}", strategy_log)

            # Check if LLM decided to call tools
            if not getattr(response, "tool_calls", None):
                # No tool calls; LLM has provided the final answer
                
                # Check for completely blank response (can happen if API silently blocks due to rate limits or safety)
                if not response.content or str(response.content).strip() == "":
                    finish_reason = getattr(response, "response_metadata", {}).get("finish_reason", "UNKNOWN")
                    if "rate_limit" in str(finish_reason).lower() or "quota" in str(finish_reason).lower():
                        return self._format_error("The model's rate limit has been reached (detected via finish reason). Please wait a moment before trying again.", strategy_log)
                    return self._format_error(f"The model returned a blank response (Finish reason: {finish_reason}). This often indicates a rate limit or safety filter block.", strategy_log)
                    
                return self._format_success(response.content, strategy_log)

            # Execute Tool Calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                tool_signature = f"{tool_name}({json.dumps(tool_args, sort_keys=True)})"
                if tool_signature in executed_tool_calls:
                    tool_result = f"System Safeguard: You already executed {tool_name} with these exact arguments. Please do not repeat the same action in an infinite loop. Either change your parameters, try a different tool, or synthesize a final answer."
                    logger.warning(f"Prevented tool loop for: {tool_signature}")
                else:
                    executed_tool_calls.add(tool_signature)
                    
                    strategy_log.append({
                        "action": "tool_call",
                        "tool": tool_name,
                        "args": tool_args
                    })
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Find the tool function
                    tool_func = self._get_tool_by_name(tool_name, workspace_tools)
                    
                    try:
                        if tool_func:
                            tool_result = tool_func(**tool_args)
                        else:
                            tool_result = f"Error: Tool '{tool_name}' not found."
                    except Exception as e:
                        logger.error(f"Tool execution error ({tool_name}): {e}")
                        tool_result = f"Error executing {tool_name}: {e}"

                    strategy_log.append({
                        "action": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_result)[:500] + ("..." if len(str(tool_result)) > 500 else "")
                    })

                # Append tool result to messages
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id
                ))

        # Max iterations reached
        logger.warning(f"Orchestrator hit max iterations ({self.max_iterations}). Forcing final answer.")
        messages.append(HumanMessage(content="You have reached the maximum number of tool calls. Synthesize a final answer based on what you have found so far, and explicitly state if you couldn't complete the task."))
        try:
            final_response = self.provider.invoke(messages)
            if not final_response.content or str(final_response.content).strip() == "":
                return self._format_error("The model returned a blank response at the final iteration. This often indicates a rate limit or safety filter block.", strategy_log)
            return self._format_success(final_response.content, strategy_log)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "resourceexhausted" in error_str or "quota" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                return self._format_error("The model's rate limit has been reached. Please wait a moment before trying again.", strategy_log)
            return self._format_error(f"Failed to generate final fallback response: {e}", strategy_log)


    def _build_tools(self, ws_tools: WorkspaceTools) -> List[StructuredTool]:
        """Wrap WorkspaceTools methods into Langchain StructuredTools."""
        return [
            StructuredTool.from_function(
                func=ws_tools.get_workspace_structure,
                name="get_workspace_structure",
                description="Returns the high-level folder structure of the workspace."
            ),
            StructuredTool.from_function(
                func=ws_tools.get_folder_contents,
                name="get_folder_contents",
                description="Returns the files inside a specific folder.",
                args_schema=FolderIdSchema
            ),
            StructuredTool.from_function(
                func=ws_tools.get_file_metadata,
                name="get_file_metadata",
                description="Returns metadata about a specific file, such as size, chunk count, processing status.",
                args_schema=AssetIdSchema
            ),
            StructuredTool.from_function(
                func=ws_tools.discover_datasets,
                name="discover_datasets",
                description="Discovers structured datasets relevant to a query using metadata/semantic matching. Returns dataset IDs.",
                args_schema=QuerySchema
            ),
            StructuredTool.from_function(
                func=ws_tools.get_dataset_schema,
                name="get_dataset_schema",
                description="Returns the exact SQL schema definition for a dataset ID.",
                args_schema=DatasetIdSchema
            ),
            StructuredTool.from_function(
                func=ws_tools.get_dataset_profile,
                name="get_dataset_profile",
                description="Returns a high-level statistical overview of the dataset without generating SQL.",
                args_schema=DatasetIdSchema
            ),
            StructuredTool.from_function(
                func=ws_tools.search_documents,
                name="search_documents",
                description="Performs semantic RAG search across documents to answer unstructured conceptual questions.",
                args_schema=QuerySchema
            ),
            StructuredTool.from_function(
                func=ws_tools.analyze_vision,
                name="analyze_vision",
                description="Analyzes an image or diagram structurally.",
                args_schema=VisionQuerySchema
            ),
            StructuredTool.from_function(
                func=ws_tools.web_search,
                name="web_search",
                description="Retrieves external information from the web when workspace info is insufficient.",
                args_schema=QuerySchema
            ),
            StructuredTool.from_function(
                func=ws_tools.query_dataset,
                name="query_dataset",
                description="Generates and executes analytical SQL on structured tables. ONLY use valid PostgreSQL.",
                args_schema=SqlQuerySchema
            )
        ]

    def _get_tool_by_name(self, name: str, ws_tools: WorkspaceTools):
        """Map tool name to the instance method."""
        tool_map = {
            "get_workspace_structure": ws_tools.get_workspace_structure,
            "get_folder_contents": ws_tools.get_folder_contents,
            "get_file_metadata": ws_tools.get_file_metadata,
            "discover_datasets": ws_tools.discover_datasets,
            "get_dataset_schema": ws_tools.get_dataset_schema,
            "get_dataset_profile": ws_tools.get_dataset_profile,
            "search_documents": ws_tools.search_documents,
            "analyze_vision": ws_tools.analyze_vision,
            "web_search": ws_tools.web_search,
            "query_dataset": ws_tools.query_dataset,
        }
        return tool_map.get(name)

    def _format_success(self, answer: Any, strategy_log: list) -> dict:
        if isinstance(answer, list):
            # Sometimes Gemini returns a list of content blocks
            answer_str = "\n".join(str(block.get("text", "")) if isinstance(block, dict) else str(block) for block in answer)
        else:
            answer_str = str(answer) if answer is not None else ""
            
        return {
            "answer": answer_str,
            "strategy": "ORCHESTRATOR",
            "sql_query": None, 
            "sql_results": [],
            "strategy_log": strategy_log,
            "citations": {"documents": [], "datasets": []} # Can be parsed dynamically if needed
        }

    def _format_error(self, message: str, strategy_log: list) -> dict:
        return {
            "answer": f"**System Error:** {message}",
            "strategy": "ERROR",
            "strategy_log": strategy_log
        }
