# Architecture Decision Records (ADR)

## ADR-001: Pure Docling Extraction Pipeline
**Status**: Accepted
**Context**: We evaluated PyMuPDF+PaddleOCR vs Docling.
**Decision**: Use Docling for structured extraction, as it handles Markdown formatting, table structures, and reading order much better.

## ADR-002: PostgreSQL as Source of Truth
**Status**: Accepted
**Context**: Need to store metadata and relationships along with vector embeddings.
**Decision**: PostgreSQL stores all metadata, documents, chunks, and state. Milvus is treated purely as a derived index for fast vector search. If Milvus fails, it can be rebuilt from PostgreSQL.

## ADR-003: Asset Versioning Approach
**Status**: Accepted
**Context**: Need to support document versions (e.g., HR Policy v1, v2).
**Decision**: Use a shared `version_group_id` for related assets, with an `is_latest` boolean flag. This avoids a complex recursive or completely separate tables.
