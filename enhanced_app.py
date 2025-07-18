import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
import datetime
import os
from enhanced_query_agent import QueryAgent
from utils.utils_auth import check_user_role

# --- CONFIG ---
DATA_DICT_PATH = 'data/data_dictionary.xlsx'
ROLE_ACCESS_PATH = 'data/role_access.xlsx'

# --- Database connection utility ---
def get_db_connection():
    # Use fixed MySQL credentials
    mysql_params = {
        "host": "localhost",
        "user": "root",
        "password": "password",
        "database": "bankexchange"
    }
    if not st.session_state.get('mysql_connected', False):
        raise Exception("Not connected to MySQL. Please login to establish connection.")
    return mysql.connector.connect(
        host=mysql_params["host"],
        user=mysql_params["user"],
        password=mysql_params["password"],
        database=mysql_params["database"]
    )

# --- UTILS ---
def load_data_dictionary():
    if st.session_state.get('mysql_connected', False):
        try:
            conn = get_db_connection()
            df = None
            try:
                df = pd.read_sql('SELECT * FROM data_dictionary', conn)
            except Exception:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                tables = [table_name for (table_name,) in cursor.fetchall()]
                rows = []
                for table in tables:
                    cursor.execute(f"SHOW COLUMNS FROM {table}")
                    for (col_name, col_type, *_) in cursor.fetchall():
                        rows.append({'Table': table, 'Column': col_name, 'Type': col_type})
                df = pd.DataFrame(rows)
            conn.close()
            return df
        except Exception as e:
            st.warning(f"Could not load MySQL schema: {e}")
            return pd.DataFrame()
    elif os.path.exists(DATA_DICT_PATH):
        return pd.read_excel(DATA_DICT_PATH)
    return pd.DataFrame()

def load_role_access():
    if st.session_state.get('mysql_connected', False):
        try:
            conn = get_db_connection()
            df = pd.read_sql('SELECT * FROM role_access', conn)
            df.set_index(df.columns[0], inplace=True)
            conn.close()
            return df
        except Exception as e:
            st.warning(f"Could not load MySQL role access: {e}")
            return pd.DataFrame()
    elif os.path.exists(ROLE_ACCESS_PATH):
        return pd.read_excel(ROLE_ACCESS_PATH, index_col=0)
    return pd.DataFrame()

def get_allowed_tables(role, role_access):
    if role_access is not None and role in role_access.index:
        allowed = role_access.loc[role]
        return [table for table, access in allowed.items() if str(access).strip()]
    return []

def get_allowed_columns(role, table, role_access, table_cols):
    if role_access is not None and role in role_access.index:
        allowed = role_access.loc[role]
        val = allowed.get(table, '')
        if isinstance(val, str):
            if val.strip().upper() == 'ALL':
                return table_cols.get(table, [])
            elif val.strip():
                return [c.strip() for c in val.split(',') if c.strip()]
    return []

def get_table_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    tables = []
    cursor.execute("SHOW TABLES")
    for (table_name,) in cursor.fetchall():
        tables.append(table_name)
    conn.close()
    return tables

def get_table_columns():
    conn = get_db_connection()
    cursor = conn.cursor()
    tables = get_table_list()
    table_cols = {}
    for table in tables:
        columns = []
        cursor.execute(f'SHOW COLUMNS FROM {table}')
        for (name, *_) in cursor.fetchall():
            columns.append(name)
        table_cols[table] = columns
    conn.close()
    return table_cols

def execute_sql_query(sql_query):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(sql_query, conn)
    except Exception as e:
        conn.close()
        raise e
    conn.close()
    return df

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    if not os.path.exists(ROLE_ACCESS_PATH):
        return None
    try:
        roles_df = pd.read_excel(ROLE_ACCESS_PATH, index_col=0)
        valid_roles = [r.strip().lower() for r in roles_df.index.tolist()]
    except Exception as e:
        print(f"Error loading role access file: {e}")
        return None
    username_clean = username.strip().lower()
    if username_clean in valid_roles and password == f"{username_clean}123":
        return username_clean.title()
    return None

