import sys
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.database import SessionLocal
from app.models.document import Document, ProcessingStatus

def test_pipeline():
    doc_id = uuid.uuid4()
    db = SessionLocal()
    try:
        doc = Document(
            id=doc_id,
            filename="test.txt",
            document_type="txt",
            mime_type="text/plain",
            file_size=10,
            processing_status=ProcessingStatus.PENDING.value,
            storage_path="test.txt",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        print(f"Created doc: {doc_id}")
    finally:
        db.close()

    from app.dependencies import get_document_service
    doc_service = get_document_service()
    
    print("Starting pipeline...")
    # I'll manually run the pipeline code here to see where it blocks
    db2 = SessionLocal()
    print("Session created.")
    doc = db2.query(Document).filter(Document.id == doc_id).first()
    print("Queried doc:", doc)
    
    doc.processing_status = ProcessingStatus.DETECTING_FILE_TYPE.value
    print("Modified status, committing...")
    db2.commit()
    print("Committed 1.")
    
    doc.processing_status = ProcessingStatus.EXTRACTING_MACHINE_TEXT.value
    print("Modified status 2, committing...")
    db2.commit()
    print("Committed 2.")
    db2.close()


if __name__ == "__main__":
    with open("test.txt", "w") as f:
        f.write("hello world")
    test_pipeline()
