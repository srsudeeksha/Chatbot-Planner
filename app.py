# ==============================================
# IMPORTS
# ==============================================
import streamlit as st
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationEntityMemory
from langchain.chains.conversation.prompt import ENTITY_MEMORY_CONVERSATION_TEMPLATE
from langchain_groq import ChatGroq
from groq import BadRequestError
import json
from datetime import datetime
import os
import time

# ==============================================
# CONFIGURATION
# ==============================================
DEFAULT_API_KEY = "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"
USERS_FILE = "users.json"
st.set_page_config(page_title='ChatBot', layout='wide', initial_sidebar_state="expanded")

# ==============================================
# USER AUTHENTICATION
# ==============================================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def signup(username, password):
    users = load_users()
    if username in users:
        return False, "Username already exists."
    users[username] = {
        "password": password,
        "sessions": {
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"): {
                "generated": [],
                "past": []
            }
        }
    }
    save_users(users)
    return True, "Signup successful. Please login."

def login(username, password):
    users = load_users()
    if username in users:
        user_data = users[username]
        if isinstance(user_data, str):
            if user_data == password:
                users[username] = {
                    "password": password,
                    "sessions": {
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"): {
                            "generated": [],
                            "past": []
                        }
                    }
                }
                save_users(users)
                return True, "Login successful."
        elif isinstance(user_data, dict) and user_data.get("password") == password:
            return True, "Login successful."
    return False, "Invalid username or password."

