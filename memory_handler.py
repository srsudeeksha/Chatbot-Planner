import json
import os
from datetime import datetime

MEMORY_FILE = "chat_sessions.json"

def load_all_chats():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_all_chats(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

def get_session_titles():
    data = load_all_chats()
    return list(data.keys())

def load_session(session_name):
    data = load_all_chats()
    return data.get(session_name, [])

def save_session(session_name, messages):
    data = load_all_chats()
    data[session_name] = messages
    save_all_chats(data)

def create_new_session():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_name = f"Chat {timestamp}"
    return session_name
