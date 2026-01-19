
import streamlit as st
from langchain.schema import ChatMessage
from langchain_core.messages import HumanMessage

from src.agent import general_agent

# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver

agent_executor = general_agent.create_agent_executor()

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(
        role="assistant", content="How can I help you?")]

for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

# Handle user input from the chat interface
if prompt := st.chat_input():
    # Append the user's message to session state and display it
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        # Append the user's message to session state and display it
        config = {"configurable": {"thread_id": "abc123"}} # TODO: remove hardcode
        response = agent_executor.invoke(input = {"messages": [HumanMessage(content=prompt)]}, config = config)

        # Extract and display the assistant's response, also append it to session state
        assistant_response = response['messages'][-1].content
        st.write(response['messages'][-1].content)
        st.session_state.messages.append(ChatMessage(role="assistant", content=assistant_response))

# Add a refresh button to reset the conversation
if st.button("Refresh Thread"):
    st.session_state.clear()
    st.rerun()  # This will rerun the script to reset everything #experimental_rerun on older version of streamlit