# --- SESSION STATE ---
def init_session_state():
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,
        "history": [],
        "db_connected": False,
        "system_ready": False,
        "data_dict": None,
        "role_access": None,
        "table_cols": None,
        "query_agent": None,
        "metrics": {},
        "current_query": "",
        "mysql_connected": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- CSS ---
st.markdown("""
<style>
    /* General Body and App Styling */
    body, .stApp {
        background-color: #1a1a1a; /* ChatGPT dark background */
        color: #ececec;
        font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        font-size: 18px;
        letter-spacing: 0.01em;
    }

    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 800px;
        margin: 0 auto;
    }

    /* --- CHAT STYLES --- */
    .chat-message {
        display: flex;
        align-items: flex-start;
        padding: 1.25rem 2rem;
        border-radius: 1.25rem;
        margin-bottom: 1.5rem;
        width: 90%;
        max-width: 700px;
        font-size: 1.1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .chat-message.user-message {
        background-color: #23272f;
        margin-left: auto;
        margin-right: 0;
    }

    .chat-message.assistant-message {
        background-color: #353740;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-right: auto;
        margin-left: 0;
    }

    .chat-message .avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        margin-right: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: white;
        font-size: 1.3rem;
        background: #19c37d;
    }

    .chat-message.user-message .avatar {
        background-color: #19c37d;
    }

    .chat-message.assistant-message .avatar {
        background-color: #9b59b6;
    }
    
    .chat-message .message-content {
        flex: 1;
        font-size: 1.1rem;
        line-height: 1.7;
        word-break: break-word;
    }

    /* --- SQL / DATAFRAME STYLES --- */
    .sql-code {
        background-color: #23272f;
        color: #f8f8f2;
        border: 1px solid #555;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
        font-size: 1rem;
    }

    .stDataFrame {
        border: 1px solid #555;
        border-radius: 8px;
        background: #23272f;
    }
    .stDataFrame, .stTable {
        background: #23272f;
    }

    /* --- SIDEBAR STYLES --- */
    .stSidebar {
        background-color: #18181c;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stSidebar .stButton>button {
        background-color: transparent;
        border: 1px solid #555;
        color: #ececec;
        margin-bottom: 0.5rem;
    }
    .stSidebar .stButton>button:hover {
        background-color: #353740;
        border-color: #777;
    }
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar p, .stSidebar li {
        color: #ececec;
        font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    }

    /* --- CHAT INPUT STYLES --- */
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 1.5rem 0.5rem 1.5rem 0.5rem;
        background: linear-gradient(to top, #1a1a1a 60%, transparent);
        display: flex;
        justify-content: center;
        z-index: 100;
    }
    .chat-input-form {
        width: 70%;
        max-width: 700px;
    }
    .stTextInput>div>div>input {
        background-color: #23272f;
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 1rem;
        padding: 1rem 1.5rem;
        font-size: 1.1rem;
        font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    }
    .stButton[kind="form_submit"]>button {
        background-color: #19c37d;
        color: white;
        border: none;
        font-size: 1.1rem;
        border-radius: 1rem;
        padding: 0.7rem 2rem;
    }
    .stButton[kind="form_submit"]>button:hover {
        background-color: #13a06f;
    }
    
    /* --- HIDE USELESS ELEMENTS --- */
    .main-header, footer {
        display: none;
    }
    
    /* Add new styles for the toggle button */
    .sidebar-toggle {
        position: fixed;
        top: 0.5rem;
        right: 1rem;
        z-index: 1000;
        padding: 0.5rem;
        background: #2e2d88;
        border-radius: 0.5rem;
        color: white;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    
    /* Adjust main content when sidebar is hidden */
    .main.sidebar-hidden .block-container {
        padding-left: 1rem !important;
        max-width: 100% !important;
    }
    
    /* Hide default Streamlit menu button */
    #MainMenu {visibility: hidden;}
    
    /* Adjust sidebar width */
    .css-1d391kg {
        width: 20rem;
    }
</style>
""", unsafe_allow_html=True)

# --- APP START ---
st.set_page_config(
    page_title="DWH Chatbot",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💻"
)

