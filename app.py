import streamlit as st
from langchain.schema import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from datetime import datetime
import pandas as pd
import json # For handling the JSON credentials

# --- Groq LLM Initialization ---
llm = ChatGroq(
    temperature=0.7,
    groq_api_key=st.secrets["GROQ_API_KEY"],
    model_name="llama3-8b-8192"
)

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Simple Chatbot with Memory")
st.header("Chatbot with Persistent Memory!")

# --- Google Sheets Connection ---
# Convert string credentials to dict for gspread
try:
    gcp_service_account_credentials = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_CREDENTIALS"])
except json.JSONDecodeError:
    st.error("Error loading Google Service Account Credentials. Check your Streamlit secrets format.")
    st.stop() # Stop the app if credentials are bad

# Initialize st.connection for Google Sheets
conn = st.connection(
    "gsheets",
    type="spreadsheet",
    spreadsheet_id=st.secrets["GOOGLE_SHEETS_SPREADSHEET_ID"],
    service_account_info=gcp_service_account_credentials
)

# --- Session Management and Persistent Memory ---
# Generate a unique session ID for this user (for "yesterday's" memory)
if "session_id" not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + st.session_state.get('user_agent', 'default_user').replace('.', '').replace(' ', '')
    # A more robust session ID for multi-user: consider hashing client IP or using a UUID
    # For a simple demo, a timestamp + user agent snippet is ok.

# Load chat history from Google Sheets on app startup
# Use st.cache_data to avoid re-loading on every rerun (except first)
@st.cache_data(ttl=3600) # Cache for 1 hour
def load_chat_history(session_id):
    try:
        # Read the whole sheet (Streamlit Connection doesn't easily filter on read)
        df = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=5) # Adjust worksheet name if needed
        session_df = df[df["session_id"] == session_id].sort_values(by="timestamp")

        messages = []
        if not session_df.empty:
            for index, row in session_df.iterrows():
                if row['sender'] == 'human':
                    messages.append(HumanMessage(content=row['message']))
                elif row['sender'] == 'ai':
                    messages.append(AIMessage(content=row['message']))
        return messages
    except Exception as e:
        st.warning(f"Could not load chat history for session {session_id}. Starting fresh. Error: {e}")
        return []

# Save a message to Google Sheets
def save_message(session_id, sender, message_content):
    # Create a DataFrame for the new row
    new_row_df = pd.DataFrame([{
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "message": message_content
    }])
    try:
        conn.write(worksheet="Sheet1", data=new_row_df, ttl=5) # Write the new row
    except Exception as e:
        st.error(f"Failed to save message to Google Sheet: {e}")

# Initialize chat history in Streamlit's session state
# This combines loaded history with a default greeting if no history
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history(st.session_state.session_id)
    if not st.session_state.messages: # If no history was loaded, start with AI greeting
        ai_initial_message = AIMessage(content="Hello! How can I help you today?")
        st.session_state.messages.append(ai_initial_message)
        save_message(st.session_state.session_id, "ai", ai_initial_message.content) # Save initial greeting

# Display past messages
for msg in st.session_state.messages:
    st.chat_message(msg.type).write(msg.content)

# Get user input
user_input = st.chat_input("Your question:")

if user_input:
    # Add user message to history
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.chat_message("human").write(user_input)
    save_message(st.session_state.session_id, "human", user_input) # Save human message

    # Get AI response
    with st.spinner("Thinking..."):
        ai_response = llm.invoke(st.session_state.messages)
        # Add AI message to history
        st.session_state.messages.append(AIMessage(content=ai_response.content))
        st.chat_message("ai").write(ai_response.content)
        save_message(st.session_state.session_id, "ai", ai_response.content) # Save AI message