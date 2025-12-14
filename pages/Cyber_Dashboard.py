# pages/Cyber_Dashboard.py

import os
import sys
from datetime import datetime

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


def fetch_incidents_df():
    """Return all cyber_incidents as a pandas DataFrame."""
    db = get_db()
    # use the CRUD helper to fetch all incidents
    rows = db.get_all_cyber_incidents(limit=None)
    cols = ["id", "incident_id", "timestamp", "severity", "category", "status", "description"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols)
    return df


# ---------------------------------------------------
# STREAMLIT PAGE CONFIG & LOGIN GUARD
# ---------------------------------------------------
st.set_page_config(
    page_title="Cybersecurity Dashboard",
    layout="wide",
)

st.session_state["current_page"] = "Cybersecurity"

# redirect to root Login.py if not logged in
if not st.session_state.get("logged_in", False):
    st.switch_page("Login.py")

# sidebar logout button
with st.sidebar:
    if st.button("Logout", key="logout_button"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.switch_page("Login.py")

st.title("Cybersecurity Dashboard")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("You must log in to view this page.")
    st.info("Use the Login page to sign in first.")
    st.stop()

st.success(f"Welcome, {st.session_state.get('username', 'user')}!")

# get role from session (default to "user")
current_role = st.session_state.get("role", "user")


# ---------------------------------------------------
# LOAD INCIDENT DATA FROM DATABASE
# ---------------------------------------------------
df = fetch_incidents_df()

if df.empty:
    st.error("No incident data found in the cyber_incidents table.")
    st.stop()

# ensure essential columns exist
for col in ["timestamp", "severity", "category", "status"]:
    if col not in df.columns:
        st.error(f"Expected column '{col}' in cyber_incidents table.")
        st.stop()

# convert timestamp column to datetime and drop bad rows
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"])


# ---------------------------------------------------
# KPI SUMMARY CARDS  (no filters – uses all data)
# ---------------------------------------------------
st.markdown("Key Incident Metrics")

unresolved_statuses = ["open", "in progress", "investigating", "new"]

total_incidents = len(df)

unresolved_count = df[
    df["status"].str.lower().isin(unresolved_statuses)
].shape[0]

high_crit_count = df[
    df["severity"].str.lower().isin(["high", "critical"])
].shape[0]
high_crit_pct = (high_crit_count / total_incidents * 100) if total_incidents else 0

category_counts = df["category"].value_counts()
top_category = category_counts.idxmax() if not category_counts.empty else "N/A"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total incidents", total_incidents)
k2.metric("Unresolved incidents", unresolved_count)
k3.metric("% High/Critical", f"{high_crit_pct:.1f}%")
k4.metric("Most common category", top_category)

st.markdown("---")


# ---------------------------------------------------
# INCIDENT TIMELINE
# ---------------------------------------------------
st.subheader("Incident timeline ")

timeline_df = df.sort_values("timestamp")

fig_timeline = px.bar(
    timeline_df,
    x="timestamp",
    y="category",
    color="severity",
    title="Incidents over time by category and severity",
    labels={"timestamp": "Time", "category": "Category"},
)
st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------
# THREAT TREND — PHISHING SPIKE
# ---------------------------------------------------
st.subheader("Threat trend: phishing spike detection")

phishing_df = df[
    df["category"].str.lower() == "phishing"
].copy()

if phishing_df.empty:
    st.info("No phishing incidents found in the data.")
else:
    monthly_counts = phishing_df.resample("M", on="timestamp").size()
    monthly_counts.index = monthly_counts.index.strftime("%Y-%m")

    st.write("Monthly phishing incidents :")
    st.line_chart(monthly_counts)

    spike_month = monthly_counts.idxmax()
    spike_value = int(monthly_counts.max())

    st.info(
        f"Spike detected: {spike_value} phishing incidents in {spike_month}."
    )

st.markdown("---")


# ---------------------------------------------------
# RESPONSE BOTTLENECK — UNRESOLVED BACKLOG
# ---------------------------------------------------
st.subheader("Response bottleneck: unresolved backlog by category")

unresolved_df = df[
    df["status"].str.lower().isin(unresolved_statuses)
]

if unresolved_df.empty:
    st.info("All incidents in the data are resolved. No backlog.")
else:
    backlog_by_category = (
        unresolved_df["category"]
        .value_counts()
        .to_frame("Unresolved Incidents")
        .sort_values("Unresolved Incidents", ascending=False)
    )

    st.write("Unresolved incidents per category :")
    st.bar_chart(backlog_by_category)

    worst_category = backlog_by_category.index[0]
    worst_count = int(backlog_by_category.iloc[0, 0])

    st.warning(
        f"Bottleneck identified: {worst_category} has the largest backlog "
        f"with {worst_count} unresolved incidents."
    )

st.markdown("---")


# ---------------------------------------------------
# SEVERITY BREAKDOWN
# ---------------------------------------------------
st.subheader("Severity breakdown")

severity_counts = df["severity"].value_counts().reset_index()
severity_counts.columns = ["severity", "count"]

st.write("Incidents by severity :")

fig_sev = px.pie(
    severity_counts,
    names="severity",
    values="count",
    title="Severity distribution",
)
st.plotly_chart(fig_sev, use_container_width=True)


# ---------------------------------------------------
# INCIDENT MANAGEMENT (CRUD)
# ---------------------------------------------------
st.header("Incident management (CRUD)")

st.write(
    "Use these tools to create, update, delete, and view "
    "individual cyber incidents stored in the database."
)

crud_tabs = st.tabs(
    ["Create incident", "Update incident", "Delete incident", "View chart"]
)

db = get_db()  # shared DatabaseManager for all tabs


# ---------- CREATE ----------
with crud_tabs[0]:
    st.subheader("Create a new incident")

    if current_role != "admin":
        st.warning("Only admin users can create incidents.")
    else:
        with st.form("create_incident_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date_val = st.date_input("Date", value=pd.Timestamp.today())
            with col2:
                time_val = st.time_input("Time", value=pd.Timestamp.now().time())

            severity_val = st.selectbox(
                "Severity", ["Low", "Medium", "High", "Critical"]
            )
            category_val = st.selectbox(
                "Category",
                ["Phishing", "Malware", "Misconfiguration", "DDoS", "Unauthorized Access"],
            )
            status_val = st.selectbox(
                "Status", ["Open", "In Progress", "Resolved", "Closed"]
            )
            description_val = st.text_area("Description")

            submitted = st.form_submit_button("Create incident")

        if submitted:
            timestamp_str = pd.Timestamp.combine(date_val, time_val).isoformat()
            if description_val.strip() == "":
                st.error("Please add a short description.")
            else:
                new_row_id = db.insert_cyber_incident(
                    timestamp=timestamp_str,
                    severity=severity_val,
                    category=category_val,
                    status=status_val,
                    description=description_val.strip(),
                )
                if new_row_id is not None:
                    st.success(f"Incident created with row ID {new_row_id}.")
                else:
                    st.error("Insert failed (possibly duplicate incident_id).")


# ---------- UPDATE ----------
with crud_tabs[1]:
    st.subheader("Update an existing incident")

    if current_role != "admin":
        st.warning("Only admin users can update incidents.")
    else:
        df_all = fetch_incidents_df()

        if df_all.empty:
            st.info("No incidents available to update.")
        else:
            # sort newest first
            df_all_sorted = df_all.sort_values("timestamp", ascending=False)

            # labels like "3 – Phishing – Open"
            options = (
                df_all_sorted["id"].astype(str)
                + " – "
                + df_all_sorted["category"].astype(str)
                + " – "
                + df_all_sorted["status"].astype(str)
            )

            selected_label = st.selectbox(
                "Select incident to update", options, index=0
            )
            selected_id = int(selected_label.split("–")[0].strip())

            current_row = df_all_sorted[
                df_all_sorted["id"] == selected_id
            ].iloc[0]

            st.write("Current values:")
            st.json(
                {
                    "id": int(current_row["id"]),
                    "incident_id": current_row["incident_id"],
                    "timestamp": str(current_row["timestamp"]),
                    "severity": current_row["severity"],
                    "category": current_row["category"],
                    "status": current_row["status"],
                    "description": current_row["description"],
                }
            )

            with st.form("update_incident_form"):
                new_severity = st.selectbox(
                    "New severity",
                    ["(no change)", "Low", "Medium", "High", "Critical"],
                    index=["Low", "Medium", "High", "Critical"]
                    .index(current_row["severity"])
                    + 1,
                )

                new_status = st.selectbox(
                    "New status",
                    ["(no change)", "Open", "In Progress", "Resolved", "Closed"],
                    index=["Open", "In Progress", "Resolved", "Closed"]
                    .index(current_row["status"])
                    + 1,
                )

                new_category = st.selectbox(
                    "New category",
                    ["(no change)", "Phishing", "Malware", "Misconfiguration", "DDoS", "Unauthorized Access"],
                    index=[
                        "Phishing",
                        "Malware",
                        "Misconfiguration",
                        "DDoS",
                        "Unauthorized Access",
                    ].index(current_row["category"])
                    + 1,
                )

                new_description = st.text_area(
                    "New description (leave blank to keep current)",
                    value="",
                    placeholder="Only type here if you want to overwrite the current description.",
                )

                update_btn = st.form_submit_button("Update incident")

            if update_btn:
                kwargs = {}
                if new_severity != "(no change)":
                    kwargs["severity"] = new_severity
                if new_status != "(no change)":
                    kwargs["status"] = new_status
                if new_category != "(no change)":
                    kwargs["category"] = new_category
                if new_description.strip():
                    kwargs["description"] = new_description.strip()

                if not kwargs:
                    st.warning("No changes selected.")
                else:
                    ok = db.update_cyber_incident(selected_id, **kwargs)
                    if ok:
                        st.success(f"Incident {selected_id} updated.")
                    else:
                        st.error("Update failed. Check the database or logs.")


# ---------- DELETE ----------
with crud_tabs[2]:
    st.subheader("Delete an incident")

    if current_role != "admin":
        st.warning("Only admin users can delete incidents.")
    else:
        df_all = fetch_incidents_df()

        if df_all.empty:
            st.info("No incidents available to delete.")
        else:
            df_all_sorted = df_all.sort_values("timestamp", ascending=False)

            options = (
                df_all_sorted["id"].astype(str)
                + " – "
                + df_all_sorted["category"].astype(str)
                + " – "
                + df_all_sorted["status"].astype(str)
            )
            selected_label = st.selectbox(
                "Select incident to delete", options, index=0
            )
            selected_id = int(selected_label.split("–")[0].strip())

            st.warning(
                f"You are about to permanently delete incident with row ID {selected_id}."
            )
            confirm = st.checkbox("Yes, I really want to delete this incident.")

            if st.button("Delete incident", disabled=not confirm):
                ok = db.delete_cyber_incident(selected_id)
                if ok:
                    st.success(f"Incident row {selected_id} deleted.")
                else:
                    st.error("Delete failed. Check the database or logs.")


# ---------- VIEW CHART ----------
with crud_tabs[3]:
    st.subheader("View incidents ")

    df_all = fetch_incidents_df()

    if df_all.empty:
        st.info("No incidents in the database.")
    else:
        st.write("Incident count per category:")

        incident_counts = (
            df_all["category"]
            .value_counts()
            .to_frame("Incident Count")
            .sort_values("Incident Count", ascending=False)
        )

        st.bar_chart(incident_counts)




st.markdown('---')
st.header('AI Assistant (Ask your data)')

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
            allowed_tables = ['cyber_incidents']
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
