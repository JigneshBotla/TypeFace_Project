import sqlalchemy, os
from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL not set in .env")

engine = sqlalchemy.create_engine(db_url)
dbname = engine.url.database  # extracts the database name from URL

print("Using database:", dbname)

with engine.begin() as conn:
    # 1) check column existence
    column_exists = conn.execute(
        sqlalchemy.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'transactions' AND column_name = 'category_id'"
        ),
        {"schema": dbname}
    ).scalar() > 0

    if column_exists:
        print("Column 'transactions.category_id' already exists.")
    else:
        print("Adding column 'category_id' to transactions...")
        conn.execute(sqlalchemy.text("ALTER TABLE transactions ADD COLUMN category_id INT NULL;"))
        print("Column added.")

    # 2) check index existence
    index_exists = conn.execute(
        sqlalchemy.text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = :schema AND table_name = 'transactions' AND index_name = 'idx_transactions_category_id'"
        ),
        {"schema": dbname}
    ).scalar() > 0

    if index_exists:
        print("Index 'idx_transactions_category_id' already exists.")
    else:
        print("Creating index 'idx_transactions_category_id'...")
        conn.execute(sqlalchemy.text("CREATE INDEX idx_transactions_category_id ON transactions (category_id);"))
        print("Index created.")

    # 3) optionally add foreign key constraint if categories table exists and FK missing
    categories_exist = conn.execute(
        sqlalchemy.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = :schema AND table_name = 'categories'"
        ),
        {"schema": dbname}
    ).scalar() > 0

    if not categories_exist:
        print("Table 'categories' does not exist in DB; skipping FK creation.")
    else:
        fk_exists = conn.execute(
            sqlalchemy.text(
                "SELECT COUNT(*) FROM information_schema.key_column_usage "
                "WHERE table_schema = :schema AND table_name = 'transactions' "
                "AND column_name = 'category_id' AND referenced_table_name = 'categories'"
            ),
            {"schema": dbname}
        ).scalar() > 0

        if fk_exists:
            print("Foreign key referencing categories already exists on transactions.category_id.")
        else:
            print("Adding foreign key constraint fk_transactions_category -> categories(id) (ON DELETE SET NULL)...")
            conn.execute(sqlalchemy.text(
                "ALTER TABLE transactions ADD CONSTRAINT fk_transactions_category FOREIGN KEY (category_id) "
                "REFERENCES categories(id) ON DELETE SET NULL"
            ))
            print("Foreign key added.")

print("Done.")
