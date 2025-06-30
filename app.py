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
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
import asyncio
import uuid

# ==============================================
# CONFIGURATION
# ==============================================
DEFAULT_API_KEY = "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"
USERS_FILE = "users.json"
st.set_page_config(page_title='Multi-Agent System', layout='wide', initial_sidebar_state="expanded")

# ==============================================
# MULTI-AGENT STATE DEFINITION
# ==============================================
class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    user_request: str
    task_type: str
    research_data: str
    plan_content: str
    review_feedback: str
    final_output: str
    current_agent: str
    workflow_status: str
    agent_outputs: Dict[str, str]

# ==============================================
# AGENT PROMPTS
# ==============================================
ROUTER_SYSTEM_PROMPT = """You are a Task Router Agent. Your job is to analyze user requests and determine the appropriate workflow.

Classify the request into one of these categories:
1. "planning" - User wants to create plans, schedules, organize tasks, set goals
2. "research" - User wants information, analysis, or investigation on a topic
3. "chat" - General conversation, questions, or casual interaction
4. "complex" - Requests that need both research and planning

Respond with ONLY the category name (planning/research/chat/complex).

Examples:
- "Help me plan a vacation to Japan" → planning
- "What are the benefits of meditation?" → research
- "How are you doing today?" → chat
- "Research the best programming languages and create a learning plan" → complex
"""

RESEARCH_SYSTEM_PROMPT = """You are a Research Agent specialized in gathering, analyzing, and synthesizing information.

Your responsibilities:
1. Thoroughly research the given topic
2. Provide comprehensive, accurate information
3. Include relevant facts, statistics, and insights
4. Structure information clearly and logically
5. Cite sources when possible
6. Highlight key findings and important points

Always provide detailed, well-researched responses that can be used by other agents for further processing.
"""

PLANNING_SYSTEM_PROMPT = """You are a Planning Agent specialized in creating detailed, actionable plans and strategies.

Your responsibilities:
1. Create comprehensive, step-by-step plans
2. Set realistic timelines and milestones
3. Consider resource requirements and constraints
4. Provide contingency plans for potential obstacles
5. Include success metrics and evaluation criteria
6. Structure plans with clear priorities and dependencies

Always create practical, implementable plans that users can follow to achieve their goals.
"""

