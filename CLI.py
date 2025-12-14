import auth
from DatabaseManager import DatabaseManager


db = DatabaseManager()
db.create_tables()  # ensure required tables exist before using the app


# =========================================
# User Registration (CLI)
# =========================================
def cli_register():
    """Interactive command-line flow to register a new user."""
    print("\n--- Register New User ---")
    username = input("Enter username: ")

    # Check if the username meets validation rules (length, characters, etc.)
    valid_user, msg = auth.validate_username(username)
    if not valid_user:
        print(f"Error: {msg}")
        return

    # Ask for password and validate its strength (length, letters, numbers)
    password = input("Enter password: ")
    valid_pass, msg = auth.validate_password(password)
    if not valid_pass:
        print(f"Error: {msg}")
        return

    # Confirm password to avoid typos during registration
    confirm = input("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match.")
        return

    # Ask for a role and default to "user" if input is invalid or blank
    role = input("Enter role (user/admin) [default: user]: ").strip().lower()
    if role not in ['admin', 'user']:
        role = 'user'

    # Pass the data to the auth module to actually create the user account
    success = auth.register_user(username, password, role)
    if success:
        print(f"Success! User '{username}' registered with role '{role}'.")
    else:
        print(f"Error: Username '{username}' already exists.")


# =========================================
# User Login (CLI)
# =========================================
def cli_login():
    """Interactive command-line flow to log in a user."""
    print("\n--- Login ---")
    username = input("Enter username: ")
    password = input("Enter password: ")

    # Use the auth module to verify credentials and fetch the user role
    role = auth.login_user(username, password)

    if role:
        print("\nLOGIN SUCCESSFUL!")
        print(f"Welcome back, {username}.")
        print(f"Your access level is: {role.upper()}")
        # Return both username and role so the main loop can track the logged-in user
        return {"username": username, "role": role}
    else:
        print("\nLogin Failed: Invalid username or password.")
        return None


# =========================================
# CYBER INCIDENTS CRUD OPERATIONS
# =========================================
def create_cyber_incident():
    """Collect details from the user and insert a new cyber incident into the database."""
    print("\n--- Create New Cyber Incident ---")
    incident_id = input("Incident ID: ")
    timestamp = input("Timestamp (e.g. 2025-11-30 10:30): ")
    severity = input("Severity (Low/Medium/High/Critical): ")
    category = input("Category (e.g. Phishing, Malware): ")
    status = input("Status (Open/Investigating/Resolved/Closed): ")
    description = input("Description: ")

    db.execute(
        """
        INSERT INTO cyber_incidents (
            incident_id, timestamp, severity, category, status, description
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (incident_id, timestamp, severity, category, status, description)
    )
    print("Incident created successfully.")


def read_all_cyber_incidents():
    """Fetch and display a summary list of all cyber incidents stored in the database."""
    print("\n--- All Cyber Incidents ---")
    cursor = db.execute(
        "SELECT id, incident_id, timestamp, severity, category, status FROM cyber_incidents;"
    )
    rows = cursor.fetchall()

    if not rows:
        print("No incidents found.")
        return

    for row in rows:
        row_id, incident_id, timestamp, severity, category, status = row
        print(f"[{row_id}] {incident_id} | {timestamp} | {severity} | {category} | {status}")


def update_cyber_incident():
    """Allow the user to select an incident and update its severity, status, or description."""
    print("\n--- Update Cyber Incident ---")
    read_all_cyber_incidents()  # show existing incidents so user can choose one
    row_id = input("Enter the DB ID of the incident you want to update: ")

    cursor = db.execute(
        "SELECT incident_id, severity, status, description FROM cyber_incidents WHERE id = ?;",
        (row_id,)
    )
    current = cursor.fetchone()
    if not current:
        print("❌ Incident not found.")
        return

    print(f"Current -> Incident ID={current[0]}, Severity={current[1]}, Status={current[2]}")
    print("Leave a field empty if you don't want to change it.\n")

    # Ask for updated values, allowing user to skip fields they don't want to change
    new_severity = input("New Severity (press Enter to keep current): ")
    new_status = input("New Status (press Enter to keep current): ")
    new_description = input("New Description (press Enter to keep current): ")

    severity = new_severity if new_severity else current[1]
    status = new_status if new_status else current[2]
    description = new_description if new_description else current[3]

    db.execute(
        """
        UPDATE cyber_incidents
        SET severity = ?, status = ?, description = ?
        WHERE id = ?;
        """,
        (severity, status, description, row_id)
    )
    print("✅ Incident updated successfully.")


def delete_cyber_incident():
    """Prompt the user to select and permanently remove a cyber incident from the database."""
    print("\n--- Delete Cyber Incident ---")
    read_all_cyber_incidents()
    row_id = input("Enter the DB ID of the incident you want to delete: ")

    confirm = input(f"Are you sure you want to delete incident {row_id}? (Y/N): ").strip().upper()
    if confirm != "Y":
        print("Deletion cancelled.")
        return

    db.execute("DELETE FROM cyber_incidents WHERE id = ?;", (row_id,))
    print("✅ Incident deleted successfully.")


def crud_menu():
    """Menu loop for performing CRUD operations on cyber incidents."""
    while True:
        print("\n=== CYBER INCIDENTS MENU ===")
        print("1. Create incident")
        print("2. View incidents")
        print("3. Update incident")
        print("4. Delete incident")
        print("5. Back to main menu")

        choice = input("Select an option (1-5): ")

        if choice == '1':
            create_cyber_incident()
        elif choice == '2':
            read_all_cyber_incidents()
        elif choice == '3':
            update_cyber_incident()
        elif choice == '4':
            delete_cyber_incident()
        elif choice == '5':
            break
        else:
            print("Invalid choice, please try again.")


# =========================================
# MAIN APPLICATION LOOP (AUTH + CRUD MENU)
# =========================================
current_user = None  # stores the logged-in user's username and role, if any

while True:
    print("\n=== AUTH & CYBER SYSTEM CLI ===")
    print("1. Register new user")
    print("2. Login to system")
    print("3. Edit cyber incidents database (CRUD)")
    print("4. Exit")

    choice = input("Select an option (1-4): ")

    if choice == '1':
        # Start the registration flow
        cli_register()

    elif choice == '2':
        # Start the login flow and keep track of the logged-in user
        current_user = cli_login()

    elif choice == '3':
        # Only logged-in admin users should be able to access the CRUD menu
        if current_user is None:
            print("You must be logged in to acess database features")
            current_user = cli_login()
        if current_user:
            if current_user["role"] == "admin":
                crud_menu()
        else:
            print("Access denied: only ADMIN users can edit the database")

    elif choice == '4':
        # Exit the application
        print("Exiting system. Goodbye!")
        break

    else:
        print("Invalid choice, please try again.")

# Close database connection when the program finishes
db.close()
