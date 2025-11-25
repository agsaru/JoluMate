from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough
import os
from dotenv import load_dotenv
load_dotenv()
def create_rag(vectorstore):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))

    def format_docs(docs):
        return "\n\n".join([doc.page_content for doc in docs])

    template = """
    You are an assistant for question-answering tasks. Use the following pieces of retrieved documents to answer the question. If you don't know the answer, just say that you don't know. 
    Documents:
    Rules:
    1. Do not hallucinate 
    2. Do not make answers on your own
    {documents}

    Question: {question}
    """

    prompt = PromptTemplate(
        template=template,
        input_variables=["documents", "question"]
    )

    pipeline = RunnableParallel(
        {"documents": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
    ) | prompt | llm | StrOutputParser()

    return pipeline


def ask_question(rag, question):
    return rag.invoke(question)