REVIEW_SYSTEM_PROMPT = """You are a Review Agent responsible for quality assurance and final output optimization.

Your responsibilities:
1. Review all agent outputs for accuracy and completeness
2. Ensure consistency across different agent contributions
3. Identify gaps or areas for improvement
4. Synthesize information into a coherent final response
5. Add executive summary or key takeaways
6. Ensure the output directly addresses the user's original request

Provide constructive feedback and create polished final outputs that exceed user expectations.
"""

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
        "plans": {},
        "agent_workflows": {}
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
                    "plans": {},
                    "agent_workflows": {}
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
            font-size: 2.2rem;
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
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-container">
        <div class="chat-icon">🤖</div>
        <div class="login-title">Multi-Agent System</div>
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
# MULTI-AGENT SYSTEM CLASSES
# ==============================================
class MultiAgentSystem:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agents = {}
        self.workflow = None
        self.initialize_agents()
        self.create_workflow()
    
    def initialize_agents(self):
        """Initialize all agents with their specific LLMs"""
        try:
            self.agents = {
                "router": ChatGroq(groq_api_key=self.api_key, model_name='llama3-70b-8192', temperature=0.1),
                "researcher": ChatGroq(groq_api_key=self.api_key, model_name='llama3-70b-8192', temperature=0.3),
                "planner": ChatGroq(groq_api_key=self.api_key, model_name='llama3-70b-8192', temperature=0.2),
                "reviewer": ChatGroq(groq_api_key=self.api_key, model_name='llama3-70b-8192', temperature=0.1)
            }
        except Exception as e:
            st.error(f"Failed to initialize agents: {str(e)}")
    
    def router_agent(self, state: AgentState) -> AgentState:
        """Route the task to appropriate workflow"""
        try:
            messages = [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=state["user_request"])
            ]
            
            response = self.agents["router"].invoke(messages)
            task_type = response.content.strip().lower()
            
            state["task_type"] = task_type
            state["current_agent"] = "router"
            state["workflow_status"] = f"Task classified as: {task_type}"
            state["agent_outputs"]["router"] = f"Task type: {task_type}"
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Router error: {str(e)}"
            return state
    
    def research_agent(self, state: AgentState) -> AgentState:
        """Conduct research on the given topic"""
        try:
            if state["task_type"] in ["research", "complex"]:
                messages = [
                    SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
                    HumanMessage(content=f"Research request: {state['user_request']}")
                ]
                
                response = self.agents["researcher"].invoke(messages)
                state["research_data"] = response.content
                state["current_agent"] = "researcher"
                state["workflow_status"] = "Research completed"
                state["agent_outputs"]["researcher"] = response.content
            else:
                state["research_data"] = "No research required for this task type"
                state["agent_outputs"]["researcher"] = "Skipped - not required"
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Research error: {str(e)}"
            return state
    
    def planning_agent(self, state: AgentState) -> AgentState:
        """Create detailed plans based on research or direct request"""
        try:
            if state["task_type"] in ["planning", "complex"]:
                context = f"User request: {state['user_request']}\n"
                if state["research_data"] and state["research_data"] != "No research required for this task type":
                    context += f"Research findings: {state['research_data']}\n"
                
                messages = [
                    SystemMessage(content=PLANNING_SYSTEM_PROMPT),
                    HumanMessage(content=f"Create a plan based on: {context}")
                ]
                
                response = self.agents["planner"].invoke(messages)
                state["plan_content"] = response.content
                state["current_agent"] = "planner"
                state["workflow_status"] = "Planning completed"
                state["agent_outputs"]["planner"] = response.content
            else:
                state["plan_content"] = "No planning required for this task type"
                state["agent_outputs"]["planner"] = "Skipped - not required"
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Planning error: {str(e)}"
            return state
    
    def review_agent(self, state: AgentState) -> AgentState:
        """Review and synthesize all agent outputs"""
        try:
            review_context = f"""
            Original request: {state['user_request']}
            Task type: {state['task_type']}
            Research data: {state.get('research_data', 'None')}
            Plan content: {state.get('plan_content', 'None')}
            
            Please review and create a comprehensive final response.
            """
            
            messages = [
                SystemMessage(content=REVIEW_SYSTEM_PROMPT),
                HumanMessage(content=review_context)
            ]
            
            response = self.agents["reviewer"].invoke(messages)
            state["final_output"] = response.content
            state["current_agent"] = "reviewer"
            state["workflow_status"] = "Review completed - Final output ready"
            state["agent_outputs"]["reviewer"] = response.content
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Review error: {str(e)}"
            return state
    
    def should_continue_to_research(self, state: AgentState) -> str:
        """Decide if research is needed"""
        if state["task_type"] in ["research", "complex"]:
            return "research"
        return "planning"
    
    def should_continue_to_planning(self, state: AgentState) -> str:
        """Decide if planning is needed after research"""
        if state["task_type"] in ["planning", "complex"]:
            return "planning"
        return "review"
    
    def should_continue_to_review(self, state: AgentState) -> str:
        """Always continue to review"""
        return "review"
    
    def create_workflow(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self.router_agent)
        workflow.add_node("research", self.research_agent)
        workflow.add_node("planning", self.planning_agent)
        workflow.add_node("review", self.review_agent)
        
        # Add edges
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self.should_continue_to_research,
            {
                "research": "research",
                "planning": "planning"
            }
        )
        workflow.add_conditional_edges(
            "research",
            self.should_continue_to_planning,
            {
                "planning": "planning",
                "review": "review"
            }
        )
        workflow.add_conditional_edges(
            "planning",
            self.should_continue_to_review,
            {
                "review": "review"
            }
        )
        workflow.add_edge("review", END)
        
        self.workflow = workflow.compile()
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """Process a user request through the multi-agent workflow"""
        initial_state = AgentState(
            messages=[],
            user_request=user_request,
            task_type="",
            research_data="",
            plan_content="",
            review_feedback="",
            final_output="",
            current_agent="",
            workflow_status="Starting workflow...",
            agent_outputs={}
        )
        
        try:
            result = self.workflow.invoke(initial_state)
            return result
        except Exception as e:
            return {
                "final_output": f"Workflow error: {str(e)}",
                "workflow_status": "Error occurred",
                "agent_outputs": {"error": str(e)}
            }

