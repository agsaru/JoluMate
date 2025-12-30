from langgraph.graph.message import add_messages
import os 
from dotenv import load_dotenv
load_dotenv()
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_groq import ChatGroq
from langgraph.graph import START,StateGraph,END
from typing import Annotated,TypedDict
from configs.db import pool
class ChatState(TypedDict):
    messages:Annotated[list,add_messages]


llm = ChatGroq(model='openai/gpt-oss-120b', api_key=os.getenv("GROQ_API_KEY"))

async def agent_node(state:ChatState):
    response=await llm.ainvoke(state['messages'])
    return {'messages':response}

graph=StateGraph(ChatState)
graph.add_node('agent',agent_node)

graph.add_edge(START,'agent')
graph.add_edge('agent',END)
checkpointer=AsyncPostgresSaver(pool)

workflow=graph.compile(checkpointer=checkpointer)