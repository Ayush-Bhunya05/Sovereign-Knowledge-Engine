"""Extraction service — single responsibility: raw document to Markdown + metadata."""

import logging
import time

from app.schemas.ingestion.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class ExtractionService:
    """Extract text content from uploaded documents using Docling, augmented with Gemini Vision."""

    def __init__(self, api_key: str | None = None, vision_model: str | None = None):
        self.api_key = api_key
        self.vision_model = vision_model
        
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            if self.api_key and self.vision_model:
                # Use a specific retry logic or let Langchain handle basic retries.
                self.vision_llm = ChatGoogleGenerativeAI(
                    model=self.vision_model, 
                    temperature=0, 
                    api_key=self.api_key,
                    max_retries=2
                )
            else:
                self.vision_llm = None
                logger.warning("No GEMINI_API_KEY or vision_model provided. Augmented Vision Pipeline will be disabled.")
        except ImportError:
            self.vision_llm = None
            logger.warning("langchain_google_genai not found. Vision Pipeline disabled.")

        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

            # Configure PDF pipeline to perform OCR on images and extract image bytes
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = RapidOcrOptions()
            pipeline_options.generate_picture_images = True
            
            self.converter = DocumentConverter(
                format_options={
                    "pdf": PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            logger.info("ExtractionService initialized with Docling engine (OCR Enabled)")
        except ImportError:
            logger.warning("Docling not available in this environment. Extraction will fail unless mocked.")
            self.converter = None

    def _analyze_image_with_vision(self, pil_image) -> str | None:
        """Invokes Gemini Vision to extract structural data from an image."""
        if not self.vision_llm:
            return None
        
        # MVP filter for decorative images: Skip if image is too small
        if pil_image.width < 150 or pil_image.height < 150:
            logger.info(f"Skipping vision analysis for small image ({pil_image.width}x{pil_image.height})")
            return None

        try:
            import base64
            from io import BytesIO
            from langchain_core.messages import HumanMessage
            
            buffered = BytesIO()
            pil_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            message = HumanMessage(
                content=[
                    {
                        "type": "text", 
                        "text": "You are an expert data analyst. Treat this as a multimodal diagram understanding task, not merely OCR. Extract all text, labels, components, relationships, arrows/flow direction, hierarchy, and spatial/structural context into a highly detailed Markdown description. If it is just a decorative image with no structural meaning, reply with 'DECORATIVE'."
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                ]
            )
            
            logger.info(f"Invoking {self.vision_model} for image ({pil_image.width}x{pil_image.height})...")
            response = self.vision_llm.invoke([message])
            
            content = response.content
            if isinstance(content, list):
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
            
            result = content.strip()
            
            if result.upper() == "DECORATIVE":
                return None
                
            return result
        except Exception as e:
            logger.error("Vision API call failed (quota/rate-limit or network error): %s", e)
            return f"*[Vision OCR extraction failed: {e}]*"

    def extract(self, file_path: str, document_type: str) -> ExtractionResult:
        """Extract text from *file_path* based on *document_type*.

        Returns:
            ExtractionResult containing markdown, page count, and metadata.
        """
        if document_type == "txt":
            return self._extract_txt(file_path)

        if not self.converter:
            raise RuntimeError("Docling converter is not initialized.")

        start_time = time.time()
        try:
            result = self.converter.convert(file_path)
            doc = result.document
            
            markdown = doc.export_to_markdown()
            
            pic_texts = []
            if hasattr(doc, 'pictures'):
                for pic in doc.pictures:
                    base_text = getattr(pic, 'text', None)
                    vision_text = None
                    
                    # Try to get the PIL Image and analyze it with Gemini Vision
                    if hasattr(pic, 'get_image'):
                        try:
                            pil_img = pic.get_image(doc)
                            if pil_img:
                                vision_text = self._analyze_image_with_vision(pil_img)
                        except Exception as img_e:
                            logger.warning(f"Could not extract PIL image from docling picture: {img_e}")
                    
                    # Combine the texts
                    final_text = ""
                    if vision_text:
                        final_text += f"\n> **[Gemini Vision: Structural Diagram Extraction]**\n> {vision_text.replace(chr(10), chr(10)+'> ')}\n"
                    elif base_text and base_text.strip():
                        final_text += f"\n> **[RapidOCR Extracted Text]**\n> {base_text.strip()}\n"
                    
                    pic_texts.append(final_text)
            
            # Replace <!-- image --> placeholders sequentially, preserving the tag
            for p_text in pic_texts:
                if p_text:
                    markdown = markdown.replace("<!-- image -->", f"<!-- image -->\n{p_text}", 1)
                else:
                    # Keep the placeholder so traceability isn't lost
                    pass

            # Attempt to gather language and page count
            language = None
            page_count = 1
            if hasattr(doc, "pages") and doc.pages:
                page_count = len(doc.pages)
            
            # Count elements for metadata
            table_count = sum(1 for item, _ in doc.iterate_items() if "table" in type(item).__name__.lower())
            image_count = sum(1 for item, _ in doc.iterate_items() if "picture" in type(item).__name__.lower() or "image" in type(item).__name__.lower())

            if document_type in ("docx", "image"):
                page_count = None

            elapsed_ms = int((time.time() - start_time) * 1000)

            parser_metadata = {
                "parser_name": "docling",
                "parser_version": "v2.0-ocr-enabled",
                "ocr_engine": "gemini-vision+rapidocr",
            }

            extraction_metadata = {
                "extracted_image_count": image_count,
                "table_count": table_count,
                "processing_time_ms": elapsed_ms,
            }

            logger.info("Extraction completed in %dms (%s, %d tables, %d images).", elapsed_ms, document_type, table_count, image_count)

            return ExtractionResult(
                markdown=markdown,
                page_count=page_count,
                language=language,
                parser_metadata=parser_metadata,
                extraction_metadata=extraction_metadata,
            )

        except Exception as e:
            logger.exception("Extraction failed for %s", file_path)
            raise RuntimeError(f"Extraction failed: {e}") from e

    def _extract_txt(self, file_path: str) -> ExtractionResult:
        start_time = time.time()
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            markdown = fh.read().strip()
            
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        parser_metadata = {
            "parser_name": "txt_native",
            "parser_version": "1.0",
            "ocr_engine": None,
        }
        
        extraction_metadata = {
            "extracted_image_count": 0,
            "table_count": 0,
            "processing_time_ms": elapsed_ms,
        }
        
        return ExtractionResult(
            markdown=markdown,
            page_count=None,
            language=None,
            parser_metadata=parser_metadata,
            extraction_metadata=extraction_metadata,
        )
