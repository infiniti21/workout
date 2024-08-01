from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
import json
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# Path to the configuration file
config_path = 'config.json'
# Load the configuration file
with open(config_path, 'r') as config_file:
    config = json.load(config_file)
openai_config = config['openai_config']
os.environ['OPENAI_API_KEY'] = openai_config['openai_api_key']
google_config = config['google_config']
os.environ['GOOGLE_API_KEY'] = google_config['google_api_key']

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide first number by second number"""
    return a / b

@tool
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

@tool
def subtract(a: float, b: float) -> float:
    """Subtract from first number the second number"""
    return a - b

tool_dict = {"add": add, "multiply": multiply, "divide": divide, "subtract": subtract}
tools = [add, multiply, divide, subtract]
llmg = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
llmo = ChatOpenAI(model="gpt-3.5-turbo")
llm_in_use = llmg
llm_with_tools = llm_in_use.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Answer all questions to the best of your ability. Use the provided tools only to perform any mathematical calculations."),
        MessagesPlaceholder(variable_name="messages")
    ]
)

chain = prompt | llm_with_tools

chat_history = ChatMessageHistory()

async def send_and_get_message(user_message):
    print('-'*40)
    user_input = user_message
    chat_history.add_user_message(user_input)
    if user_input.casefold()=='exit':
        raise HTTPException(status_code=400, detail="Exit command received")
    messages = [HumanMessage(user_input)]
    print("INCOKING chain with tools..")
    response_json = chain.invoke(chat_history.messages)
    ai_response = response_json.content
    tool_calls = response_json.tool_calls
    print("MAIN CHAIN response: ", ai_response, '\nMAIN CHAIN tool_calls: ', tool_calls)
    if ai_response:
        chat_history.add_ai_message(ai_response)
    if tool_calls:
        print("ENTERING tool call..")
        for tool_call in tool_calls:
            selected_tool = tool_dict[tool_call["name"].lower()]
            print("INVOKING tool call..")
            tool_msg = selected_tool.invoke(tool_call)
            print("TOOL msg:", tool_msg)
            messages.append(tool_msg)
        print("INVOKING chain with tool call result messages:\n", messages)
        ai_response = llm_with_tools.invoke(messages).content
        chat_history.add_ai_message(ai_response)
    print("FINAL AI RESPONSE:", ai_response, "\nFINAL TOOL CALLS:", tool_calls)
    response_s = json.dumps({"ai_response": ai_response,
                             "tool_calls": tool_calls})
    return response_s

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        print("*"*80)
        data = await websocket.receive_text()
        print("WS RECEIVED data:", data)
        response = await send_and_get_message(data)
        print('WS SENDING data:', data)
        await websocket.send_text(response)
        print("*"*80)