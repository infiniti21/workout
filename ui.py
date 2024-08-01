import asyncio
# import httpx
import streamlit as st
# import random
import json
from websockets import connect


async def send_message(message):
    print("-"*40)
    print("Entered send_message. Connecting to WS..")
    url = "ws://127.0.0.1:8000/ws"
    async with connect(url) as websocket:
        print("CONNECTED to WS. Sending data:", message)
        await websocket.send(message)
        print("SENT data:", message)
        response = await websocket.recv()
        response = response.replace("'", '"')
        print("RECEIVED data:", response)
        response_d = json.loads(response)
        print("RETURNING data to MAIN:", response_d)
        print("-"*40)
        return response_d
    
async def main():
    st.title("Chatbot Interface")
    user_input = st.text_input("User:", key="user_input")
    if st.button("Send"):
        if user_input:
            print("*"*80)
            print("MAIN sending and waiting for data:", user_input)
            reply = await send_message(user_input)
            print("MAIN received response:", reply)
            ai_response = reply.get("ai_response")
            tool_calls = reply.get("tool_calls", [])
            if isinstance(reply, dict):
                st.text_are("Bot:", value=ai_response, height=200, disabled=True)
                st.text_are("Tool calls:", value=tool_calls, height=200, disabled=True)
            print("*"*80)

if __name__=='__main__':
    asyncio.run(main())