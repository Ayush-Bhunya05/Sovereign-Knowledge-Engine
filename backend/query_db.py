from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

def get_binning_info():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.filename == "14.binning.pdf").first()
        if not doc:
            print("14.binning.pdf not found in DB.")
            return

        print(f"Document Found: {doc.filename}")
        print(f"Document ID: {doc.id}")
        print(f"Total Chunks Generated: {doc.chunk_count}")
        print(f"Extracted Text Length: {len(doc.extracted_text) if doc.extracted_text else 0} characters")

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        for idx, c in enumerate(chunks):
            print(f"\n--- Chunk {idx} (ID: {c.id}) ---")
            print(f"Character Count: {c.character_count}")
            print(f"Tokens (approx): {c.character_count // 4}")
            print(f"Chunk Text:\n{c.chunk_text}")
    finally:
        db.close()

if __name__ == "__main__":
    get_binning_info()
