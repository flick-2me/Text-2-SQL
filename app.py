"""
Chat with a SQL database using a LangChain SQL agent on Groq.

    python load_data.py      # build data.db first
    streamlit run app.py
"""

import sqlite3
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine

from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq

LOCAL_DB, MYSQL = "USE_LOCALDB", "USE_MYSQL"
DB_FILE = Path(__file__).parent / "data.db"

st.set_page_config(page_title="Chat with SQL DB", page_icon="🗄️", layout="wide")
st.title("🗄️ Chat with your SQL Database")
st.caption("LangChain SQL agent on Groq. Ask in English, it writes and runs the SQL.")


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Connection")

    opt = ["SQLite — data.db (bundled)", "MySQL"]
    choice = st.radio("Database", opt)
    db_uri = LOCAL_DB if opt.index(choice) == 0 else MYSQL

    mysql_host = mysql_user = mysql_password = mysql_db = None
    if db_uri == MYSQL:
        mysql_host = st.text_input("Host", "localhost")
        mysql_user = st.text_input("User")
        mysql_password = st.text_input("Password", type="password")
        mysql_db = st.text_input("Database")

    st.divider()
    api_key = st.text_input("Groq API key", type="password",
                            help="Free key from console.groq.com")
    model_name = st.text_input("Model", "openai/gpt-oss-20b")
    top_k = st.slider("Max rows returned per query", 5, 100, 20)

    st.divider()
    clear = st.button("Clear chat history", use_container_width=True)


# ----------------------------------------------------------------------
# Guards — stop before building anything that needs credentials
# ----------------------------------------------------------------------
if not api_key:
    st.info("Enter your Groq API key in the sidebar to begin.")
    st.stop()

if db_uri == LOCAL_DB and not DB_FILE.exists():
    st.error(f"`{DB_FILE.name}` not found. Run `python load_data.py` first.")
    st.stop()

if db_uri == MYSQL and not all([mysql_host, mysql_user, mysql_password, mysql_db]):
    st.warning("Fill in all MySQL connection fields.")
    st.stop()


# ----------------------------------------------------------------------
# Database + agent
# ----------------------------------------------------------------------
@st.cache_resource(ttl="2h")
def configure_db(db_uri, host=None, user=None, password=None, database=None):
    if db_uri == LOCAL_DB:
        # Read-only connection so the agent can never DROP or UPDATE anything.
        creator = lambda: sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        engine = create_engine("sqlite:///", creator=creator)
    else:
        engine = create_engine(
            f"mysql+mysqlconnector://{user}:{password}@{host}/{database}")
    # sample_rows gives the agent example values, which cuts down on
    # queries that filter for strings that don't exist.
    return SQLDatabase(engine, sample_rows_in_table_info=3)


@st.cache_resource(ttl="2h")
def build_agent(_db, api_key, model_name, top_k):
    llm = ChatGroq(model=model_name, api_key=api_key, temperature=0)
    toolkit = SQLDatabaseToolkit(db=_db, llm=llm)
    return create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type="tool-calling",
        verbose=True,
        handle_parsing_errors=True,
        top_k=top_k,
        max_iterations=12,
        )


try:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
    agent = build_agent(db, api_key, model_name, top_k)
except Exception as e:
    st.error(f"Connection failed: {e}")
    st.stop()

with st.expander(" Schema the agent can see :"):
    for table in db.get_usable_table_names():
        cols = [c["name"] for c in db._inspector.get_columns(table)]
        st.markdown(f"**{table}** — {', '.join(cols)}")


# ----------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------
WELCOME = {"role": "assistant",
           "content": "Ask me anything about the data. I'll write the SQL and run it."}

if "messages" not in st.session_state or clear:
    st.session_state.messages = [WELCOME]

EXAMPLES = [
    "What was the survival rate by passenger class on the Titanic?",
    "Join titanic to ports — average fare and survival rate by country of embarkation.",
    "Which penguin species has the longest average flipper?",
    "What is the average tip percentage by day of the week?",
    "What is the average diamond price for each cut, and how many of each?",
]

with st.expander("💡 Example questions"):
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES):
        if cols[i % 2].button(q, key=f"ex{i}", use_container_width=True):
            st.session_state.pending = q
            st.rerun()

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

query = st.chat_input("Ask a question about the data...")
if "pending" in st.session_state:
    query = st.session_state.pop("pending")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    st.chat_message("user").write(query)

    with st.chat_message("assistant"):
        cb = StreamlitCallbackHandler(
            st.container(), expand_new_thoughts=True, collapse_completed_thoughts=True
        )
        try:
            result = agent.invoke({"input": query}, {"callbacks": [cb]})
            answer = result.get("output", "No output returned.")
        except Exception as e:
            answer = f"⚠️ {type(e).__name__}: {e}"

        st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
