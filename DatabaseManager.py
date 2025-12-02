import sqlite3
import os
# sqlite3 used for SQL database manipulation
# os is used to check if flies exists


class DatabaseManager:
    def __init__(self, db_path="security_app.db"):
        """Establish the database connection when this object is created"""
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def execute(self, query, params=()):
        # Utility method used to run SQL commands and save changes
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def create_tables(self):
        # Creates all required tables if they don’t already exist

        # Table for storing user accounts and roles
        self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );
        """)

        # Table for storing cybersecurity incident details
        self.execute("""
            CREATE TABLE IF NOT EXISTS cyber_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT,
                timestamp TEXT,
                severity TEXT,
                category TEXT,
                status TEXT,
                description TEXT
            );
        """)

    def close(self):
        # Closes the DB connection cleanly when the app shuts down
        self.conn.close()




def migrate_users_from_txt(db: DatabaseManager, txt_path="data/users.txt"):
    """Function to migrate data from user.txt to the database"""
    # Check if the text file exists; skip migration if missing
    if not os.path.exists(txt_path):
        print("users.txt not found, skipping migration.")
        return

    # Read each user entry from the text file and insert into database
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # ignore empty lines

            username, password_hash, role = line.split(",")

            #instering the values in the user.txt in the users table and print the values username that has been inserted
            db.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?);
                """,
                (username, password_hash, role)
            )
            print(f"Inserted user: {username}")




#runs the database file to create the tables and migrate the data
db = DatabaseManager()
db.create_tables()
migrate_users_from_txt(db)
