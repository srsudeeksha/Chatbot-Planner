# ==============================================
# IMPORT
# ==============================================
import streamlit as st
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationEntityMemory
from langchain.chains.conversation.prompt import ENTITY_MEMORY_CONVERSATION_TEMPLATE
from langchain_groq import ChatGroq
from groq import BadRequestError
import json
from datetime import datetime, timedelta
import os
import time
import re

# ==============================================
# CONFIGURATION
# ==============================================
DEFAULT_API_KEY = "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"
USERS_FILE = "users.json"
st.set_page_config(page_title='ChatBot & Planner', layout='wide', initial_sidebar_state="expanded")

# ==============================================
# PLANNING AGENT PROMPTS
# ==============================================
PLANNER_SYSTEM_PROMPT = """You are a highly sophisticated and well-mannered planning assistant. Your role is to help users create detailed, actionable plans for their goals, tasks, and projects.

Your personality traits:
- Professional yet friendly and approachable
- Thorough and detail-oriented
- Encouraging and supportive
- Proactive in suggesting improvements
- Clear and organized in communication

When creating plans, always:
1. Break down complex goals into manageable steps
2. Suggest realistic timelines
3. Consider potential obstacles and provide contingency plans
4. Prioritize tasks based on importance and urgency
5. Include specific deadlines and milestones
6. Offer encouragement and motivation

Format your responses clearly with:
- Clear headings and subheadings
- Numbered steps or bullet points
- Timeline suggestions
- Priority levels (High, Medium, Low)
- Success metrics where applicable

Always ask clarifying questions if the user's request is vague, and provide actionable, specific advice."""

PLAN_TEMPLATE = """Based on the conversation history and the user's current request, create a comprehensive plan.

Current conversation:
{history}

User's request: {input}

Please provide a detailed, well-structured plan that addresses the user's needs. Include specific steps, timelines, and any relevant advice."""

# ==============================================
# USER AUTHENTICATION (Same as before)
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
        "sessions": {},
        "plans": {}
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
                    "sessions": {},
                    "plans": {}
                }
                save_users(users)
                return True, "Login successful."
        elif isinstance(user_data, dict) and user_data.get("password") == password:
            return True, "Login successful."
    return False, "Invalid username or password."

