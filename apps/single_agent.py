from langchain.schema import ChatMessage
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
from langchain_core.messages import HumanMessage

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest", api_key=st.session_state['GOOGLE_API_KEY'])

# configure agent
system_prompt = 'You are a virtual real estate agent.'
agent_executor = create_react_agent(llm, tools=[], state_modifier=system_prompt)

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(
        role="assistant", content="How can I help you?")]

for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

if prompt := st.chat_input():
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):

        response = agent_executor.invoke(input = {"messages": [HumanMessage(content=prompt)]})
        st.write(response['messages'][1].content)
        st.session_state.messages.append(ChatMessage(role="assistant", content=response['messages'][1].content))