def show_login():
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .login-container {
            background: white;
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            margin: 3rem auto;
        }
        .login-title {
            color: #4a6baf;
            text-align: center;
            font-size: 2.2rem;
            margin-bottom: 1.5rem;
            font-weight: 700;
        }
        .chat-icon {
            text-align: center;
            font-size: 4rem;
            color: #4a6baf;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="login-container">
            <div class="chat-icon">💬</div>
            <h1 class="login-title">Welcome to ChatBot</h1>
        </div>
        """, unsafe_allow_html=True)

        mode = st.radio(
            "Select Mode",
            ["Login", "Signup"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            label_visibility="collapsed"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            label_visibility="collapsed"
        )
        
        if st.button(mode):
            if mode == "Signup":
                success, msg = signup(username, password)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(msg)
            else:
                success, msg = login(username, password)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(msg)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login()
    st.stop()

# ==============================================
# CUSTOM STYLING FOR CHAT INTERFACE
# ==============================================
def apply_custom_styles():
    st.markdown("""
    <style>
        .main { display: flex; flex-direction: column; height: 100vh; }
        .chat-container {
            flex: 1; overflow-y: auto; padding: 10px 20px;
            margin-bottom: 80px;
        }
        .user-message {
            background: #3797F0; color: white; padding: 10px 15px;
            border-radius: 18px; margin: 5px 0; margin-left: auto;
            max-width: 70%; width: fit-content;
        }
        .bot-message {
            background: #f0f2f6; color: black; padding: 10px 15px;
            border-radius: 18px; margin: 5px 0; margin-right: auto;
            max-width: 70%; width: fit-content;
        }
        .input-container {
            position: fixed; bottom: 0; left: 0; right: 0;
            padding: 15px; background: white; z-index: 100;
            border-top: 1px solid #e0e0e0;
        }
        .stApp { overflow: hidden; }
        footer { display: none; }
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# ==============================================
# SESSION MANAGEMENT
# ==============================================
def load_user_sessions(username):
    users = load_users()
    if username in users:
        user_data = users[username]
        if isinstance(user_data, dict):
            return user_data.get("sessions", {})
    return {}

def save_user_sessions(username, sessions):
    users = load_users()
    if username not in users:
        users[username] = {"password": "", "sessions": {}}
    users[username]["sessions"] = sessions
    save_users(users)

# ==============================================
# SESSION STATE INITIALIZATION
# ==============================================
def initialize_session_state():
    keys_defaults = {
        "generated": [], 
        "past": [], 
        "processing": False,
        "entity_memory": None, 
        "llm": None, 
        "conversation": None,
        "stream_output": "",
        "streaming": False
    }
    
    for key, default in keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    if "current_session" not in st.session_state:
        session_name = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.current_session = session_name
        user_sessions = load_user_sessions(st.session_state.username)
        if session_name not in user_sessions:
            user_sessions[session_name] = {"generated": [], "past": []}
            save_user_sessions(st.session_state.username, user_sessions)

    user_sessions = load_user_sessions(st.session_state.username)
    if st.session_state.current_session in user_sessions:
        st.session_state.past = user_sessions[st.session_state.current_session].get("past", [])
        st.session_state.generated = user_sessions[st.session_state.current_session].get("generated", [])

initialize_session_state()

# ==============================================
# SIDEBAR CONTROLS (SIMPLIFIED)
# ==============================================
# ==============================================
# SIDEBAR CONTROLS (SIMPLIFIED)
# ==============================================
def sidebar_controls():
    with st.sidebar:
        st.markdown(f"### 👋 Welcome, {st.session_state.username}!")
        st.markdown(f"**Model:** llama3-70b-8192")  # Display model name only
        st.markdown("---")
        
        if st.button("+ New Chat", type='primary'):
            new_session()

        if st.button("🗑️ Clear Current Chat"):
            clear_current_chat()

        if st.button("📅 Export Chat"):
            export_chat()

        if st.button("🔒 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

        st.markdown("---")
        st.title("Chat Sessions")
        user_sessions = load_user_sessions(st.session_state.username)
        for session in user_sessions:
            if st.button(session, key=f"session_{session}"):
                load_session(session)

def clear_current_chat():
    user_sessions = load_user_sessions(st.session_state.username)
    st.session_state.past = []
    st.session_state.generated = []
    user_sessions[st.session_state.current_session] = {"generated": [], "past": []}
    save_user_sessions(st.session_state.username, user_sessions)
    if st.session_state.entity_memory:
        st.session_state.entity_memory.entity_store = {}
        st.session_state.entity_memory.buffer.clear()
    st.rerun()

def export_chat():
    user_sessions = load_user_sessions(st.session_state.username)
    chat_data = {
        "past": user_sessions[st.session_state.current_session].get("past", []),
        "generated": user_sessions[st.session_state.current_session].get("generated", [])
    }
    st.download_button(
        label="Download Chat",
        data=json.dumps(chat_data, indent=2),
        file_name=f"chat_{st.session_state.current_session}.json",
        mime="application/json"
    )

def load_session(session_name):
    user_sessions = load_user_sessions(st.session_state.username)
    if session_name in user_sessions:
        st.session_state.current_session = session_name
        st.session_state.past = user_sessions[session_name].get("past", [])
        st.session_state.generated = user_sessions[session_name].get("generated", [])
        st.rerun()

def new_session():
    session_name = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.current_session = session_name
    user_sessions = load_user_sessions(st.session_state.username)
    user_sessions[session_name] = {"generated": [], "past": []}
    save_user_sessions(st.session_state.username, user_sessions)
    st.session_state.past = []
    st.session_state.generated = []
    if st.session_state.entity_memory:
        st.session_state.entity_memory.entity_store = {}
        st.session_state.entity_memory.buffer.clear()
    st.rerun()

sidebar_controls()

# ==============================================
# MAIN CHAT INTERFACE
# ==============================================
def initialize_llm():
    try:
        st.session_state.llm = ChatGroq(
            groq_api_key=DEFAULT_API_KEY,
            model_name='llama3-70b-8192',
            temperature=0.1,
            streaming=True
        )
        st.session_state.entity_memory = ConversationEntityMemory(
            llm=st.session_state.llm,
            k=5
        )
        st.session_state.conversation = ConversationChain(
            llm=st.session_state.llm,
            prompt=ENTITY_MEMORY_CONVERSATION_TEMPLATE,
            memory=st.session_state.entity_memory,
            verbose=False
        )
    except BadRequestError as e:
        st.error(f"API Error: {str(e)}")

def run_chatbot():
    st.title("💬 ChatBot")
    chat_container = st.container()
    input_container = st.container()

    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for i in range(len(st.session_state['generated'])):
            st.markdown(f'<div class="user-message">{st.session_state["past"][i]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-message">{st.session_state["generated"][i]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with input_container:
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        form = st.form(key='chat_form', clear_on_submit=True)
        with form:
            cols = st.columns([6, 1])
            with cols[0]:
                user_input = st.text_input(
                    "Type your message...",
                    key="user_input",
                    label_visibility="collapsed",
                    placeholder="Type a message..."
                )
            with cols[1]:
                submitted = st.form_submit_button("Send", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted and user_input.strip() and not st.session_state.processing:
        st.session_state.processing = True
        st.session_state.stream_output = ""
        st.session_state.streaming = True
        try:
            if not st.session_state.llm:
                initialize_llm()

            st.session_state.entity_memory.chat_memory.add_user_message(user_input)

            chat_placeholder = chat_container.empty()
            full_output = ""

            for chunk in st.session_state.llm.stream(user_input):
                full_output += chunk.content
                st.session_state.stream_output = full_output
                chat_placeholder.markdown(f'<div class="chat-container"><div class="bot-message">{full_output}</div></div>', unsafe_allow_html=True)
                time.sleep(0.02)

            st.session_state.entity_memory.chat_memory.add_ai_message(full_output)
            st.session_state.past.append(user_input)
            st.session_state.generated.append(full_output)
            
            user_sessions = load_user_sessions(st.session_state.username)
            user_sessions[st.session_state.current_session] = {
                "past": st.session_state.past,
                "generated": st.session_state.generated
            }
            save_user_sessions(st.session_state.username, user_sessions)

        except Exception as e:
            st.error(f"Error: {str(e)}")

        finally:
            st.session_state.stream_output = ""
            st.session_state.streaming = False
            st.session_state.processing = False
            st.rerun()

run_chatbot()
