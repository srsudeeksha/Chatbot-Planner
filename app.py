import streamlit as st
#from langchain_openai import ChatOpenAI # For OpenAI models
# from langchain_google_genai import ChatGoogleGenerativeAI # For Google's Gemini/PaLM models
from langchain.schema import HumanMessage, AIMessage

from langchain_groq import ChatGroq # Add this line
import os
# Initialize the Language Model with Groq
# You can choose a model like "llama3-8b-8192" or "llama3-70b-8192" etc.
# Check Groq's documentation for available models and their names.
llm = ChatGroq(
    temperature=0.7,
    groq_api_key=st.secrets["GROQ_API_KEY"], # Use the key name "GROQ_API_KEY"
    model_name="llama3-8b-8192" # Or "mixtral-8x7b-32768", "gemma-7b-it", etc.
)
# --- Configuration ---
# Streamlit Cloud will securely provide API keys via st.secrets
# For local testing, you can uncomment these lines IF you've set them in your environment
# os.environ["OPENAI_API_KEY"] = "YOUR_LOCAL_OPENAI_API_KEY_HERE"
# os.environ["GOOGLE_API_KEY"] = "YOUR_LOCAL_GOOGLE_API_KEY_HERE" # If using Google

# Initialize the Language Model
# Access API key securely from st.secrets for deployment
# For OpenAI:
# llm = ChatOpenAI(temperature=0.7, api_key=st.secrets["OPENAI_API_KEY"])
# Or for Google (uncomment and remove OpenAI line if using Google):
# llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.0, google_api_key=st.secrets["GOOGLE_API_KEY"])

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