"""
Build data.db for the SQL chat agent.
    python load_data.py
"""

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent / "data.db"

# Two simple, classic datasets mirroring well-known Kaggle sets.
BUILTIN = {
    "titanic": "Passenger survival records from the Titanic (891 rows).",
    "tips": "Restaurant bills, tips, party size and day of week (244 rows).",
}

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """SQLite has no category or bool type -- convert so columns stay queryable."""
    df = df.copy()
    for col in df.columns:
        if str(df[col].dtype) == "category":
            df[col] = df[col].astype("object")
        elif df[col].dtype == bool:
            df[col] = df[col].astype(int)
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df

def load_builtin(conn):
    import seaborn as sns

    for name, desc in BUILTIN.items():
        try:
            df = clean(sns.load_dataset(name))
            df.to_sql(name, conn, if_exists="replace", index=False)
            print(f"  {name:<10} {len(df):>6,} rows x {len(df.columns):>2} cols   {desc}")
        except Exception as e:
            print(f"  {name:<10} SKIPPED ({e})")

def summarise(conn):
    tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )["name"].tolist()
    print(f"\nDatabase: {DB_PATH}")
    print(f"Tables:   {', '.join(tables)}")
    for t in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info('{t}')")]
        print(f"\n  {t}: {', '.join(cols)}")

def main():
    conn = sqlite3.connect(DB_PATH)
    print("Loading...")
    try:
        load_builtin(conn)
        conn.commit()
        summarise(conn)
    finally:
        conn.close()
    print("\nDone. Now run:  streamlit run app.py")

if __name__ == "__main__":
    main()