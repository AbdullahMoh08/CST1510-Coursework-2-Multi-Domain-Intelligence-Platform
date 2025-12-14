# pages/IT_Operations.py

import os
import sys

import streamlit as st
import pandas as pd
import plotly.express as px
from api_utils import ai_generate_sql


# ---------------------------------------------------
# Allow importing DatabaseManager from project root
# ---------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from DatabaseManager import DatabaseManager  # uses security_app.db


# ---------------------------------------------------
# DB HELPER SETUP
# ---------------------------------------------------
@st.cache_resource
def get_db():
    """Create a single shared DatabaseManager for the app."""
    db = DatabaseManager()          # security_app.db by default
    db.create_tables()              # make sure all tables exist
    return db


def fetch_tickets_df():
    """
    Return IT tickets as a pandas DataFrame.

    Try to read from the it_tickets table via DatabaseManager
    If empty, fall back to data/it_tickets.csv
    """
    db = get_db()

    #
    rows = db.get_all_it_tickets(limit=None)
    if rows:
        cols = [
            "id",
            "ticket_id",
            "priority",
            "description",
            "status",
            "assigned_to",
            "created_at",
            "resolution_time_hours",
        ]
        df_db = pd.DataFrame(rows, columns=cols)
        return df_db

    # Fallback to CSV
    csv_path = os.path.join("data", "it_tickets.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()

    df_csv = pd.read_csv(csv_path)
    return df_csv


# ---------------------------------------------------
# STREAMLIT PAGE CONFIG & LOGIN GUARD
# ---------------------------------------------------
st.set_page_config(
    page_title="IT Operations Dashboard",
    layout="wide",
)

st.session_state["current_page"] = "IT Operations"

# redirect to root Login.py if not logged in
if not st.session_state.get("logged_in", False):
    st.switch_page("Login.py")

# sidebar logout button
with st.sidebar:
    if st.button("Logout", key="logout_button"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.switch_page("Login.py")

st.title("IT Operations Dashboard")

#checks if the a user is logged in
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("You must log in to view this page.")
    st.info("Use the Login page to sign in first.")
    st.stop()

st.success(f"Welcome, {st.session_state.get('username', 'user')}!")

current_role = st.session_state.get("role", "user")


# ---------------------------------------------------
# LOAD TICKET DATA
# ---------------------------------------------------
df = fetch_tickets_df()

if df.empty:
    st.error("No ticket data found in the it_tickets table or CSV.")
    st.stop()

# ensure created_at exists
if "created_at" not in df.columns:
    st.error("Expected column 'created_at' in it_tickets data.")
    st.stop()

# convert created_at column to datetime and drop invalid rows
df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
df = df.dropna(subset=["created_at"])

# ensure core columns exist
required_cols = [
    "ticket_id",
    "priority",
    "description",
    "status",
    "assigned_to",
    "resolution_time_hours",
]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required columns in ticket data: {missing}")
    st.stop()


# ---------------------------------------------------
# KPI SUMMARY CARDS  (NO FILTERS – full dataset)
# ---------------------------------------------------
st.markdown("### Key Ticket Metrics")

open_statuses = ["open", "in progress", "new"]

total_tickets = len(df)

# open / in-progress tickets
open_tickets = df[
    df["status"].str.lower().isin(open_statuses)
].shape[0]

# resolved / closed tickets for resolution analysis
resolved_df = df[
    df["status"].str.lower().isin(["resolved", "closed"])
]

avg_resolution = (
    resolved_df["resolution_time_hours"].mean()
    if not resolved_df.empty
    else 0
)

top_agent = (
    df["assigned_to"].value_counts().idxmax()
    if not df.empty
    else "N/A"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total tickets", total_tickets)
c2.metric("Open tickets", open_tickets)
c3.metric("Avg. resolution time (hrs)", f"{avg_resolution:.1f}")
c4.metric("Busiest support agent", top_agent)

st.markdown("---")


# ---------------------------------------------------
# TICKET TIMELINE
# ---------------------------------------------------
st.subheader("Ticket timeline ")

timeline_df = df.sort_values("created_at")

fig_timeline = px.bar(
    timeline_df,
    x="created_at",
    y="priority",
    color="status",
    title="Tickets over time by priority and status",
    labels={"created_at": "Created at", "priority": "Priority"},
)
st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------
# STATUS & PRIORITY OVERVIEW
# ---------------------------------------------------
st.subheader("Ticket status overview")

status_counts = (
    df["status"]
    .value_counts()
    .to_frame("Ticket Count")
    .sort_values("Ticket Count", ascending=False)
)
st.write("Tickets per status :")
st.bar_chart(status_counts)

st.markdown("---")

st.subheader("Priority distribution")

priority_counts = (
    df["priority"]
    .value_counts()
    .to_frame("Ticket Count")
    .sort_values("Ticket Count", ascending=False)
)
st.write("Tickets per priority :")
st.bar_chart(priority_counts)

st.markdown("---")


# ---------------------------------------------------
# RESOLUTION BOTTLENECK — BY PRIORITY
# ---------------------------------------------------
st.subheader("Average resolution time by priority")

if not resolved_df.empty:
    res_time_by_priority = (
        resolved_df.groupby("priority")["resolution_time_hours"]
        .mean()
        .to_frame("Avg Resolution Time (hrs)")
        .sort_values("Avg Resolution Time (hrs)", ascending=False)
    )
    st.bar_chart(res_time_by_priority)

    slowest_priority = res_time_by_priority.index[0]
    slowest_time = float(res_time_by_priority.iloc[0, 0])
    st.info(
        f"Slowest to resolve: {slowest_priority} tickets "
        f"take an average of {slowest_time:.1f} hours."
    )
else:
    st.info("No resolved tickets in the data to analyse resolution time.")

st.markdown("---")


# ---------------------------------------------------
# ACTIVE TICKETS BY AGENT (BOTTLENECK)
# ---------------------------------------------------
st.subheader("Active tickets by support agent")

active_statuses = ["open", "in progress", "waiting for user"]

active_tickets = df[
    df["status"].str.lower().isin(active_statuses)
]

if active_tickets.empty:
    st.info("There are no active tickets for any agent in the data.")
else:
    tickets_by_agent = (
        active_tickets.groupby("assigned_to")["ticket_id"]
        .count()
        .to_frame("Active Tickets")
        .sort_values("Active Tickets", ascending=False)
    )

    st.write("Number of open / in-progress tickets per agent :")
    st.bar_chart(tickets_by_agent)

    busiest_agent = tickets_by_agent.index[0]
    busiest_count = int(tickets_by_agent.iloc[0, 0])

    st.warning(
        f"Potential bottleneck: {busiest_agent} currently has "
        f"{busiest_count} active tickets."
    )

st.markdown("---")


# ---------------------------------------------------
# INCIDENT MANAGEMENT (CRUD) – ADMIN ONLY
# ---------------------------------------------------
st.header("IT Ticket Management (CRUD)")

st.write(
    "Use these tools to create, update, delete, and view "
    "IT support tickets stored in the database."
)

crud_tabs = st.tabs(
    ["Create ticket", "Update ticket", "Delete ticket", "View chart"]
)

db = get_db()  # shared DatabaseManager for all tabs


# ---------- CREATE ----------
with crud_tabs[0]:
    st.subheader("Create a new ticket")

    if current_role != "admin":
        st.warning("Only admin users can create tickets.")
    else:
        with st.form("create_ticket_form", clear_on_submit=True):
            ticket_id_val = st.text_input("Ticket ID")
            col1, col2 = st.columns(2)
            with col1:
                date_val = st.date_input("Created date", value=pd.Timestamp.today())
            with col2:
                time_val = st.time_input("Created time", value=pd.Timestamp.now().time())

            priority_val = st.selectbox(
                "Priority", ["Low", "Medium", "High", "Critical"]
            )
            status_val = st.selectbox(
                "Status", ["Open", "In Progress", "Resolved", "Closed", "Waiting for user"]
            )
            assigned_to_val = st.text_input("Assigned to (agent name)")
            resolution_val = st.number_input(
                "Resolution time (hours, optional)", min_value=0.0, step=0.5, value=0.0
            )
            description_val = st.text_area("Description")

            submitted = st.form_submit_button("Create ticket")

        if submitted:
            if not ticket_id_val.strip():
                st.error("Ticket ID is required.")
            elif not description_val.strip():
                st.error("Please add a short description.")
            else:
                created_at_str = pd.Timestamp.combine(date_val, time_val).isoformat()
                res_hours = resolution_val if resolution_val > 0 else None

                new_row_id = db.insert_it_ticket(
                    ticket_id=ticket_id_val.strip(),
                    priority=priority_val,
                    description=description_val.strip(),
                    status=status_val,
                    assigned_to=assigned_to_val.strip(),
                    created_at=created_at_str,
                    resolution_time_hours=res_hours,
                )
                if new_row_id is not None:
                    st.success(f"Ticket created with row ID {new_row_id}.")
                else:
                    st.error("Insert failed (possibly duplicate ticket_id).")


# ---------- UPDATE ----------
with crud_tabs[1]:
    st.subheader("Update an existing ticket")

    if current_role != "admin":
        st.warning("Only admin users can update tickets.")
    else:
        df_all = fetch_tickets_df()

        if df_all.empty:
            st.info("No tickets available to update.")
        else:
            df_all_sorted = df_all.sort_values("created_at", ascending=False)

            options = (
                df_all_sorted["id"].astype(str)
                + " – "
                + df_all_sorted["ticket_id"].astype(str)
                + " – "
                + df_all_sorted["status"].astype(str)
            )

            selected_label = st.selectbox(
                "Select ticket to update", options, index=0
            )
            selected_id = int(selected_label.split("–")[0].strip())

            current_row = df_all_sorted[
                df_all_sorted["id"] == selected_id
            ].iloc[0]

            st.write("Current values:")
            st.json(
                {
                    "id": int(current_row["id"]),
                    "ticket_id": current_row["ticket_id"],
                    "created_at": str(current_row["created_at"]),
                    "priority": current_row["priority"],
                    "status": current_row["status"],
                    "assigned_to": current_row["assigned_to"],
                    "resolution_time_hours": current_row["resolution_time_hours"],
                    "description": current_row["description"],
                }
            )

            with st.form("update_ticket_form"):
                new_priority = st.selectbox(
                    "New priority",
                    ["(no change)", "Low", "Medium", "High", "Critical"],
                    index=["Low", "Medium", "High", "Critical"]
                    .index(current_row["priority"])
                    + 1,
                )

                new_status = st.selectbox(
                    "New status",
                    ["(no change)", "Open", "In Progress", "Resolved", "Closed", "Waiting for user"],
                    index=["Open", "In Progress", "Resolved", "Closed", "Waiting for user"]
                    .index(current_row["status"])
                    + 1,
                )

                new_assigned = st.text_input(
                    "New assigned to (leave blank for no change)",
                    value="",
                    placeholder=f"Current: {current_row['assigned_to']}",
                )

                new_resolution = st.number_input(
                    "New resolution time (hours, leave 0 for no change)",
                    min_value=0.0,
                    step=0.5,
                    value=0.0,
                )

                new_description = st.text_area(
                    "New description (leave blank to keep current)",
                    value="",
                    placeholder="Only type here if you want to overwrite the current description.",
                )

                update_btn = st.form_submit_button("Update ticket")

            if update_btn:
                kwargs = {}
                if new_priority != "(no change)":
                    kwargs["priority"] = new_priority
                if new_status != "(no change)":
                    kwargs["status"] = new_status
                if new_assigned.strip():
                    kwargs["assigned_to"] = new_assigned.strip()
                if new_resolution > 0:
                    kwargs["resolution_time_hours"] = new_resolution
                if new_description.strip():
                    kwargs["description"] = new_description.strip()

                if not kwargs:
                    st.warning("No changes selected.")
                else:
                    ok = db.update_it_ticket(selected_id, **kwargs)
                    if ok:
                        st.success(f"Ticket {selected_id} updated.")
                    else:
                        st.error("Update failed. Check the database or logs.")


# ---------- DELETE ----------
with crud_tabs[2]:
    st.subheader("Delete a ticket")

    if current_role != "admin":
        st.warning("Only admin users can delete tickets.")
    else:
        df_all = fetch_tickets_df()

        if df_all.empty:
            st.info("No tickets available to delete.")
        else:
            df_all_sorted = df_all.sort_values("created_at", ascending=False)

            options = (
                df_all_sorted["id"].astype(str)
                + " – "
                + df_all_sorted["ticket_id"].astype(str)
                + " – "
                + df_all_sorted["status"].astype(str)
            )
            selected_label = st.selectbox(
                "Select ticket to delete", options, index=0
            )
            selected_id = int(selected_label.split("–")[0].strip())

            st.warning(
                f"You are about to permanently delete ticket with row ID {selected_id}."
            )
            confirm = st.checkbox("Yes, I really want to delete this ticket.")

            if st.button("Delete ticket", disabled=not confirm):
                ok = db.delete_it_ticket(selected_id)
                if ok:
                    st.success(f"Ticket row {selected_id} deleted.")
                else:
                    st.error("Delete failed. Check the database or logs.")


# ---------- VIEW CHART ----------
with crud_tabs[3]:
    st.subheader("View tickets ")

    df_all = fetch_tickets_df()

    if df_all.empty:
        st.info("No tickets in the database.")
    else:
        st.write("Ticket count per priority:")

        ticket_counts = (
            df_all["priority"]
            .value_counts()
            .to_frame("Ticket Count")
            .sort_values("Ticket Count", ascending=False)
        )

        st.bar_chart(ticket_counts)


#--------
#AI
st.markdown('---')
st.header('AI Assistant')

show_sql = st.toggle('Show SQL query', value=False, key='dash_ai_show_sql')
show_table = st.toggle('Show table results', value=True, key='dash_ai_show_table')

if 'dash_ai_messages' not in st.session_state:
    st.session_state['dash_ai_messages'] = [
        {'role': 'assistant', 'content': "Ask me questions about this dashboard’s data."}
    ]

for msg in st.session_state['dash_ai_messages']:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

q = st.chat_input('Ask a question...')

if q:
    st.session_state['dash_ai_messages'].append({'role': 'user', 'content': q})
    with st.chat_message('user'):
        st.markdown(q)

    with st.chat_message('assistant'):
        with st.spinner('Thinking...'):
            allowed_tables = ['it_tickets']
            sql, explanation = ai_generate_sql(question=q, allowed_tables=allowed_tables)
            df_ai = run_select_query(sql)

            st.markdown(explanation)

            if show_sql:
                st.code(sql, language='sql')

            if show_table:
                if df_ai.empty:
                    st.info('No matching records were found.')
                else:
                    st.dataframe(df_ai, use_container_width=True)

            st.session_state['dash_ai_messages'].append({'role': 'assistant', 'content': explanation})
