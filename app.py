import streamlit as st
from langchain.schema import HumanMessage, AIMessage
from langchain_groq import ChatGroq # Add this line
import os

llm = ChatGroq(
    temperature=0.7,
    groq_api_key=st.secrets["GROQ_API_KEY"], # Use the key name "GROQ_API_KEY"
    model_name="llama3-8b-8192" # Or "mixtral-8x7b-32768", "gemma-7b-it", etc.
)

# --- Streamlit App ---
st.set_page_config(page_title="Simple Chatbot")
st.header("Ask Me Anything!")

# Initialize chat history in Streamlit's session state
if "messages" not in st.session_state:
    st.session_state.messages = [AIMessage(content="Hello! How can I help?")]

# Display past messages
for msg in st.session_state.messages:
    st.chat_message(msg.type).write(msg.content)

# Get user input
user_input = st.chat_input("Your question:")

if user_input:
    # Add user message to history
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.chat_message("human").write(user_input)

    # Get AI response
    with st.spinner("Thinking..."):
        ai_response = llm.invoke(st.session_state.messages)
        # Add AI message to history
        st.session_state.messages.append(AIMessage(content=ai_response.content))
        st.chat_message("ai").write(ai_response.content)