# Add this right after the CSS block
st.markdown("""
<style>
    /* Existing CSS remains unchanged */
    
    /* Add new styles for the toggle button */
    .sidebar-toggle {
        position: fixed;
        top: 0.5rem;
        right: 1rem;
        z-index: 1000;
        padding: 0.5rem;
        background: #2e2d88;
        border-radius: 0.5rem;
        color: white;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    
    /* Adjust main content when sidebar is hidden */
    .main.sidebar-hidden .block-container {
        padding-left: 1rem !important;
        max-width: 100% !important;
    }
    
    /* Hide default Streamlit menu button */
    #MainMenu {visibility: hidden;}
    
    /* Adjust sidebar width */
    .css-1d391kg {
        width: 20rem;
    }
</style>
""", unsafe_allow_html=True)

# Add this right after st.set_page_config
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'

# Add toggle button
toggle_btn = """
<div class='sidebar-toggle' onclick='
    const icon = document.getElementById("toggle-icon");
    const sidebar = document.querySelector("section.css-1d391kg");
    const main = document.querySelector("section.main");
    if (sidebar.style.display === "none") {
        sidebar.style.display = "block";
        icon.innerHTML = "◀";
        main.classList.remove("sidebar-hidden");
    } else {
        sidebar.style.display = "none";
        icon.innerHTML = "▶";
        main.classList.add("sidebar-hidden");
    }
'>
    <span id="toggle-icon">◀</span>
</div>
"""
st.markdown(toggle_btn, unsafe_allow_html=True)

init_session_state()

# --- SYSTEM INIT ---
def initialize_system_state():
    st.session_state.data_dict = load_data_dictionary()
    st.session_state.role_access = load_role_access()
    st.session_state.table_cols = get_table_columns()
    agent_db = {
        "host": "localhost",
        "user": "root",
        "password": "password",
        "database": "bankexchange"
    }
    st.session_state.query_agent = QueryAgent('MySQL', agent_db, st.session_state.data_dict, st.session_state.role_access)
    st.session_state.system_ready = True

if 'system_ready' not in st.session_state:
    st.session_state.system_ready = False

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("ASK DWH")
    st.subheader("Login to continue")
    with st.form("login_form", clear_on_submit=True):
        st.subheader("🔐 Login")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login")
        if submitted:
            role = authenticate(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                # --- Establish MySQL connection here ---
                try:
                    conn = mysql.connector.connect(
                        host="localhost",
                        user="root",
                        password="password",
                        database="bankexchange"
                    )
                    conn.close()
                    st.session_state['mysql_connected'] = True
                    # --- Initialize QueryAgent and system state here ---
                    initialize_system_state()
                except Exception as e:
                    st.session_state['mysql_connected'] = False
                    st.error(f"MySQL connection failed: {e}")
                    st.stop()
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials!")
    st.info("Demo: Use roles as username (teller, manager, auditor, it, customer service) and password as role123 (e.g., teller123)")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"👋 {st.session_state.username.title()}")
    st.write(f"**Role:** {st.session_state.role}")
    st.divider()

    # --- MySQL connection status only ---
    if st.session_state.get('mysql_connected', False):
        st.info("MySQL Status: Connected")
    else:
        st.warning("MySQL Status: Not Connected")

    # --- Remove metrics and allowed tables sections ---
    # --- Sample Queries ---
    st.subheader("💡 Sample Queries")
    
    # Organize queries by category
    transaction_queries = {
        "Sample Queries": [
            "Show me all transactions",
            "Show me all customers",
            "Show me transactions where amount is greater than $1000",
            "Show me all accounts"
        ]
    }

    # Display queries in expandable sections
    for category, queries in {**transaction_queries}.items():
        with st.expander(f"📋 {category}", expanded=False):
            for query in queries:
                if st.button(query, key=f"sample_{query}", use_container_width=True):
                    st.session_state.current_query = query
                    st.rerun()
    
    st.divider()

    st.subheader("🕑 History")
    for msg in st.session_state.history[-5:]:
        st.write(f"{msg['role'].title()}: {msg['content'][:40]}{'...' if len(msg['content'])>40 else ''}")

    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
        
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- THEME TOGGLE ---
    if 'theme_mode' not in st.session_state:
        st.session_state['theme_mode'] = 'dark'

    st.markdown('---')
    theme_label = '🌙 Dark Mode' if st.session_state['theme_mode'] == 'dark' else '☀️ Light Mode'
    if st.button(f"Switch to {'Light' if st.session_state['theme_mode']=='dark' else 'Dark'} Mode", key='theme_toggle'):
        st.session_state['theme_mode'] = 'light' if st.session_state['theme_mode'] == 'dark' else 'dark'
        st.rerun()
    st.markdown(f"**Current Theme:** {theme_label}")