def show_login():
    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            height: 100%;
            overflow: hidden;
        }

        [data-testid="stAppViewContainer"] > .main {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }

        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 2.5rem 3rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            max-width: 420px;
            margin: 4rem auto;
            text-align: center;
            transition: 0.3s ease-in-out;
        }

        .login-container:hover {
            transform: scale(1.01);
            box-shadow: 0 12px 48px rgba(0,0,0,0.3);
        }

        .chat-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
            color: #6B73FF;
            animation: float 2s ease-in-out infinite;
        }

        @keyframes float {
            0% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
            100% { transform: translateY(0); }
        }

        .login-title {
            font-size: 2.5rem;
            font-weight: 800;
            color: #333;
            margin-bottom: 1.5rem;
        }

        .stTextInput input {
            color: #000000 !important;
            background-color: white !important;
        }

        .stTextInput label {
            color: #000000 !important;
        }

        .stButton>button {
            background-color: #6B73FF !important;
            color: white !important;
            padding: 0.6rem 1.4rem;
            font-size: 1rem;
            border-radius: 12px;
            border: none;
            transition: background 0.3s ease;
        }

        .stButton>button:hover {
            background-color: #000DFF !important;
            transform: scale(1.05);
        }

        .stRadio > div > label {
            color: #000 !important;
            font-weight: 600;
        }
        
        input::placeholder {
            color: white !important;
            opacity: 0.6;
        }

        @media (prefers-color-scheme: light) {
            input::placeholder {
                color: black !important;
                opacity: 0.6;
            }
        }

        @media (prefers-color-scheme: dark) {
            .login-container {
                background: rgba(25, 25, 25, 0.95);
                box-shadow: 0 10px 40px rgba(255,255,255,0.1);
            }

            .chat-icon, .login-title {
                color: #8aa6ff;
            }

            .stTextInput input {
                color: #ffffff !important;
                background-color: #2d2d2d !important;
            }

            .stTextInput label {
                color: #ffffff !important;
            }

            .stRadio > div > label {
                color: #ffffff !important;
            }

            .stButton>button {
                background-color: #8aa6ff !important;
                color: black !important;
            }

            .stButton>button:hover {
                background-color: #c6d5ff !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-container">
        <div class="chat-icon">🤖</div>
        <div class="login-title">Sudeeksha's Bot & Planner</div>
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
        label_visibility="collapsed",
        key="username_input"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter your password",
        label_visibility="collapsed",
        key="password_input"
    )

    if st.button(mode):
        if mode == "Signup":
            success, msg = signup(username, password)
            if success:
                st.success(msg + " Please login now.")
                time.sleep(1)
                st.session_state.signup_done = True
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

    st.markdown("</div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login()
    st.stop()

# ==============================================
# CUSTOM STYLING
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
        .planner-message {
            background: #e8f5e8; color: #2d5a2d; padding: 15px 20px;
            border-radius: 18px; margin: 10px 0; margin-right: auto;
            max-width: 85%; width: fit-content;
            border-left: 4px solid #4CAF50;
        }
        .input-container {
            position: fixed; bottom: 0; left: 0; right: 0;
            padding: 15px; background: white; z-index: 100;
            border-top: 1px solid #e0e0e0;
        }
        .stApp { overflow: hidden; }
        footer { display: none; }
        .session-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 4px 0;
            background: #f8f9fa;
        }
        .session-item:hover {
            background: #e9ecef;
        }
        .delete-btn {
            color: #dc3545;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }
        .plan-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            transition: all 0.3s ease;
        }
        .plan-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        .plan-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .plan-date {
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .plan-preview {
            color: #495057;
            line-height: 1.4;
        }
        .mode-selector {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
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
        users[username] = {"password": "", "sessions": {}, "plans": {}}
    users[username]["sessions"] = sessions
    save_users(users)

def load_user_plans(username):
    users = load_users()
    if username in users:
        user_data = users[username]
        if isinstance(user_data, dict):
            return user_data.get("plans", {})
    return {}

def save_user_plans(username, plans):
    users = load_users()
    if username not in users:
        users[username] = {"password": "", "sessions": {}, "plans": {}}
    users[username]["plans"] = plans
    save_users(users)

def delete_session(session_name):
    user_sessions = load_user_sessions(st.session_state.username)
    if session_name in user_sessions:
        del user_sessions[session_name]
        save_user_sessions(st.session_state.username, user_sessions)
        
        if session_name == st.session_state.current_session:
            new_session()
        else:
            st.rerun()

def delete_plan(plan_name):
    user_plans = load_user_plans(st.session_state.username)
    if plan_name in user_plans:
        del user_plans[plan_name]
        save_user_plans(st.session_state.username, user_plans)
        st.rerun()

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
        "planner_llm": None,
        "stream_output": "",
        "streaming": False,
        "app_mode": "Chat",  # Chat or Planner
        "current_plan": None,
        "plan_history": []
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
# SIDEBAR CONTROLS
# ==============================================
def sidebar_controls():
    with st.sidebar:
        st.markdown(f"### 👋 Welcome, {st.session_state.username}!")
        
        # Mode selector
        
        mode = st.radio(
            "Choose Mode:",
            ["💬 Chat", "📋 Planner"],
            index=0 if st.session_state.app_mode == "Chat" else 1,
            horizontal=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if mode == "💬 Chat":
            st.session_state.app_mode = "Chat"
        else:
            st.session_state.app_mode = "Planner"
        
        st.markdown(f"**Model:** llama3-70b-8192")
        st.markdown("---")
        
        if st.session_state.app_mode == "Chat":
            chat_sidebar_controls()
        else:
            planner_sidebar_controls()
        
        st.markdown("---")
        if st.button("🔒 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

def chat_sidebar_controls():
    if st.button("+ New Chat", type='primary'):
        new_session()

    if st.button("🗑️ Clear Current Chat"):
        clear_current_chat()

    if st.button("📅 Download Chat"):
        export_chat()

    st.markdown("### Chat Sessions")
    user_sessions = load_user_sessions(st.session_state.username)
    for session in sorted(user_sessions.keys(), reverse=True):
        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(session[:16] + "...", key=f"session_{session}"):
                load_session(session)
        with cols[1]:
            if st.button("🗑️", key=f"delete_{session}"):
                delete_session(session)

def planner_sidebar_controls():
    if st.button("+ New Plan", type='primary'):
        st.session_state.current_plan = None
        st.session_state.plan_history = []

    if st.button("📋 View All Plans"):
        show_all_plans()

    st.markdown("### Plan Sessions")
    user_plans = load_user_plans(st.session_state.username)
    for plan_name in sorted(user_plans.keys(), reverse=True)[:5]:
        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(plan_name[:16] + "...", key=f"plan_{plan_name}"):
                load_plan(plan_name)
        with cols[1]:
            if st.button("🗑️", key=f"delete_plan_{plan_name}"):
                delete_plan(plan_name)

# ==============================================
# CHAT FUNCTIONS
# ==============================================
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
    current_session_data = user_sessions.get(st.session_state.current_session, {})
    
    past = current_session_data.get("past", [])
    generated = current_session_data.get("generated", [])

    json_data = {
        "past": past,
        "generated": generated
    }
    json_str = json.dumps(json_data, indent=2)

    txt_data = ""
    for user_msg, bot_msg in zip(past, generated):
        txt_data += f"User: {user_msg}\nBot: {bot_msg}\n\n"

    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download as JSON",
            data=json_str,
            file_name=f"chat_{st.session_state.current_session}.json",
            mime="application/json"
        )

    with col2:
        st.download_button(
            label="Download as TXT",
            data=txt_data,
            file_name=f"chat_{st.session_state.current_session}.txt",
            mime="text/plain"
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

# ==============================================
# PLANNER FUNCTIONS
# ==============================================
def initialize_planner_llm():
    try:
        st.session_state.planner_llm = ChatGroq(
            groq_api_key=DEFAULT_API_KEY,
            model_name='llama3-70b-8192',
            temperature=0.3,
            streaming=True
        )
    except BadRequestError as e:
        st.error(f"API Error: {str(e)}")

def create_plan(user_request):
    if not st.session_state.planner_llm:
        initialize_planner_llm()
    
    # Create conversation history context
    history_context = ""
    if st.session_state.plan_history:
        history_context = "\n".join([
            f"User: {entry['request']}\nPlanner: {entry['response'][:200]}..."
            for entry in st.session_state.plan_history[-3:]  # Last 3 interactions
        ])
    
    # Format the prompt
    prompt = f"{PLANNER_SYSTEM_PROMPT}\n\n{PLAN_TEMPLATE.format(history=history_context, input=user_request)}"
    
    try:
        full_response = ""
        for chunk in st.session_state.planner_llm.stream(prompt):
            full_response += chunk.content
            yield chunk.content
        
        # Save the plan interaction
        plan_entry = {
            "request": user_request,
            "response": full_response,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.plan_history.append(plan_entry)
        
        # Save plan to user's plans if it's substantial
        if len(full_response) > 200:
            save_plan_to_storage(user_request, full_response)
            
    except Exception as e:
        yield f"I apologize, but I encountered an error while creating your plan: {str(e)}"

def save_plan_to_storage(title, content):
    plan_name = f"{title[:50]}..." if len(title) > 50 else title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    user_plans = load_user_plans(st.session_state.username)
    user_plans[f"{timestamp} - {plan_name}"] = {
        "title": title,
        "content": content,
        "created_at": timestamp
    }
    save_user_plans(st.session_state.username, user_plans)

def load_plan(plan_name):
    user_plans = load_user_plans(st.session_state.username)
    if plan_name in user_plans:
        plan_data = user_plans[plan_name]
        st.session_state.current_plan = plan_data
        st.rerun()

def show_all_plans():
    st.session_state.show_all_plans = True

# ==============================================
# LLM INITIALIZATION
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

# ==============================================
# MAIN INTERFACES
# ==============================================
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
                    "Type your message....",
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

def run_planner():
    # Add custom CSS for chat-like interface
    st.markdown("""
    <style>
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 10px 15px;
        border-radius: 18px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: auto;
        margin-right: 0;
        word-wrap: break-word;
        text-align: right;
    }
    
    .planner-message {
        background-color: #f1f1f1;
        color: #333;
        padding: 10px 15px;
        border-radius: 18px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: 0;
        margin-right: auto;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    
    .planner-message.loading {
        background-color: #e9ecef;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📋 Planning Assistant")
    
    # Show current plan if one is loaded
    if st.session_state.current_plan:
        st.markdown("### Current Plan")
        with st.expander("📋 Plan Details", expanded=True):
            st.markdown(f"**Title:** {st.session_state.current_plan['title']}")
            st.markdown(f"**Created:** {st.session_state.current_plan['created_at']}")
            st.markdown("**Plan Content:**")
            st.markdown(st.session_state.current_plan['content'])
        
        if st.button("🔄 Create New Plan"):
            st.session_state.current_plan = None
            st.rerun()
        
        st.markdown("---")
    
    # Show plan history
    if st.session_state.plan_history:
        st.markdown("### Current Planning Session")
        
        for i, entry in enumerate(st.session_state.plan_history):
            # User message (right side)
            st.markdown(f'<div class="user-message">{entry.get("request", "No request")}</div>', unsafe_allow_html=True)
            
            # Planner response (left side)
            response = entry.get("response", "")
            if response:
                if response == "Generating plan...":
                    st.markdown(f'<div class="planner-message loading">🔄 {response}</div>', unsafe_allow_html=True)
                else:
                    # Escape HTML and show the response
                    import html
                    escaped_response = html.escape(str(response))
                    st.markdown(f'<div class="planner-message">{escaped_response}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="planner-message">❌ No response generated</div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Planning input
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    form = st.form(key='planner_form', clear_on_submit=True)
    with form:
        st.markdown("### What would you like to plan?")
        planning_examples = [
            "Plan a 30-day fitness routine for beginners",
            "Create a study schedule for my upcoming exams",
            "Help me plan a weekend trip to a nearby city",
            "Design a meal prep plan for the week",
            "Plan a career transition strategy",
            "Create a budget plan for saving money"
        ]
        
        example_choice = st.selectbox(
            "Choose an example or write your own:",
            ["Custom request"] + planning_examples,
            key="example_selector"
        )
        
        if example_choice == "Custom request":
            user_request = st.text_area(
                "Describe what you'd like to plan:",
                placeholder="Be as detailed as possible about your goals, timeline, constraints, and preferences...",
                height=100
            )
        else:
            user_request = example_choice
            st.info(f"Selected example: {example_choice}")
        
        submitted = st.form_submit_button("🚀 Create Plan", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle form submission
    if submitted and user_request.strip():
        # Check if we're already processing this request
        if not st.session_state.processing:
            st.session_state.processing = True
            st.session_state.current_request = user_request
            
            # Add loading entry
            loading_entry = {
                "request": user_request,
                "response": "Generating plan...",
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.plan_history.append(loading_entry)
            st.rerun()
    
    # Process the request if we're in processing state
    if st.session_state.processing and hasattr(st.session_state, 'current_request'):
        try:
            if not st.session_state.planner_llm:
                initialize_planner_llm()
            
            # Get the planning response
            response_generator = create_plan(st.session_state.current_request)
            
            # If create_plan returns a generator, consume it
            if hasattr(response_generator, '__iter__') and not isinstance(response_generator, (str, bytes)):
                response = ''.join(str(chunk) for chunk in response_generator)
            else:
                response = str(response_generator)
            
            # Update the last entry with the actual response
            if st.session_state.plan_history and st.session_state.plan_history[-1]["response"] == "Generating plan...":
                st.session_state.plan_history[-1]["response"] = response
            
        except Exception as e:
            st.error(f"Error creating plan: {str(e)}")
            # Remove the loading entry if there was an error
            if st.session_state.plan_history and st.session_state.plan_history[-1]["response"] == "Generating plan...":
                st.session_state.plan_history.pop()
        
        finally:
            # Clean up processing state
            st.session_state.processing = False
            if hasattr(st.session_state, 'current_request'):
                delattr(st.session_state, 'current_request')
            st.rerun()

def show_all_plans_page():
    st.title("📋 All Your Plans")
    
    user_plans = load_user_plans(st.session_state.username)
    
    if not user_plans:
        st.info("You haven't created any plans yet. Start by creating your first plan!")
        if st.button("🚀 Create First Plan"):
            st.session_state.show_all_plans = False
            st.rerun()
        return
    
    # Search and filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Search plans...", placeholder="Search by title or content")
    with col2:
        sort_order = st.selectbox("Sort by", ["Newest First", "Oldest First", "Alphabetical"])
    
    # Filter and sort plans
    filtered_plans = user_plans.copy()
    
    if search_term:
        filtered_plans = {
            name: plan for name, plan in user_plans.items()
            if search_term.lower() in plan.get('title', '').lower() or 
               search_term.lower() in plan.get('content', '').lower()
        }
    
    if sort_order == "Newest First":
        sorted_plans = sorted(filtered_plans.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
    elif sort_order == "Oldest First":
        sorted_plans = sorted(filtered_plans.items(), key=lambda x: x[1].get('created_at', ''))
    else:  # Alphabetical
        sorted_plans = sorted(filtered_plans.items(), key=lambda x: x[1].get('title', '').lower())
    
    st.markdown(f"**Found {len(sorted_plans)} plan(s)**")
    
    # Display plans
    for plan_name, plan_data in sorted_plans:
        with st.container():
            st.markdown('<div class="plan-card">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([6, 1, 1])
            
            with col1:
                st.markdown(f'<div class="plan-title">{plan_data.get("title", "Untitled Plan")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-date">📅 Created: {plan_data.get("created_at", "Unknown")}</div>', unsafe_allow_html=True)
                
                # Show preview of content
                content_preview = plan_data.get('content', '')[:200] + "..." if len(plan_data.get('content', '')) > 200 else plan_data.get('content', '')
                st.markdown(f'<div class="plan-preview">{content_preview}</div>', unsafe_allow_html=True)
            
            with col2:
                if st.button("👁️ View", key=f"view_{plan_name}"):
                    st.session_state.current_plan = plan_data
                    st.session_state.show_all_plans = False
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete", key=f"delete_all_{plan_name}"):
                    delete_plan(plan_name)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
    
    # Back button
    if st.button("⬅️ Back to Planner"):
        st.session_state.show_all_plans = False
        st.rerun()

# ==============================================
# MAIN APPLICATION
# ==============================================
def main():
    sidebar_controls()
    
    # Check if showing all plans
    if hasattr(st.session_state, 'show_all_plans') and st.session_state.show_all_plans:
        show_all_plans_page()
        return
    
    if st.session_state.app_mode == "Chat":
        run_chatbot()
    else:
        run_planner()

if __name__ == "__main__":
    main()