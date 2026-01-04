from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from rag.utils import search_documents

@tool
async def search_knowledge_base(query: str, config: RunnableConfig) -> str:
    """
    Search the user's uploaded PDF documents for knowledge.
    Use this tool when the user asks questions about specific content, 
    documents, or "context" they have uploaded.
    """
    
    user_id = config.get("configurable", {}).get("user_id")
    
    if not user_id:
        return "Error: No user identified for this search."

    results = await search_documents(query, user_id)
    
    if not results:
        return "No relevant information found in your documents."
        
    return results