"""Chunking service — table-aware markdown chunker."""

import hashlib
import logging
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.schemas.ingestion.schemas import EnrichedChunkData

logger = logging.getLogger(__name__)

class ChunkingService:
    """Generate text chunks from Markdown, preserving tables as atomic blocks."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def _hash_content(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def chunk_markdown(
        self,
        markdown: str,
        workspace_id: uuid.UUID,
        asset_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        page_count: int | None = None
    ) -> list[EnrichedChunkData]:
        """Split markdown into chunks, treating tables atomically."""
        
        chunks = []
        global_index = 0

        # Simple table block extraction
        lines = markdown.split("\n")
        blocks = []
        current_block = []
        in_table = False

        for line in lines:
            is_table_line = line.strip().startswith("|") and line.strip().endswith("|")
            
            if is_table_line and not in_table:
                # Flush text block
                if current_block:
                    blocks.append(("text", "\n".join(current_block)))
                    current_block = []
                in_table = True
                current_block.append(line)
            elif is_table_line and in_table:
                current_block.append(line)
            elif not is_table_line and in_table:
                # Flush table block
                blocks.append(("table", "\n".join(current_block)))
                current_block = [line]
                in_table = False
            else:
                current_block.append(line)

        if current_block:
            blocks.append(("table" if in_table else "text", "\n".join(current_block)))

        # Process blocks
        # Naive heading tracking
        current_heading = None
        
        for block_type, content in blocks:
            if not content.strip():
                continue
                
            # Update heading context based on the last heading seen in the block
            # (A robust implementation would use MarkdownHeaderTextSplitter, but this is a simplified atomic table approach)
            for line in content.split("\n"):
                if line.startswith("#"):
                    current_heading = line.strip().lstrip("#").strip()

            if block_type == "table":
                # Tables are atomic, yield as a single chunk regardless of size
                text = content.strip()
                chunks.append(
                    EnrichedChunkData(
                        chunk_index=global_index,
                        page_number=None, # Markdown loses page boundaries unless docling annotated them
                        chunk_text=text,
                        character_count=len(text),
                        content_hash=self._hash_content(text),
                        heading_context=current_heading,
                        section_context=None,
                        workspace_id=workspace_id,
                        folder_id=folder_id,
                        asset_id=asset_id,
                    )
                )
                global_index += 1
            else:
                # Text blocks get split
                text_chunks = self._splitter.split_text(content)
                for text_chunk in text_chunks:
                    text_chunk = text_chunk.strip()
                    if not text_chunk:
                        continue
                    chunks.append(
                        EnrichedChunkData(
                            chunk_index=global_index,
                            page_number=None,
                            chunk_text=text_chunk,
                            character_count=len(text_chunk),
                            content_hash=self._hash_content(text_chunk),
                            heading_context=current_heading,
                            section_context=None,
                            workspace_id=workspace_id,
                            folder_id=folder_id,
                            asset_id=asset_id,
                        )
                    )
                    global_index += 1

        logger.info("Generated %d atomic chunks from Markdown", len(chunks))
        return chunks
