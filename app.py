import streamlit as st
from langchain.schema import HumanMessage, AIMessage
from langchain_groq import ChatGroq
import sqlite3
from datetime import datetime
import hashlib

# Initialize database
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
                 (session_id TEXT PRIMARY KEY,
                  session_name TEXT,
                  created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  message_type TEXT,
                  content TEXT,
                  timestamp TIMESTAMP,
                  FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id))''')
    conn.commit()
    conn.close()

init_db()

# Initialize Groq client
llm = ChatGroq(
    temperature=0.7,
    groq_api_key=st.secrets["GROQ_API_KEY"],
    model_name="llama3-8b-8192"
)

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="Chatbot with History",
    page_icon="🤖",
    layout="wide",  # Changed to "wide" to ensure sidebar has enough space
    initial_sidebar_state="expanded"  # This ensures sidebar is visible by default
)

# Generate unique session ID
def generate_session_id():
    return hashlib.md5(str(datetime.now()).encode()).hexdigest()

# Database operations
def get_chat_sessions():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT session_id, session_name FROM chat_sessions ORDER BY created_at DESC")
    sessions = c.fetchall()
    conn.close()
    return sessions

def get_messages(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT message_type, content FROM messages WHERE session_id = ? ORDER BY timestamp", (session_id,))
    messages = [AIMessage(content=row[1]) if row[0] == "ai" else HumanMessage(content=row[1]) for row in c.fetchall()]
    conn.close()
    return messages

def save_message(session_id, message, session_name=None):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    # Check if session exists
    c.execute("SELECT 1 FROM chat_sessions WHERE session_id = ?", (session_id,))
    if not c.fetchone():
        c.execute("INSERT INTO chat_sessions (session_id, session_name, created_at) VALUES (?, ?, ?)",
                 (session_id, session_name or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}", datetime.now()))
    
    c.execute("INSERT INTO messages (session_id, message_type, content, timestamp) VALUES (?, ?, ?, ?)",
             (session_id, "ai" if isinstance(message, AIMessage) else "human", message.content, datetime.now()))
    conn.commit()
    conn.close()

def update_session_name(session_id, new_name):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("UPDATE chat_sessions SET session_name = ? WHERE session_id = ?", (new_name, session_id))
    conn.commit()
    conn.close()

# Initialize session state
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = generate_session_id()
    save_message(st.session_state.current_session_id, AIMessage(content="Hello! How can I help you today?"))

# Sidebar for chat history - made more prominent
with st.sidebar:
    st.markdown("""
    <style>
        .sidebar .sidebar-content {
            width: 350px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("💬 Chat History")
    
    # Button to create new chat
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.current_session_id = generate_session_id()
        save_message(st.session_state.current_session_id, AIMessage(content="Hello! How can I help you today?"))
        st.rerun()
    
    # Display chat sessions with better formatting
    st.subheader("Your Conversations")
    sessions = get_chat_sessions()
    
    if not sessions:
        st.write("No previous conversations")
    else:
        for session_id, session_name in sessions:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                if st.button(
                    f"🗨️ {session_name}",
                    key=f"session_{session_id}",
                    use_container_width=True,
                ):
                    st.session_state.current_session_id = session_id
                    st.rerun()
            with col2:
                if st.button("×", key=f"del_{session_id}"):
                    # Add delete functionality here if needed
                    pass

# Main chat area
current_messages = get_messages(st.session_state.current_session_id)
current_session_name = next((name for sid, name in get_chat_sessions() if sid == st.session_state.current_session_id), "New Chat")

st.header(current_session_name)

# Display messages
for msg in current_messages:
    st.chat_message(msg.type).write(msg.content)

# Get user input
user_input = st.chat_input("Your message:")

if user_input:
    # Save user message
    user_msg = HumanMessage(content=user_input)
    save_message(st.session_state.current_session_id, user_msg)
    
    # Display user message
    st.chat_message("human").write(user_input)
    
    # Get AI response
    with st.spinner("Thinking..."):
        # Get all messages for context
        conversation_history = get_messages(st.session_state.current_session_id)
        ai_response = llm.invoke(conversation_history)
        
        # Save and display AI response
        save_message(st.session_state.current_session_id, AIMessage(content=ai_response.content))
        st.chat_message("ai").write(ai_response.content)
    
    # Update session name if it's a new chat
    if current_session_name.startswith("Chat ") or current_session_name == "New Chat":
        new_name = user_input[:30] + "..." if len(user_input) > 30 else user_input
        update_session_name(st.session_state.current_session_id, new_name)
        st.rerun()