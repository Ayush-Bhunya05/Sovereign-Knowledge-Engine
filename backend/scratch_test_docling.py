from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.ocr_options = RapidOcrOptions()
pipeline_options.generate_picture_images = True

converter = DocumentConverter(
    format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
)

import requests
pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
with open("test.pdf", "wb") as f:
    f.write(requests.get(pdf_url).content)

res = converter.convert("test.pdf")
doc = res.document

for pic in doc.pictures:
    print("Found picture!")
    print(pic.model_dump())
