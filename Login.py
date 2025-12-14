import streamlit as st
import auth
from DatabaseManager import DatabaseManager

# ---------------------------------------------
# INITIAL SETUP
# ---------------------------------------------

if "db" not in st.session_state:
    st.session_state["db"] = DatabaseManager()
    st.session_state["db"].create_tables()

if "username" not in st.session_state:
    st.session_state["username"] = None

if "role" not in st.session_state:
    st.session_state["role"] = None

# ✅ add a proper logged_in flag used by the dashboard
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


# ---------------------------------------------
# LOGIN FORM
# ---------------------------------------------

def login_form():
    st.subheader("Login")

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        role = auth.login_user(username, password)
        if role:
            # ✅ store login info in session_state
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.session_state["logged_in"] = True

            st.success(f"Logged in as **{username}** ({role})")

            # ✅ Switch to the DASHBOARD page we built
            #    (make sure the file name matches your actual page)
            st.switch_page("pages/Cyber_Dashboard.py")
        else:
            st.error("Invalid username or password.")


# ---------------------------------------------
# REGISTER FORM
# ---------------------------------------------

def register_form():
    st.subheader("Register New User")

    with st.form("register_form", clear_on_submit=True):
        username = st.text_input("New Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submitted = st.form_submit_button("Register")

    if submitted:
        valid_user, msg = auth.validate_username(username)
        if not valid_user:
            st.error(msg)
            return

        valid_pass, msg = auth.validate_password(password)
        if not valid_pass:
            st.error(msg)
            return

        if password != confirm:
            st.error("Passwords do not match.")
            return

        created = auth.register_user(username, password, role)
        if created:
            st.success(f"User '{username}' registered successfully.")
        else:
            st.error("Username already exists.")


# ---------------------------------------------
# MAIN APP PAGE
# ---------------------------------------------

def main():
    st.title("Security App — Login")

    #if already logged in, go straight to dashboard
    if st.session_state.get("logged_in", False) and st.session_state["username"]:
        st.switch_page("pages/Cyber_Dashboard.py")

    # sidebar status + logout
    if st.session_state["username"]:
        st.sidebar.success(
            f"Logged in as {st.session_state['username']} ({st.session_state['role']})"
        )
        if st.sidebar.button("Log Out"):
            st.session_state["username"] = None
            st.session_state["role"] = None
            st.session_state["logged_in"] = False  #reset
            st.rerun()
    else:
        st.sidebar.info("Not logged in")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_form()

    with tab2:
        register_form()


if __name__ == "__main__":
    main()
