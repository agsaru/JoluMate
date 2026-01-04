
import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import ToolNode, tools_condition 

from configs.db import pool
from rag.tools import search_knowledge_base

load_dotenv()

tools = [search_knowledge_base]

llm = ChatGroq(
    model='llama-3.3-70b-versatile', 
    api_key=os.getenv("GROQ_API_KEY")
).bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

async def agent_node(state: ChatState):
    sys_msg = SystemMessage(content="""You are JoluMate. 
    You have access to a 'search_knowledge_base' tool. 
    ALWAYS use this tool if the user asks about their documents, PDFs, or specific context.
    Otherwise, just chat normally.""")
    
    messages = [sys_msg] + state['messages']
    response = await llm.ainvoke(messages)
    return {'messages': response}

graph = StateGraph(ChatState)

graph.add_node('agent', agent_node)
graph.add_node('tools', ToolNode(tools))

graph.add_edge(START, 'agent')

graph.add_conditional_edges('agent',tools_condition,)

graph.add_edge('tools', 'agent')

checkpointer = AsyncPostgresSaver(pool)
workflow = graph.compile(checkpointer=checkpointer)