# --- THEME CSS ---
if st.session_state['theme_mode'] == 'dark':
    st.markdown("""
    <style>
    body, .stApp { background-color: #1a1a1a; color: #ececec; font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; font-size: 18px; letter-spacing: 0.01em; }
    .main .block-container { max-width: 800px; margin: 0 auto; padding-bottom: 140px !important; }
    .chat-message { background: #23272f; color: #ececec; }
    .chat-message.user-message { background-color: #23272f; }
    .chat-message.assistant-message { background-color: #353740; }
    .chat-message .avatar { background: #19c37d; color: #fff; }
    .chat-message.assistant-message .avatar { background: #9b59b6; }
    .sql-code, .stDataFrame, .stTable { background: #23272f; color: #f8f8f2; }
    .stSidebar { background-color: #18181c; color: #ececec; }
    .stTextInput>div>div>input { background-color: #23272f; color: #fff; border: 1px solid rgba(255,255,255,0.12); }
    .stButton[kind="form_submit"]>button { background-color: #19c37d; color: white; }
    .stButton[kind="form_submit"]>button:hover { background-color: #13a06f; }
    #fixed-chat-input { position: fixed; left: 0; bottom: 0; width: 100vw; z-index: 1000; background: linear-gradient(to top, #1a1a1a 60%, transparent); padding: 1.5rem 0.5rem 1.5rem 0.5rem; display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    body, .stApp { background-color: #f3f4f6; color: #23272f; font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; font-size: 18px; letter-spacing: 0.01em; }
    .main .block-container { max-width: 800px; margin: 0 auto; padding-bottom: 140px !important; }
    .chat-message { background: #f6f7fa; color: #23272f; }
    .chat-message.user-message { background-color: #e6f7ee; }
    .chat-message.assistant-message { background-color: #f6f7fa; }
    .chat-message .avatar { background: #19c37d; color: #fff; }
    .chat-message.assistant-message .avatar { background: #9b59b6; }
    .sql-code, .stDataFrame, .stTable { background: #f3f4f6; color: #23272f; }
    .stSidebar, .stSidebar * { background-color: #e5e7eb; color: #23272f !important; }
    .stTextInput>div>div>input { background-color: #fff; color: #23272f; border: 1px solid #ccc; }
    .stButton[kind="form_submit"]>button { background-color: #19c37d; color: white; }
    .stButton[kind="form_submit"]>button:hover { background-color: #13a06f; }
    #fixed-chat-input { position: fixed; left: 0; bottom: 0; width: 100vw; z-index: 1000; background: linear-gradient(to top, #f3f4f6 60%, transparent); padding: 1.5rem 0.5rem 1.5rem 0.5rem; display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

# --- MAIN CHAT INTERFACE ---
if st.session_state.get('mysql_connected', False) and st.session_state.get('query_agent', None) is not None:
    st.title("How can DWH team help you today?")

# --- CHAT HISTORY ---
for i, message in enumerate(st.session_state.history):
    is_user = message["role"] == "user"
    avatar_content = st.session_state.username[0].upper() if is_user else "🤖"
    
    if is_user:
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="avatar">{avatar_content}</div>
            <div class="message-content">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
    else: # Assistant
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div class="avatar">{avatar_content}</div>
            <div class="message-content">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display SQL query and results in expanders, ChatGPT-style
        if "results" in message and message["results"] is not None and not message["results"].empty:
            with st.expander("📊 View Results", expanded=True):
                df = message["results"]
                st.dataframe(df, use_container_width=True)
                
                # --- Download and Charting options ---
                col1, col2 = st.columns(2)
                with col1:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV", csv, f"query_results_{i}.csv", "text/csv", key=f"csv_{i}")
                with col2:
                    if len(df.columns) > 1:
                        try:
                            # Simple chart builder
                            st.write("📈 **Create a quick chart**")
                            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                            all_cols = df.columns.tolist()
                            if len(numeric_cols) >= 1:
                                x_axis = st.selectbox("X-Axis", all_cols, key=f"x_axis_{i}")
                                y_axis = st.selectbox("Y-Axis", numeric_cols, key=f"y_axis_{i}")
                                chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Pie"], key=f"chart_type_{i}")
                                if chart_type == "Bar":
                                    fig = px.bar(df, x=x_axis, y=y_axis)
                                    st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "Line":
                                    fig = px.line(df, x=x_axis, y=y_axis)
                                    st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "Pie":
                                    pie_labels = st.selectbox("Pie Labels (Category)", all_cols, key=f"pie_labels_{i}")
                                    pie_values = st.selectbox("Pie Values (Numeric)", numeric_cols, key=f"pie_values_{i}")
                                    fig = px.pie(df, names=pie_labels, values=pie_values)
                                    st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Could not generate chart: {e}")


# --- FIXED CHAT INPUT FORM ---
st.markdown('<div id="fixed-chat-input" class="chat-input-container">', unsafe_allow_html=True)
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([8, 1])
    with col1:
        query_input = st.text_input(
            "chat-input", # internal key
            value=st.session_state.get("current_query", ""), 
            placeholder="Ask me anything about your data...",
            label_visibility="collapsed"
        )
    with col2:
        submitted = st.form_submit_button("➤")

    # Prevent queries if MySQL is selected but not connected
    allow_query = True
    if not st.session_state.get('mysql_connected', False):
        allow_query = False
        st.warning("Please connect to MySQL first using the sidebar.")

    if submitted and query_input and allow_query:
        st.session_state.current_query = "" # Clear sample query
        st.session_state.history.append({"role": "user", "content": query_input})
        
        with st.spinner("Processing..."):
            try:
                allowed_tables = get_allowed_tables(st.session_state.role, st.session_state.role_access)
                allowed_columns = {t: get_allowed_columns(st.session_state.role, t, st.session_state.role_access, st.session_state.table_cols) for t in allowed_tables}

                # Detect if the query refers to previous result
                contextual_phrases = [
                    'from the above', 'from previous', 'previous result', 'above result',
                    'based on the above', 'based on previous', 'using the last result','based on this', 'using previous result'
                ]
                lower_query = query_input.lower()
                is_contextual = any(phrase in lower_query for phrase in contextual_phrases)
                previous_query = None
                previous_result_columns = None
                if is_contextual:
                    # Find last assistant message with sql_query and results
                    for msg in reversed(st.session_state.history):
                        if msg.get("role") == "assistant" and msg.get("sql_query"):
                            previous_query = msg["sql_query"]
                            if msg.get("results") is not None and not msg["results"].empty:
                                previous_result_columns = list(msg["results"].columns)
                            break
                
                sql_query, response, df = st.session_state.query_agent.answer_query(
                    query_input, allowed_tables, allowed_columns,
                    previous_query=previous_query, previous_result_columns=previous_result_columns
                )
                
                st.session_state.history.append({
                    "role": "assistant",
                    "content": response,
                    "sql_query": sql_query,
                    "results": df
                })
                # --- LOG USER PROMPT AND GENERATED SQL TO FILE ---
                try:
                    log_dir = "logs"
                    os.makedirs(log_dir, exist_ok=True)
                    username = st.session_state.username
                    log_path = os.path.join(log_dir, f"{username}.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"USER PROMPT: {query_input}\n")
                        f.write(f"GENERATED SQL: {sql_query}\n\n")
                except Exception as log_exc:
                    print(f"Logging error: {log_exc}")
            except Exception as e:
                st.session_state.history.append({"role": "assistant", "content": f"An error occurred: {e}"})
        
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("**RAG SQL Chatbot** -Your own DWH assistant") 