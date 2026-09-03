# Sovereign Knowledge Engine (Agentic RAG Platform)

![Project Banner](https://img.shields.io/badge/AI-Sovereign_Knowledge_Engine-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Milvus](https://img.shields.io/badge/Milvus-Vector_DB-0d6efd?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Gemini_API-Google-ff6f00?style=for-the-badge)

Sovereign Knowledge Engine is an autonomous, full-stack Artificial Intelligence assistant capable of multi-document reasoning, hybrid search, and automated SQL-based data analysis. It provides an enterprise-grade agentic orchestration engine that dynamically routes complex user queries across semantic knowledge bases, structured datasets, and live web research.

## 🚀 Key Features

* **Agentic Orchestration Engine:** An autonomous LLM loop (powered by Google Gemini) that breaks down complex queries, performs multi-step reasoning, and calls the appropriate tools.
* **High-Fidelity Document Ingestion:** Integrated with **Docling** for advanced parsing of PDFs, PPTs, and DOCX files.
* **Gemini-Powered OCR:** Extracts and analyzes complex visual diagrams and images embedded inside documents.
* **Structured Data Analysis (Text-to-SQL):** Automatically discovers uploaded CSV and Excel datasets, fetches schemas, generates validated PostgreSQL queries, and executes them to answer numerical/analytical questions.
* **Hybrid Semantic Search:** Uses **Milvus** vector database to semantically match queries against chunked document knowledge bases.
* **Live Web Research:** Automatically falls back to fetching authoritative, real-time context from the web (via DuckDuckGo) when internal workspace data is insufficient.
* **Strict Execution Safeguards:** Implements read-only execution roles for SQL, loop-prevention, rate-limit handling, and robust context retrieval to guarantee hallucination-free interactions.

## 🛠️ Technology Stack

### Backend
* **Framework:** Python, FastAPI, Uvicorn
* **Database (Relational):** PostgreSQL, SQLAlchemy ORM, Alembic (Migrations)
* **Database (Vector):** Milvus
* **LLM / AI:** Google Gemini API (1.5 Pro/Flash), Langchain Core
* **Document Processing:** Docling, Pandas (CSV/XLSX)

### Frontend
* **Framework:** React.js, Vite
* **Styling:** Vanilla CSS (Glassmorphism, Modern Dark Mode)
* **Icons:** Lucide React
* **Markdown:** `react-markdown`, `remark-gfm`

## 🏗️ Architecture Overview

The platform uses a **Workspace-based Architecture**. Users can create isolated workspaces and upload various documents (PDF, DOCX, PPTX, CSV, XLSX).

When a query is submitted:
1. **Classification:** The Agentic Orchestrator determines if the query requires document lookup, structural data analysis, or web research.
2. **Tool Execution:** 
   - `search_documents`: Queries Milvus for semantic similarity.
   - `discover_datasets` -> `get_dataset_schema` -> `query_dataset`: Discovers matching CSV/Excel tables and executes generated SQL.
   - `web_search`: Pulls in current authoritative knowledge from the internet.
3. **Synthesis:** The LLM aggregates all tool outputs and synthesizes a final, properly cited answer.

## ⚙️ Local Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js & npm
- PostgreSQL running locally or via Docker
- Milvus (Standalone) running via Docker

### 1. Clone the Repository
```bash
git clone https://github.com/CommitAndCry/Sovereign-Knowledge-Engine.git
cd Sovereign-Knowledge-Engine
```

### 2. Backend Setup
Navigate to the `backend` folder and create a virtual environment:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

Set up your environment variables by creating a `.env` file in the `backend` directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db
MILVUS_URI=http://localhost:19530
GEMINI_API_KEY=your_gemini_api_key_here
```

Run Alembic migrations to set up the PostgreSQL schema:
```bash
alembic upgrade head
```

Start the FastAPI backend server:
```bash
uvicorn app.main:app --reload
```

### 3. Frontend Setup
Open a new terminal and navigate to the `frontend` folder:
```bash
cd frontend
npm install
```

Start the Vite development server:
```bash
npm run dev
```
The application will be accessible at `http://localhost:5173`.

## 🤝 Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your enhancements. Ensure you follow standard coding practices and add comments where applicable.

## 📄 License
This project is licensed under the MIT License.
