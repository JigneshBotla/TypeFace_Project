# check_receipts.py
import os, sqlalchemy
from dotenv import load_dotenv

# make sure this script is run from the backend directory where .env lives
load_dotenv()  # loads .env in current working directory

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL not found in .env (run this from backend folder)")

engine = sqlalchemy.create_engine(db_url)
with engine.connect() as conn:
    print("Tables in DB:")
    for r in conn.execute(sqlalchemy.text("SHOW TABLES")):
        print(" -", r[0])

    print("\nRecent receipts (id, user_id, file_path, uploaded_at):")
    rs = conn.execute(sqlalchemy.text(
        "SELECT id, user_id, file_path, uploaded_at FROM receipts ORDER BY id DESC LIMIT 20"
    ))
    for row in rs:
        print(row)
