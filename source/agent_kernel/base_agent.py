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
# OLLAMA_URL = "http://localhost:11434/v1"
OLLAMA_URL = "http://localhost:1234/v1" # временно используется LM Studio для отладки

DEFAULT_THREAD_ID = "session-1"
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

async def send_prompt(agent, input_str: str, role:str="user", thread_id:str=DEFAULT_THREAD_ID):
    return await agent.ainvoke(
        {"role": role, "messages": [HumanMessage(content=input_str)]},
        config={"configurable": {"thread_id": thread_id}}
    )

def memory_clear(agent, thread_id:str=DEFAULT_THREAD_ID):
    agent.update_state({"configurable": {"thread_id": thread_id}}, {"messages": []})
