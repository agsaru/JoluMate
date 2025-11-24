from langchain_text_splitters import RecursiveCharacterTextSplitter

def text_splitter(docs):
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )
    return splitter.split_documents(docs)