# ==============================================
# CUSTOM STYLING
# ==============================================
def apply_custom_styles():
    st.markdown("""
    <style>
        .main { display: flex; flex-direction: column; height: 100vh; }
        .agent-workflow-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
        }
        .agent-step {
            background: white;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            border-left: 3px solid #28a745;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .agent-step.active {
            border-left-color: #ffc107;
            background: #fff3cd;
        }
        .agent-step.completed {
            border-left-color: #28a745;
            background: #d4edda;
        }
        .agent-step.error {
            border-left-color: #dc3545;
            background: #f8d7da;
        }
        .workflow-progress {
            background: #e9ecef;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .user-message {
            background: #3797F0;
            color: white;
            padding: 10px 15px;
            border-radius: 18px;
            margin: 5px 0;
            margin-left: auto;
            max-width: 70%;
            width: fit-content;
        }
        .agent-message {
            background: #f0f2f6;
            color: black;
            padding: 15px 20px;
            border-radius: 18px;
            margin: 10px 0;
            margin-right: auto;
            max-width: 85%;
            width: fit-content;
            border-left: 4px solid #007bff;
        }
        .final-output {
            background: #d4edda;
            color: #155724;
            padding: 20px;
            border-radius: 15px;
            margin: 15px 0;
            border-left: 4px solid #28a745;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .agent-tabs {
            background: white;
            border-radius: 10px;
            padding: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# ==============================================
# SESSION STATE INITIALIZATION
# ==============================================
def initialize_session_state():
    keys_defaults = {
        "multi_agent_system": None,
        "workflow_history": [],
        "current_workflow": None,
        "workflow_in_progress": False,
        "app_mode": "Multi-Agent Chat"
    }
    
    for key, default in keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

initialize_session_state()

# ==============================================
# WORKFLOW MANAGEMENT
# ==============================================
def save_workflow_to_user(workflow_result):
    """Save workflow result to user's data"""
    users = load_users()
    username = st.session_state.username
    
    if username in users:
        if "agent_workflows" not in users[username]:
            users[username]["agent_workflows"] = {}
        
        workflow_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        users[username]["agent_workflows"][f"{timestamp}_{workflow_id}"] = {
            "request": workflow_result.get("user_request", ""),
            "result": workflow_result,
            "timestamp": timestamp
        }
        
        save_users(users)

def load_user_workflows():
    """Load user's workflow history"""
    users = load_users()
    username = st.session_state.username
    
    if username in users:
        return users[username].get("agent_workflows", {})
    return {}

# ==============================================
# SIDEBAR CONTROLS
# ==============================================
def sidebar_controls():
    with st.sidebar:
        st.markdown(f"### 🤖 Multi-Agent System")
        st.markdown(f"**User:** {st.session_state.username}")
        st.markdown("**Model:** llama3-70b-8192")
        st.markdown("---")
        
        # Mode selection
        mode = st.radio(
            "System Mode:",
            ["🤖 Multi-Agent Chat", "📊 Workflow History", "⚙️ Agent Status"],
            index=0
        )
        
        if mode == "🤖 Multi-Agent Chat":
            st.session_state.app_mode = "Multi-Agent Chat"
        elif mode == "📊 Workflow History":
            st.session_state.app_mode = "Workflow History"
        else:
            st.session_state.app_mode = "Agent Status"
        
        st.markdown("---")
        
        # Agent system controls
        if st.button("🔄 Reset Agent System"):
            st.session_state.multi_agent_system = None
            st.session_state.current_workflow = None
            st.session_state.workflow_in_progress = False
            st.rerun()
        
        if st.button("📋 Clear Workflow History"):
            st.session_state.workflow_history = []
            st.rerun()
        
        st.markdown("---")
        
        # Workflow history preview
        if st.session_state.workflow_history:
            st.markdown("### Recent Workflows")
            for i, workflow in enumerate(st.session_state.workflow_history[-3:]):
                with st.expander(f"Workflow {len(st.session_state.workflow_history) - i}"):
                    st.write(f"**Request:** {workflow.get('user_request', 'N/A')[:50]}...")
                    st.write(f"**Status:** {workflow.get('workflow_status', 'N/A')}")
        
        st.markdown("---")
        if st.button("🔒 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

# ==============================================
# MAIN INTERFACES
# ==============================================
def run_multi_agent_chat():
    st.title("🤖 Multi-Agent AI System")
    st.markdown("**Four specialized agents working together: Router → Researcher → Planner → Reviewer**")
    
    # Initialize multi-agent system
    if not st.session_state.multi_agent_system:
        with st.spinner("Initializing multi-agent system..."):
            st.session_state.multi_agent_system = MultiAgentSystem(DEFAULT_API_KEY)
        st.success("Multi-agent system initialized!")
    
    # Display workflow history
    if st.session_state.workflow_history:
        st.markdown("### Conversation History")
        for i, workflow in enumerate(st.session_state.workflow_history):
            # User message
            st.markdown(f'<div class="user-message">{workflow.get("user_request", "")}</div>', unsafe_allow_html=True)
            
            # Agent workflow result
            final_output = workflow.get("final_output", "No output generated")
            st.markdown(f'<div class="final-output"><strong>🤖 Multi-Agent Response:</strong><br>{final_output}</div>', unsafe_allow_html=True)
            
            # Show workflow details in expander
            with st.expander(f"🔍 View Agent Workflow Details #{i+1}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("**Workflow Status:**")
                    st.info(workflow.get("workflow_status", "Unknown"))
                    
                    st.markdown("**Task Type:**")
                    st.info(workflow.get("task_type", "Unknown"))
                
                with col2:
                    st.markdown("**Agent Outputs:**")
                    agent_outputs = workflow.get("agent_outputs", {})
                    
                    for agent_name, output in agent_outputs.items():
                        with st.expander(f"🤖 {agent_name.title()} Agent"):
                            if output and output not in ["Skipped - not required", ""]:
                                st.write(output[:500] + "..." if len(str(output)) > 500 else output)
                            else:
                                st.write("No output or skipped")
            
            st.markdown("---")
    
    # Current workflow progress
    if st.session_state.workflow_in_progress and st.session_state.current_workflow:
        st.markdown("### 🔄 Workflow in Progress")
        workflow = st.session_state.current_workflow
        
        progress_container = st.container()
        with progress_container:
            st.markdown('<div class="workflow-progress">', unsafe_allow_html=True)
            st.markdown(f"**Current Status:** {workflow.get('workflow_status', 'Processing...')}")
            st.markdown(f"**Current Agent:** {workflow.get('current_agent', 'Unknown').title()}")
            
            # Progress indicators
            agents = ["router", "researcher", "planner", "reviewer"]
            cols = st.columns(4)
            
            for i, agent in enumerate(agents):
                with cols[i]:
                    if agent in workflow.get("agent_outputs", {}):
                        st.success(f"✅ {agent.title()}")
                    elif workflow.get("current_agent") == agent:
                        st.warning(f"🔄 {agent.title()}")
                    else:
                        st.info(f"⏳ {agent.title()}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Input form
    st.markdown("### 💭 Ask the Multi-Agent System")
    with st.form(key='multi_agent_form', clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_area(
                "What would you like the agents to help you with?",
                placeholder="Examples:\n- Research renewable energy and create an implementation plan\n- Plan a career transition to data science\n- Analyze market trends for electric vehicles",
                height=100
            )
        
        with col2:
            st.markdown("**Agent Flow:**")
            st.markdown("1. 🎯 Router")
            st.markdown("2. 🔍 Researcher")
            st.markdown("3. 📋 Planner")
            st.markdown("4. ✅ Reviewer")
        
        submitted = st.form_submit_button("🚀 Process with Agents", type="primary")
    
    # Process the request
    if submitted and user_input.strip() and not st.session_state.workflow_in_progress:
        st.session_state.workflow_in_progress = True
        
        # Create progress placeholder
        progress_placeholder = st.empty()
        
        try:
            with st.spinner("🤖 Multi-agent system processing your request..."):
                # Process the request through the workflow
                result = st.session_state.multi_agent_system.process_request(user_input)
                
                # Update session state
                st.session_state.current_workflow = result
                st.session_state.workflow_history.append(result)
                
                # Save to user data
                save_workflow_to_user(result)
        
        except Exception as e:
            st.error(f"Error processing request: {str(e)}")
        
        finally:
            st.session_state.workflow_in_progress = False
            st.rerun()

def run_workflow_history():
    st.title("📊 Workflow History")
    
    # Load both persistent and session workflows
    user_workflows = load_user_workflows()
    session_workflows = st.session_state.get('workflow_history', [])

    # Convert session workflows to user_workflows format
    for i, workflow in enumerate(session_workflows):
        if workflow not in user_workflows.values():  # Avoid duplicates
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            workflow_id = f"session_{i}_{timestamp}"
            user_workflows[workflow_id] = {
                "request": workflow.get("user_request", ""),
                "result": workflow,
                "timestamp": timestamp
            }
    
    if not user_workflows:
        st.info("No workflow history found. Start by using the Multi-Agent Chat!")
        return
    
    st.markdown(f"**Total Workflows:** {len(user_workflows)}")
    
    # Search and filter
    search_term = st.text_input("🔍 Search workflows...", placeholder="Search by request content")
    
    # Filter workflows
    filtered_workflows = user_workflows
    if search_term:
        filtered_workflows = {
            k: v for k, v in user_workflows.items()
            if search_term.lower() in v.get('request', '').lower()
        }
    
    # Display workflows
    for workflow_id, workflow_data in sorted(filtered_workflows.items(), reverse=True):
        with st.expander(f"📋 {workflow_data.get('timestamp', 'Unknown')} - {workflow_data.get('request', 'No request')[:50]}..."):
            result = workflow_data.get('result', {})
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**Request:**")
                st.write(workflow_data.get('request', 'No request'))
                
                st.markdown("**Task Type:**")
                st.info(result.get('task_type', 'Unknown'))
                st.markdown("**Status:**")
                st.info(result.get('workflow_status', 'Unknown'))
            
            with col2:
                st.markdown("**Final Output:**")
                st.write(result.get('final_output', 'No output')[:200] + "..." if len(str(result.get('final_output', ''))) > 200 else result.get('final_output', 'No output'))
                
                if st.button(f"🗑️ Delete", key=f"delete_{workflow_id}"):
                    users = load_users()
                    if st.session_state.username in users and "agent_workflows" in users[st.session_state.username]:
                        del users[st.session_state.username]["agent_workflows"][workflow_id]
                        save_users(users)
                        st.rerun()

def run_agent_status():
    st.title("⚙️ Agent Status & Configuration")
    
    if not st.session_state.multi_agent_system:
        st.warning("Multi-agent system not initialized. Please go to Multi-Agent Chat first.")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🤖 Active Agents")
        agents_info = {
            "Router Agent": {"emoji": "🎯", "role": "Task Classification", "model": "llama3-70b-8192"},
            "Research Agent": {"emoji": "🔍", "role": "Information Gathering", "model": "llama3-70b-8192"},
            "Planning Agent": {"emoji": "📋", "role": "Strategy & Planning", "model": "llama3-70b-8192"},
            "Review Agent": {"emoji": "✅", "role": "Quality Assurance", "model": "llama3-70b-8192"}
        }
        
        for agent_name, info in agents_info.items():
            st.markdown(f"""
            <div class="agent-step completed">
                <strong>{info['emoji']} {agent_name}</strong><br>
                <small>Role: {info['role']}</small><br>
                <small>Model: {info['model']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 System Statistics")
        if st.session_state.workflow_history:
            total_workflows = len(st.session_state.workflow_history)
            task_types = {}
            for workflow in st.session_state.workflow_history:
                task_type = workflow.get('task_type', 'unknown')
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            st.metric("Total Workflows", total_workflows)
            
            st.markdown("**Task Distribution:**")
            for task_type, count in task_types.items():
                st.write(f"- {task_type.title()}: {count}")
        else:
            st.info("No workflows processed yet")

# ==============================================
# ENHANCED MULTI-AGENT SYSTEM WITH ADVANCED HANDOFF
# ==============================================

class TaskHandoffState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    user_request: str
    task_type: str
    task_priority: str
    task_complexity: str
    research_data: str
    research_quality_score: float
    plan_content: str
    plan_validation: str
    review_feedback: str
    final_output: str
    current_agent: str
    workflow_status: str
    agent_outputs: Dict[str, str]
    handoff_logs: List[Dict[str, str]]
    validation_results: Dict[str, bool]
    iteration_count: int
    max_iterations: int

class AdvancedMultiAgentSystem(MultiAgentSystem):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.create_advanced_workflow()
    
    def enhanced_router_agent(self, state: TaskHandoffState) -> TaskHandoffState:
        """Enhanced router with priority and complexity analysis"""
        try:
            enhanced_prompt = f"""
            {ROUTER_SYSTEM_PROMPT}
            
            Additionally, analyze the request for:
            1. Priority Level (high/medium/low)
            2. Complexity Level (simple/moderate/complex)
            3. Estimated processing time
            
            Request: {state['user_request']}
            
            Respond in this format:
            Task Type: [planning/research/chat/complex]
            Priority: [high/medium/low]
            Complexity: [simple/moderate/complex]
            Reasoning: [brief explanation]
            """
            
            messages = [
                SystemMessage(content=enhanced_prompt),
                HumanMessage(content=state["user_request"])
            ]
            
            response = self.agents["router"].invoke(messages)
            response_text = response.content
            
            # Parse response
            task_type = "chat"
            priority = "medium"
            complexity = "moderate"
            
            for line in response_text.split('\n'):
                if line.startswith('Task Type:'):
                    task_type = line.split(':', 1)[1].strip().lower()
                elif line.startswith('Priority:'):
                    priority = line.split(':', 1)[1].strip().lower()
                elif line.startswith('Complexity:'):
                    complexity = line.split(':', 1)[1].strip().lower()
            
            state["task_type"] = task_type
            state["task_priority"] = priority
            state["task_complexity"] = complexity
            state["current_agent"] = "router"
            state["workflow_status"] = f"Task classified: {task_type} | Priority: {priority} | Complexity: {complexity}"
            state["agent_outputs"]["router"] = response_text
            
            # Log handoff
            state["handoff_logs"].append({
                "from": "user",
                "to": "router",
                "timestamp": datetime.now().isoformat(),
                "data_passed": f"User request: {state['user_request'][:50]}...",
                "status": "completed"
            })
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Router error: {str(e)}"
            return state
    
    def quality_research_agent(self, state: TaskHandoffState) -> TaskHandoffState:
        """Research agent with quality scoring"""
        try:
            if state["task_type"] in ["research", "complex"]:
                research_prompt = f"""
                {RESEARCH_SYSTEM_PROMPT}
                
                Task Details:
                - Priority: {state.get('task_priority', 'medium')}
                - Complexity: {state.get('task_complexity', 'moderate')}
                
                Please provide comprehensive research and end with a quality assessment:
                Quality Score: [0-100] - Rate the completeness and accuracy of your research
                
                Research Topic: {state['user_request']}
                """
                
                messages = [
                    SystemMessage(content=research_prompt),
                    HumanMessage(content=state["user_request"])
                ]
                
                response = self.agents["researcher"].invoke(messages)
                research_content = response.content
                
                # Extract quality score
                quality_score = 75.0  # default
                lines = research_content.split('\n')
                for line in lines:
                    if line.startswith('Quality Score:'):
                        try:
                            score_text = line.split(':', 1)[1].strip()
                            quality_score = float(score_text.split()[0])
                        except:
                            pass
                
                state["research_data"] = research_content
                state["research_quality_score"] = quality_score
                state["current_agent"] = "researcher"
                state["workflow_status"] = f"Research completed (Quality: {quality_score}/100)"
                state["agent_outputs"]["researcher"] = research_content
                
                # Log handoff
                state["handoff_logs"].append({
                    "from": "router",
                    "to": "researcher",
                    "timestamp": datetime.now().isoformat(),
                    "data_passed": f"Task type: {state['task_type']}, Priority: {state['task_priority']}",
                    "status": "completed",
                    "quality_score": quality_score
                })
                
                # Validation
                state["validation_results"]["research_quality"] = quality_score >= 60.0
                
            else:
                state["research_data"] = "No research required for this task type"
                state["research_quality_score"] = 0.0
                state["agent_outputs"]["researcher"] = "Skipped - not required"
                state["validation_results"]["research_quality"] = True
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Research error: {str(e)}"
            state["validation_results"]["research_quality"] = False
            return state
    
    def strategic_planning_agent(self, state: TaskHandoffState) -> TaskHandoffState:
        """Planning agent with validation checks"""
        try:
            if state["task_type"] in ["planning", "complex"]:
                planning_context = f"""
                User Request: {state['user_request']}
                Task Priority: {state.get('task_priority', 'medium')}
                Task Complexity: {state.get('task_complexity', 'moderate')}
                Research Quality Score: {state.get('research_quality_score', 0)}
                
                Research Data:
                {state.get('research_data', 'No research data available')}
                
                Create a detailed, actionable plan. Include:
                1. Executive Summary
                2. Step-by-step implementation
                3. Timeline and milestones
                4. Risk assessment
                5. Success metrics
                
                End with:
                Plan Validation: [PASS/FAIL] - Self-assessment of plan quality
                """
                
                messages = [
                    SystemMessage(content=PLANNING_SYSTEM_PROMPT),
                    HumanMessage(content=planning_context)
                ]
                
                response = self.agents["planner"].invoke(messages)
                plan_content = response.content
                
                # Extract validation
                plan_validation = "PASS"
                if "Plan Validation: FAIL" in plan_content:
                    plan_validation = "FAIL"
                
                state["plan_content"] = plan_content
                state["plan_validation"] = plan_validation
                state["current_agent"] = "planner"
                state["workflow_status"] = f"Planning completed (Validation: {plan_validation})"
                state["agent_outputs"]["planner"] = plan_content
                
                # Log handoff
                state["handoff_logs"].append({
                    "from": "researcher",
                    "to": "planner",
                    "timestamp": datetime.now().isoformat(),
                    "data_passed": f"Research data ({len(state.get('research_data', ''))} chars), Quality: {state.get('research_quality_score', 0)}",
                    "status": "completed",
                    "validation": plan_validation
                })
                
                # Validation
                state["validation_results"]["plan_quality"] = plan_validation == "PASS"
                
            else:
                state["plan_content"] = "No planning required for this task type"
                state["plan_validation"] = "SKIP"
                state["agent_outputs"]["planner"] = "Skipped - not required"
                state["validation_results"]["plan_quality"] = True
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Planning error: {str(e)}"
            state["validation_results"]["plan_quality"] = False
            return state
    
    def comprehensive_review_agent(self, state: TaskHandoffState) -> TaskHandoffState:
        """Review agent with comprehensive analysis"""
        try:
            review_context = f"""
            COMPREHENSIVE REVIEW REQUEST
            
            Original Request: {state['user_request']}
            Task Classification: {state.get('task_type', 'unknown')} (Priority: {state.get('task_priority', 'medium')}, Complexity: {state.get('task_complexity', 'moderate')})
            
            Agent Outputs to Review:
            1. Router Output: {state['agent_outputs'].get('router', 'None')[:200]}...
            2. Research Quality: {state.get('research_quality_score', 0)}/100
            3. Research Data: {state.get('research_data', 'None')[:300]}...
            4. Plan Validation: {state.get('plan_validation', 'None')}
            5. Plan Content: {state.get('plan_content', 'None')[:300]}...
            
            Validation Results:
            - Research Quality: {'✓' if state.get('validation_results', {}).get('research_quality') else '✗'}
            - Plan Quality: {'✓' if state.get('validation_results', {}).get('plan_quality') else '✗'}
            
            Handoff History:
            {json.dumps(state.get('handoff_logs', []), indent=2)}
            
            Please provide:
            1. Executive summary of the complete workflow
            2. Quality assessment of each agent's contribution
            3. Final synthesized response
            4. Recommendations for improvement (if any)
            
            Final Assessment: [EXCELLENT/GOOD/NEEDS_IMPROVEMENT]
            """
            
            messages = [
                SystemMessage(content=REVIEW_SYSTEM_PROMPT),
                HumanMessage(content=review_context)
            ]
            
            response = self.agents["reviewer"].invoke(messages)
            review_content = response.content
            
            state["final_output"] = review_content
            state["review_feedback"] = review_content
            state["current_agent"] = "reviewer"
            state["workflow_status"] = "Comprehensive review completed"
            state["agent_outputs"]["reviewer"] = review_content
            
            # Final handoff log
            state["handoff_logs"].append({
                "from": "planner",
                "to": "reviewer",
                "timestamp": datetime.now().isoformat(),
                "data_passed": "Complete workflow data for final review",
                "status": "completed",
                "final_assessment": "GOOD"  # Could be extracted from response
            })
            
            return state
        except Exception as e:
            state["workflow_status"] = f"Review error: {str(e)}"
            return state
    
    def should_iterate_workflow(self, state: TaskHandoffState) -> str:
        """Decide if workflow needs another iteration"""
        # Check if any validation failed and we haven't exceeded max iterations
        validation_results = state.get("validation_results", {})
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 2)
        
        if iteration_count >= max_iterations:
            return "finalize"
        
        # If research or planning failed validation, iterate
        if not validation_results.get("research_quality", True) or not validation_results.get("plan_quality", True):
            state["iteration_count"] = iteration_count + 1
            return "iterate"
        
        return "finalize"
    
    def iteration_handler(self, state: TaskHandoffState) -> TaskHandoffState:
        """Handle workflow iteration"""
        state["workflow_status"] = f"Iteration {state.get('iteration_count', 0) + 1} - Improving quality"
        
        # Add iteration log
        state["handoff_logs"].append({
            "from": "system",
            "to": "iteration_handler",
            "timestamp": datetime.now().isoformat(),
            "data_passed": "Quality improvement iteration",
            "status": "processing"
        })
        
        return state
    
    def create_advanced_workflow(self):
        """Create enhanced workflow with iterations and quality checks"""
        workflow = StateGraph(TaskHandoffState)
        
        # Add nodes
        workflow.add_node("enhanced_router", self.enhanced_router_agent)
        workflow.add_node("quality_research", self.quality_research_agent)
        workflow.add_node("strategic_planning", self.strategic_planning_agent)
        workflow.add_node("comprehensive_review", self.comprehensive_review_agent)
        workflow.add_node("iteration_handler", self.iteration_handler)
        
        # Add edges
        workflow.add_edge(START, "enhanced_router")
        
        # Conditional routing from router
        workflow.add_conditional_edges(
            "enhanced_router",
            lambda state: "quality_research" if state["task_type"] in ["research", "complex"] else "strategic_planning"
        )
        
        # From research to planning
        workflow.add_conditional_edges(
            "quality_research",
            lambda state: "strategic_planning" if state["task_type"] in ["planning", "complex"] else "comprehensive_review"
        )
        
        # From planning to review
        workflow.add_edge("strategic_planning", "comprehensive_review")
        
        # From review - check if iteration needed
        workflow.add_conditional_edges(
            "comprehensive_review",
            self.should_iterate_workflow,
            {
                "iterate": "iteration_handler",
                "finalize": END
            }
        )
        
        # From iteration handler back to research
        workflow.add_edge("iteration_handler", "quality_research")
        
        self.workflow = workflow.compile()
    
    def process_advanced_request(self, user_request: str) -> Dict[str, Any]:
        """Process request with advanced handoff system"""
        initial_state = TaskHandoffState(
            messages=[],
            user_request=user_request,
            task_type="",
            task_priority="medium",
            task_complexity="moderate",
            research_data="",
            research_quality_score=0.0,
            plan_content="",
            plan_validation="",
            review_feedback="",
            final_output="",
            current_agent="",
            workflow_status="Starting advanced workflow...",
            agent_outputs={},
            handoff_logs=[],
            validation_results={},
            iteration_count=0,
            max_iterations=2
        )
        
        try:
            result = self.workflow.invoke(initial_state)
            return result
        except Exception as e:
            return {
                "final_output": f"Advanced workflow error: {str(e)}",
                "workflow_status": "Error occurred",
                "agent_outputs": {"error": str(e)},
                "handoff_logs": [{"error": str(e)}]
            }

# ==============================================
# ENHANCED UI FUNCTIONS
# ==============================================

def run_advanced_multi_agent_chat():
    st.title("🚀 Advanced Multi-Agent System with Task Handoff")
    st.markdown("**Enhanced system with quality validation, iterations, and detailed handoff tracking**")
    
    # Toggle between basic and advanced mode
    mode = st.radio("System Mode:", ["🤖 Basic Multi-Agent", "🚀 Advanced Multi-Agent"], horizontal=True)
    
    if mode == "🚀 Advanced Multi-Agent":
        # Initialize advanced system
        if "advanced_multi_agent_system" not in st.session_state:
            st.session_state.advanced_multi_agent_system = None
        
        if not st.session_state.advanced_multi_agent_system:
            with st.spinner("Initializing advanced multi-agent system..."):
                st.session_state.advanced_multi_agent_system = AdvancedMultiAgentSystem(DEFAULT_API_KEY)
            st.success("Advanced multi-agent system initialized!")
        
        # Display workflow with handoff visualization
        if st.session_state.workflow_history:
            st.markdown("### 🔄 Task Handoff Visualization")
            
            # Get the latest workflow for visualization
            latest_workflow = st.session_state.workflow_history[-1]
            handoff_logs = latest_workflow.get("handoff_logs", [])
            
            if handoff_logs:
                st.markdown("#### Agent Communication Flow")
                
                for i, log in enumerate(handoff_logs):
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{log.get('from', 'Unknown').title()}**")
                    
                    with col2:
                        st.markdown(f"→ *{log.get('data_passed', 'No data')}* →")
                        if log.get('quality_score'):
                            st.markdown(f"Quality: {log['quality_score']}/100")
                    
                    with col3:
                        st.markdown(f"**{log.get('to', 'Unknown').title()}**")
                    
                    if i < len(handoff_logs) - 1:
                        st.markdown("---")
        
        # Input for advanced system
        st.markdown("### 💭 Advanced AI Request")
        with st.form(key='advanced_agent_form', clear_on_submit=True):
            user_input = st.text_area(
                "Request for Advanced Multi-Agent Processing:",
                placeholder="Examples:\n- Create a comprehensive business plan for a sustainable energy startup\n- Research AI ethics and develop implementation guidelines\n- Analyze climate change impacts and propose mitigation strategies",
                height=120
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("🚀 Process with Advanced Agents", type="primary")
            with col2:
                show_details = st.checkbox("Show Handoff Details")
        
        if submitted and user_input.strip():
            with st.spinner("🔄 Advanced multi-agent system processing..."):
                try:
                    result = st.session_state.advanced_multi_agent_system.process_advanced_request(user_input)
                    st.session_state.workflow_history.append(result)
                    save_workflow_to_user(result)
                    
                    # Display results
                    st.success("✅ Advanced processing completed!")
                    
                    # Show final output
                    st.markdown("### 🎯 Final Output")
                    st.markdown(f'<div class="final-output">{result.get("final_output", "No output generated")}</div>', unsafe_allow_html=True)
                    
                    if show_details:
                        # Show handoff details
                        st.markdown("### 🔍 Detailed Handoff Analysis")
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown("**Task Analysis:**")
                            st.info(f"Type: {result.get('task_type', 'Unknown')}")
                            st.info(f"Priority: {result.get('task_priority', 'Unknown')}")
                            st.info(f"Complexity: {result.get('task_complexity', 'Unknown')}")
                            
                            st.markdown("**Quality Metrics:**")
                            research_score = result.get('research_quality_score', 0)
                            st.metric("Research Quality", f"{research_score}/100")
                            
                            validation_results = result.get('validation_results', {})
                            st.write("**Validation Results:**")
                            for key, value in validation_results.items():
                                st.write(f"- {key}: {'✅ Pass' if value else '❌ Fail'}")
                        
                        with col2:
                            st.markdown("**Handoff Timeline:**")
                            handoff_logs = result.get('handoff_logs', [])
                            
                            for log in handoff_logs:
                                timestamp = log.get('timestamp', 'Unknown')
                                from_agent = log.get('from', 'Unknown')
                                to_agent = log.get('to', 'Unknown')
                                status = log.get('status', 'Unknown')
                                
                                status_emoji = "✅" if status == "completed" else "🔄"
                                
                                st.markdown(f"""
                                <div class="agent-step {'completed' if status == 'completed' else 'active'}">
                                    {status_emoji} <strong>{from_agent.title()}</strong> → <strong>{to_agent.title()}</strong><br>
                                    <small>{timestamp}</small>
                                </div>
                                """, unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"Error in advanced processing: {str(e)}")
    
    else:
        # Run basic multi-agent chat
        run_multi_agent_chat()

# ==============================================
# MAIN APPLICATION
# ==============================================
def main():
    sidebar_controls()
    
    if st.session_state.app_mode == "Multi-Agent Chat":
        run_advanced_multi_agent_chat()
    elif st.session_state.app_mode == "Workflow History":
        run_workflow_history()
    elif st.session_state.app_mode == "Agent Status":
        run_agent_status()

if __name__ == "__main__":
    main()