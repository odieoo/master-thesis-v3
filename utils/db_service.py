# # Installing packages

# import json
# import os
# import sqlite3
# import json

# # Installing sections
# ########################################################
# # Change this path to where your DB is stored
# #read the db name 
# db_name = "chinook.db"
# db_path = f"../db/{db_name}"

# # Connect to the SQLite DB
# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# # Get all table names from sqlite_master
# # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# # Get only user-defined tables (not internal SQLite system tables)
# cursor.execute(
#     """
#     SELECT name FROM sqlite_master
#     WHERE type='table' AND name NOT LIKE 'sqlite_%';
# """
# )
# # get the table names
# tables = [row[0] for row in cursor.fetchall()]

# # For each table, get its columns
# # get the columns for each table
# table_columns = []

# for table in tables:
#     cursor.execute(f"PRAGMA table_info({table})")
#     columns = [f"{table}.{row[1]}" for row in cursor.fetchall()]  # row[1] = column name
#     table_columns.extend(columns)
# #print("table_columns", table_columns)

# # Test section
# # i = 0
# # for col in table_columns:
# #     i = i + 1
# #     print(i, col)
# # saved JSON with db name
# # Save as JSON
# with open(f"../output/{db_name}_json.json", "w") as f:
#     json.dump(table_columns, f, indent=2)
# db_service.py
import json
import sqlite3
import os

def get_table_columns():
    # Change this path to where your DB is stored
    db_name = "chinook.db"
    db_path = os.path.join("..", "db", db_name)

    # Connect to the SQLite DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get only user-defined tables
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """
    )
    tables = [row[0] for row in cursor.fetchall()]

    # Get the columns for each table
    table_columns = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [f"{table}.{row[1]}" for row in cursor.fetchall()]
        table_columns.extend(columns)

    # Save as JSON
    os.makedirs("../output", exist_ok=True)
    with open(f"../output/{db_name}_json.json", "w") as f:
        json.dump(table_columns, f, indent=2)

    return table_columns
