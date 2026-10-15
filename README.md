# Chat with your SQL Database

A LangChain SQL agent on Groq, wrapped in Streamlit. Ask a question in English;
the agent inspects the schema, writes SQL, runs it, and explains the result.

## Setup

```bash
pip install -r requirements.txt
python load_data.py          # builds data.db
streamlit run app.py
```

Paste your Groq API key (free from console.groq.com) into the sidebar.

## The data

`data.db` replaces the old 6-row `student.db` with real datasets — the same
ones you find on Kaggle:

| Table | Rows | What's in it |
|---|---|---|
| `titanic` | 891 | Passenger survival, class, fare, age, embarkation port |
| `diamonds` | 53,940 | Price, carat, cut, colour, clarity |
| `penguins` | 344 | Palmer Penguins: species, island, body measurements |
| `tips` | 244 | Restaurant bills, tips, party size, day |
| `ports` | 3 | Titanic embarkation ports with country and coordinates |

`ports.town` joins to `titanic.embark_town`, so the agent has a real JOIN to
perform rather than only single-table aggregation.

## Using your own Kaggle dataset

```bash
python load_data.py --csv ~/Downloads/netflix_titles.csv --table netflix
```

Column names are lowercased and spaces become underscores. Add `--append` to
add rows to an existing table instead of replacing it.

## Bugs fixed from the original app.py

| Original | Problem |
|---|---|
| `os.environ['GROQ_API_KEY'] = api_key` then `ChatGroq(...)` | Ran before the key was checked, so the app crashed on first load with an empty key. Now guarded by `st.stop()`. |
| `st.info("Please enter...")` | Displayed a message but execution continued anyway. |
| `agent.run(query, callbacks=[cb])` | `.run()` is removed in current LangChain. Now `agent.invoke({"input": q}, {"callbacks": [cb]})`. |
| `if 'messages' not in st.session_state or st.sidebar.button(...)` | Short-circuit `or` meant the Clear button never rendered on first load. Now created separately. |
| `st.text_input("Enter your Groq API Key")` | Key was visible in plain text. Now `type="password"`. |
| No error handling around the agent | Any SQL or API error crashed the whole app. Now caught and shown in the chat. |

## Safety note

The SQLite connection opens with `mode=ro`, so the agent physically cannot
write to the database — verified: a `DROP TABLE` returns
"attempt to write a readonly database". Do the equivalent for MySQL by
connecting with a read-only user before pointing this at anything real.

## Try these

- What was the survival rate by passenger class?
- Join titanic to ports: average fare and survival rate by country.
- Which penguin species has the longest average flipper?
- Average diamond price by cut, with counts.
