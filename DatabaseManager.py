import sqlite3
import os
import csv
import time  # used for generating default IDs for some CRUD helpers

# sqlite3 used for SQL database manipulation
# os is used to check if files exists
# csv is used to read csv files from the data/ folder


class DatabaseManager:
    def __init__(self, db_path="security_app.db"):
        """Establish the database connection when this object is created"""
        # check_same_thread=False is needed because Streamlit reruns code
        # timeout gives SQLite a bit more time before raising "database is locked"
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)

    def execute(self, query, params=()):
        """
        Utility method used to run SQL commands and save changes.
        Returns a cursor so the caller can still use fetchall(), etc.
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def create_tables(self):
        """Creates all required tables if they don’t already exist"""

        # ---------------- USERS TABLE ----------------
        # Table for storing user accounts and roles
        self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );
        """)

        # ---------------- CYBER INCIDENTS TABLE ----------------
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

        # enforce unique incident_id
        self.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cyber_incidents_incident_id
            ON cyber_incidents(incident_id);
        """)

        # ---------------- IT TICKETS TABLE ----------------
        # Table for IT support tickets
        self.execute("""
            CREATE TABLE IF NOT EXISTS it_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT,
                priority TEXT,
                description TEXT,
                status TEXT,
                assigned_to TEXT,
                created_at TEXT,
                resolution_time_hours INTEGER
            );
        """)

        # enforce unique ticket_id
        self.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_it_tickets_ticket_id
            ON it_tickets(ticket_id);
        """)

        # ---------------- DATASETS METADATA TABLE ----------------
        # Table for tracking datasets used by the app / analysts
        self.execute("""
            CREATE TABLE IF NOT EXISTS datasets_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT,
                name TEXT,
                rows INTEGER,
                columns INTEGER,
                uploaded_by TEXT,
                upload_date TEXT
            );
        """)

        # enforce unique dataset_id
        self.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_datasets_metadata_dataset_id
            ON datasets_metadata(dataset_id);
        """)

    # ------------------------------------------------------------------
    # CSV LOADER FUNCTIONS
    # ------------------------------------------------------------------

    def load_cyber_incidents_from_csv(self, csv_path="data/cyber_incidents.csv"):
        """
        Loads incident records from cyber_incidents.csv into the cyber_incidents table.

        - incident_id is UNIQUE (enforced by index)
        - INSERT OR IGNORE means re-running this only inserts *new* incident_ids
        """
        if not os.path.exists(csv_path):
            print(f"CSV not found at: {csv_path}")
            return

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            inserted = 0
            skipped_duplicates = 0

            for row in reader:
                incident_id = row.get("incident_id")
                if not incident_id:
                    continue  # skip invalid rows

                cursor = self.execute("""
                    INSERT OR IGNORE INTO cyber_incidents
                    (incident_id, timestamp, severity, category, status, description)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    incident_id,
                    row.get("timestamp"),
                    row.get("severity"),
                    row.get("category"),
                    row.get("status"),
                    row.get("description")
                ))

                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped_duplicates += 1

        print(f"✔ Loaded {inserted} new cyber incidents from {csv_path}.")
        if skipped_duplicates:
            print(f"ℹ Skipped {skipped_duplicates} duplicate incidents (by incident_id).")

    def load_it_tickets_from_csv(self, csv_path="data/it_tickets.csv"):
        """
        Loads IT ticket records from it_tickets.csv into the it_tickets table.

        - ticket_id is UNIQUE
        - INSERT OR IGNORE means this can be run multiple times safely
        """
        if not os.path.exists(csv_path):
            print(f"CSV not found at: {csv_path}")
            return

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            inserted = 0
            skipped_duplicates = 0

            for row in reader:
                ticket_id = row.get("ticket_id")
                if not ticket_id:
                    continue

                cursor = self.execute("""
                    INSERT OR IGNORE INTO it_tickets
                    (ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    ticket_id,
                    row.get("priority"),
                    row.get("description"),
                    row.get("status"),
                    row.get("assigned_to"),
                    row.get("created_at"),
                    row.get("resolution_time_hours")
                ))

                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped_duplicates += 1

        print(f"✔ Loaded {inserted} new IT tickets from {csv_path}.")
        if skipped_duplicates:
            print(f"ℹ Skipped {skipped_duplicates} duplicate tickets (by ticket_id).")

    def load_datasets_metadata_from_csv(self, csv_path="data/datasets_metadata.csv"):
        """
        Loads dataset metadata from datasets_metadata.csv into the datasets_metadata table.

        - dataset_id is UNIQUE
        - INSERT OR IGNORE means only new datasets are added
        """
        if not os.path.exists(csv_path):
            print(f"CSV not found at: {csv_path}")
            return

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            inserted = 0
            skipped_duplicates = 0

            for row in reader:
                dataset_id = row.get("dataset_id")
                if not dataset_id:
                    continue

                cursor = self.execute("""
                    INSERT OR IGNORE INTO datasets_metadata
                    (dataset_id, name, rows, columns, uploaded_by, upload_date)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    dataset_id,
                    row.get("name"),
                    row.get("rows"),
                    row.get("columns"),
                    row.get("uploaded_by"),
                    row.get("upload_date")
                ))

                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped_duplicates += 1

        print(f"✔ Loaded {inserted} new dataset metadata rows from {csv_path}.")
        if skipped_duplicates:
            print(f"ℹ Skipped {skipped_duplicates} duplicate datasets (by dataset_id).")

    # ------------------------------------------------------------------
    # CRUD HELPERS — USERS
    # ------------------------------------------------------------------

    def create_user(self, username, password_hash, role):
        """
        Insert a new user.
        Returns the new row's id, or None if it failed (e.g. duplicate username).
        """
        try:
            cursor = self.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?);
            """, (username, password_hash, role))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # likely UNIQUE(username) violation
            return None

    def get_user_by_username(self, username):
        """
        Fetch a single user row by username.
        Returns a tuple or None if not found.
        """
        cursor = self.execute(
            "SELECT * FROM users WHERE username = ?;",
            (username,)
        )
        return cursor.fetchone()

    def update_user_password(self, username, new_password_hash):
        """
        Update the password hash for a given username.
        Returns True if something was updated, False otherwise.
        """
        cursor = self.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE username = ?;
        """, (new_password_hash, username))
        return cursor.rowcount > 0

    def delete_user(self, username):
        """
        Delete a user by username.
        Returns True if something was deleted, False otherwise.
        """
        cursor = self.execute(
            "DELETE FROM users WHERE username = ?;",
            (username,)
        )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # CRUD HELPERS — CYBER INCIDENTS
    # ------------------------------------------------------------------

    def get_all_cyber_incidents(self, limit=None):
        """
        Return all cyber_incidents as a list of rows.
        If limit is given, returns at most that many, most recent first.
        """
        if limit is not None:
            cursor = self.execute(
                "SELECT * FROM cyber_incidents ORDER BY timestamp DESC LIMIT ?;",
                (limit,)
            )
        else:
            cursor = self.execute(
                "SELECT * FROM cyber_incidents ORDER BY timestamp DESC;"
            )
        return cursor.fetchall()

    def get_cyber_incident_by_id(self, row_id):
        """
        Fetch a single cyber_incidents row by its internal primary key id.
        """
        cursor = self.execute(
            "SELECT * FROM cyber_incidents WHERE id = ?;",
            (row_id,)
        )
        return cursor.fetchone()

    def get_cyber_incident_by_incident_id(self, incident_id):
        """
        Fetch a single cyber_incidents row by its external incident_id.
        """
        cursor = self.execute(
            "SELECT * FROM cyber_incidents WHERE incident_id = ?;",
            (incident_id,)
        )
        return cursor.fetchone()

    def insert_cyber_incident(self, timestamp, severity, category, status, description, incident_id=None):
        """
        Insert a new cyber incident.

        If incident_id is not provided, a simple one is auto-generated.
        Returns the new row's id, or None if the insert failed.
        """
        if incident_id is None:
            incident_id = f"APP-{int(time.time())}"

        try:
            cursor = self.execute("""
                INSERT INTO cyber_incidents
                (incident_id, timestamp, severity, category, status, description)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (incident_id, timestamp, severity, category, status, description))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # likely UNIQUE(incident_id) violation
            return None

    def update_cyber_incident(self, row_id, **kwargs):
        """
        Update fields of a cyber incident by its primary key id.

        Example:
            db.update_cyber_incident(3, status="Resolved", severity="High")

        Returns True if something was updated, False otherwise.
        """
        if not kwargs:
            return False

        allowed_fields = {"incident_id", "timestamp", "severity", "category", "status", "description"}
        sets = []
        params = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                sets.append(f"{key} = ?")
                params.append(value)

        if not sets:
            return False

        params.append(row_id)
        query = "UPDATE cyber_incidents SET " + ", ".join(sets) + " WHERE id = ?;"
        cursor = self.execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_cyber_incident(self, row_id):
        """
        Delete a cyber incident by its internal id.
        Returns True if something was deleted.
        """
        cursor = self.execute(
            "DELETE FROM cyber_incidents WHERE id = ?;",
            (row_id,)
        )
        return cursor.rowcount > 0

    def delete_cyber_incident_by_incident_id(self, incident_id):
        """
        Delete a cyber incident by its external incident_id.
        Returns True if something was deleted.
        """
        cursor = self.execute(
            "DELETE FROM cyber_incidents WHERE incident_id = ?;",
            (incident_id,)
        )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # CRUD HELPERS — IT TICKETS
    # ------------------------------------------------------------------

    def get_all_it_tickets(self, limit=None):
        """
        Return all it_tickets rows.
        If limit is given, returns at most that many, most recent first.
        """
        if limit is not None:
            cursor = self.execute(
                "SELECT * FROM it_tickets ORDER BY created_at DESC LIMIT ?;",
                (limit,)
            )
        else:
            cursor = self.execute(
                "SELECT * FROM it_tickets ORDER BY created_at DESC;"
            )
        return cursor.fetchall()

    def insert_it_ticket(self, ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours=None):
        """
        Insert a new IT ticket.
        Returns the new row's id, or None if insert failed (e.g. duplicate ticket_id).
        """
        try:
            cursor = self.execute("""
                INSERT INTO it_tickets
                (ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                ticket_id,
                priority,
                description,
                status,
                assigned_to,
                created_at,
                resolution_time_hours
            ))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def update_it_ticket(self, row_id, **kwargs):
        """
        Update fields of an IT ticket by its primary key id.
        Returns True if something was updated.
        """
        if not kwargs:
            return False

        allowed_fields = {"ticket_id", "priority", "description", "status", "assigned_to", "created_at", "resolution_time_hours"}
        sets = []
        params = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                sets.append(f"{key} = ?")
                params.append(value)

        if not sets:
            return False

        params.append(row_id)
        query = "UPDATE it_tickets SET " + ", ".join(sets) + " WHERE id = ?;"
        cursor = self.execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_it_ticket(self, row_id):
        """
        Delete an IT ticket by its internal id.
        """
        cursor = self.execute(
            "DELETE FROM it_tickets WHERE id = ?;",
            (row_id,)
        )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # CRUD HELPERS — DATASETS METADATA
    # ------------------------------------------------------------------

    def get_all_datasets_metadata(self, limit=None):
        """
        Return all datasets_metadata rows.
        """
        if limit is not None:
            cursor = self.execute(
                "SELECT * FROM datasets_metadata ORDER BY upload_date DESC LIMIT ?;",
                (limit,)
            )
        else:
            cursor = self.execute(
                "SELECT * FROM datasets_metadata ORDER BY upload_date DESC;"
            )
        return cursor.fetchall()

    def insert_dataset_metadata(self, dataset_id, name, rows, columns, uploaded_by, upload_date):
        """
        Insert a new dataset metadata row.
        Returns the new row's id or None if insert failed.
        """
        try:
            cursor = self.execute("""
                INSERT INTO datasets_metadata
                (dataset_id, name, rows, columns, uploaded_by, upload_date)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (dataset_id, name, rows, columns, uploaded_by, upload_date))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def update_dataset_metadata(self, row_id, **kwargs):
        """
        Update fields of a dataset metadata row by its id.
        """
        if not kwargs:
            return False

        allowed_fields = {"dataset_id", "name", "rows", "columns", "uploaded_by", "upload_date"}
        sets = []
        params = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                sets.append(f"{key} = ?")
                params.append(value)

        if not sets:
            return False

        params.append(row_id)
        query = "UPDATE datasets_metadata SET " + ", ".join(sets) + " WHERE id = ?;"
        cursor = self.execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_dataset_metadata(self, row_id):
        """
        Delete a dataset metadata row by its id.
        """
        cursor = self.execute(
            "DELETE FROM datasets_metadata WHERE id = ?;",
            (row_id,)
        )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------

    def close(self):
        """Closes the DB connection cleanly when the app shuts down"""
        if self.conn:
            self.conn.close()
            self.conn = None


def migrate_users_from_txt(db: DatabaseManager, txt_path="data/users.txt"):
    """Function to migrate data from users.txt to the database"""
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

            # OR IGNORE avoids UNIQUE constraint errors if the user already exists
            db.execute(
                """
                INSERT OR IGNORE INTO users (username, password_hash, role)
                VALUES (?, ?, ?);
                """,
                (username, password_hash, role)
            )

            print(f"Inserted user: {username}")


# Run migrations / loaders only if this file is executed directly
if __name__ == "__main__":
    db = DatabaseManager()
    db.create_tables()

    # migrate users from text file
    migrate_users_from_txt(db)

    # load all three CSVs
    db.load_cyber_incidents_from_csv()
    db.load_it_tickets_from_csv()
    db.load_datasets_metadata_from_csv()

    db.close()
