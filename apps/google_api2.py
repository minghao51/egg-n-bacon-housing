from langchain_core.prompts import ChatPromptTemplate
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import ChatMessage
# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)


# with st.sidebar:
#     openai_api_key = st.text_input("OpenAI API Key", type="password")

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(
        role="assistant", content="How can I help you?")]

for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

if prompt := st.chat_input():
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        stream_handler = StreamHandler(st.empty())
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", api_key=st.session_state['GOOGLE_API_KEY'])
        # response = llm.invoke(st.session_state.messages)
        # prompt = ChatPromptTemplate.from_messages([(
        #     "system",
        #     "You are a helpful assistant.", #that translates {input_language} to {output_language}
        # ),
        # ("human", f"{st.session_state.messages}"),
        # ])
        prompt = [
            (
                "system",
                "You are a helpful assistant that translates English to French. Translate the user sentence.",
            ),
            ("human", f"I love programming"), #{st.session_state.messages}
        ]
        # chain = prompt | llm
        response = llm.invoke(prompt)
        st.session_state.messages.append(ChatMessage(role="assistant", content=response.content))
