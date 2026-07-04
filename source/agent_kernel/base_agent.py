import subprocess
import requests
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_URL = "http://localhost:11434/v1"

CONFIG = {"configurable": {"thread_id": "session-1"}}
AGENT_EXEC = None

def kernel_init(model_name:str, tools:list, sysprompt:str, temp:float=0.7):
    global OLLAMA_URL

    llm = ChatOpenAI(
        model=model_name,
        base_url=OLLAMA_URL,
        api_key="not-needed",
        # temperature=0.1,
        temperature=temp,
    )

    return create_agent(
        llm,
        tools,
        system_prompt=sysprompt,
        checkpointer=MemorySaver(),
    )

async def send_prompt(agent, input_str: str, role:str="user"):
    return await agent.ainvoke(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config=CONFIG
    )

def memory_clear(agent):
    global CONFIG
    agent.update_state(CONFIG, {"messages": []}) 
    