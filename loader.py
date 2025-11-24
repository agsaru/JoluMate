from langchain_community.document_loaders import PyMuPDFLoader,UnstructuredWordDocumentLoader,TextLoader,UnstructuredPowerPointLoader,UnstructuredImageLoader,UnstructuredFileLoader,UnstructuredPDFLoader

def is_scanned():
    return False
def scanned_pdf_loader():
    pass


def load_file(filename):
    filetype=filename.rsplit(".",1)[1]
    print(filetype)
    if filetype=="pdf":
        if is_scanned():
            return scanned_pdf_loader()
        else:
            return PyMuPDFLoader(filename).load()
    elif filetype in ["doc","docx"]:  
        return UnstructuredWordDocumentLoader(filename).load()
    elif filetype in ["ppt", "pptx"]:
        return UnstructuredPowerPointLoader(filename).load()
    elif filetype=="txt":
        return TextLoader(filename).load()
    elif filetype in ["png","jpg","jpeg"]:
        return UnstructuredImageLoader(filename).load()
    else:
        return UnstructuredFileLoader(filename).load()

