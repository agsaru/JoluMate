from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda,RunnableParallel,RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
load_dotenv()
def create_rag(vectorstore):
   retriever=vectorstore.as_retriever(search_type="similarity",search_kwargs={"k":4})
   llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        api_key=os.getenv("GOOGLE_API_KEY")
    )
   prompt=PromptTemplate(
      template="""You are an intelligentt RAG assitant.
      You must answer only from the provided documents.
      If the answer related the question is not available or insufficient 
       ,just say you don't know the answer.
       RULES:
       1. Do not hallucinate
       2. Do not randomly guess
        {documents}
         Question:{question}
           """,
           input_variables=["documents","question"]
   )
   
   def format_docs(retrieved_docs):
      doc_text=[]
      for i ,doc in enumerate(retrieved_docs):
         text=f"[Document {i+1}]\n {doc.page_content.strip()}"
         doc_text.append(text)
      return "\n\n".join(doc_text)

   parralel_chain=RunnableParallel({
      "documents":retriever|RunnableLambda(format_docs),
      "question":RunnablePassthrough()
   })

   parser=StrOutputParser()

   main_chain=parralel_chain | prompt| llm| parser
   return main_chain

def ask_question(rag,question):
   return rag.invoke(question)