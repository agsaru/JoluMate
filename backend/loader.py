from langchain_community.document_loaders import PyMuPDFLoader,UnstructuredWordDocumentLoader,TextLoader,UnstructuredPowerPointLoader,UnstructuredImageLoader,UnstructuredFileLoader,UnstructuredPDFLoader
import fitz
from pdf2image import convert_from_path
import pytesseract
from langchain_classic.schema import Document
def is_scanned(filepath):
    doc=fitz.open(filepath)
    for page in doc:
      text=page.get_text().strip()
      if text:
          return False
    return True
def scanned_pdf_loader(filepath):
    images=convert_from_path(filepath)
    docs=[]
    for i,img in enumerate(images):
        text=pytesseract.image_to_string(img,lang="eng")
        doc=Document(
            page_content=text,
            metadata={
                "source": filepath,
                "page": i,
                "ocr": True
            }
        )
        docs.append(doc)
    return docs

def load_file(filepath):
    filetype = filepath.rsplit(".", 1)[1].lower()
    print(filetype)
    if filetype=="pdf":
        if is_scanned(filepath):
            return scanned_pdf_loader(filepath)
        else:
            return PyMuPDFLoader(filepath).load()
    elif filetype in ["doc","docx"]:  
        return UnstructuredWordDocumentLoader(filepath).load()
    elif filetype in ["ppt", "pptx"]:
        return UnstructuredPowerPointLoader(filepath).load()
    elif filetype=="txt":
        return TextLoader(filepath).load()
    elif filetype in ["png","jpg","jpeg"]:
        return UnstructuredImageLoader(filepath).load()
    else:
        return UnstructuredFileLoader(filepath).load()

