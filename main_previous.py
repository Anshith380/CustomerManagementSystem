
import streamlit as st
import pandas as pd

from backend import (
    add_customer,
    get_customers,
    update_customer,
    archive_customer,
)

from auth import (
    authenticate_user,
    logout,
    require_role,
)

from user_admin import (
    create_user,
    get_users,
    set_user_active,
)

from lead_backend import (
    create_lead,
    get_leads,
    get_assignable_users,
    update_lead_status,
)

from datetime import datetime
from task_backend import (
    create_task,
    get_tasks,
    get_task_assignees,
    update_task_status,
)

from opportunity_backend import (
    create_opportunity,
    get_opportunities,
    get_opportunity_assignees,
    update_opportunity_stage,
    OPPORTUNITY_STAGES,
)

from interaction_backend import (
    create_interaction,
    get_interactions,
    INTERACTION_TYPES,
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================
st.set_page_config(
    page_title="Customer Management System",
    page_icon="👥",
    layout="wide",
)


# ==================================================
# SESSION INITIALIZATION
# ==================================================
if "user" not in st.session_state:
    st.session_state["user"] = None


# ==================================================
# LOGIN PAGE
# ==================================================
if st.session_state["user"] is None:

    st.title("👥 Customer Management System")
    st.caption("Manage customers, users, and business leads.")
    st.subheader("Secure Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        login_submitted = st.form_submit_button(
            "Login",
            use_container_width=True,
        )

    if login_submitted:
        if not email.strip() or not password:
            st.error("Enter your email and password.")
        else:
            try:
                logged_in_user = authenticate_user(email, password)

                if logged_in_user:
                    st.session_state["user"] = logged_in_user
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

            except Exception:
                st.error(
                    "Login is temporarily unavailable. "
                    "Check the database connection."
                )

    st.stop()


# ==================================================
# LOGGED-IN USER
# ==================================================
user = st.session_state["user"]

st.title("👥 Customer Management System")
st.caption("Manage customers, users, and business leads.")

st.sidebar.write(f"**User:** {user['full_name']}")
st.sidebar.write(f"**Email:** {user['email']}")
st.sidebar.write(f"**Role:** {user['role'].title()}")

if st.sidebar.button("Logout", use_container_width=True):
    logout()


# ==================================================
# ROLE-BASED NAVIGATION
# ==================================================
pages_by_role = {
    "admin": [
        "Dashboard",
        "Add Customer",
        "View Customers",
        "Edit / Archive",
        "Lead Dashboard",
        "Add Lead",
        "Manage Leads",
        "Task Dashboard",
        "Create Task",
        "Manage Tasks",
        "Record Interaction",
        "Interaction History",
        "Opportunities Dashboard",
        "Create Opportunity",
        "Manage Opportunities",
        "User Management",
    ],
    "manager": [
        "Dashboard",
        "Add Customer",
        "View Customers",
        "Edit / Archive",
        "Lead Dashboard",
        "Add Lead",
        "Manage Leads",
        "Task Dashboard",
        "Create Task",
        "Manage Tasks",
        "Record Interaction",
        "Interaction History",
        "Opportunities Dashboard",
        "Create Opportunity",
        "Manage Opportunities",
    ],
    "employee": [
        "Dashboard",
        "Add Customer",
        "View Customers",
        "Lead Dashboard",
        "Add Lead",
        "Manage Leads",
        "Task Dashboard",
        "Create Task",
        "Manage Tasks",
        "Record Interaction",
        "Interaction History",
        "Opportunities Dashboard",
        "Create Opportunity",
        "Manage Opportunities",
    ],
}

role = user["role"]
allowed_pages = pages_by_role.get(role, [])

if not allowed_pages:
    st.error("Your account has no assigned CRM permissions.")
    st.stop()

page = st.sidebar.radio("Navigation", allowed_pages)


# ==================================================
# CUSTOMER DASHBOARD
# ==================================================
if page == "Dashboard":

    st.subheader("CRM Dashboard")

    try:
        customers = get_customers()
        active_customers = get_customers(status="active")
        archived_customers = get_customers(status="archived")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Customers", len(customers))
        col2.metric("Active Customers", len(active_customers))
        col3.metric("Archived Customers", len(archived_customers))

        if customers:
            st.subheader("Recent Customers")
            st.dataframe(
                pd.DataFrame(customers).head(10),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No customers found. Add your first customer.")

    except Exception:
        st.error("Unable to load the dashboard.")


# ==================================================
# ADD CUSTOMER
# ==================================================
elif page == "Add Customer":

    st.subheader("Register a New Customer")

    with st.form("add_customer_form"):
        first_name = st.text_input("First Name *")
        last_name = st.text_input("Last Name *")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        company = st.text_input("Company")
        address = st.text_input("Address")

        source = st.selectbox(
            "Customer Source",
            [
                "Website",
                "Referral",
                "Social Media",
                "Advertisement",
                "Other",
            ],
        )

        submitted = st.form_submit_button("Save Customer")

    if submitted:
        if not first_name.strip() or not last_name.strip():
            st.error("First name and last name are required.")
        else:
            try:
                customer_id = add_customer(
                    first_name=first_name,
                    last_name=last_name,
                    email=email or None,
                    phone=phone or None,
                    company=company or None,
                    address=address or None,
                    source=source,
                )

                st.success(
                    f"Customer added successfully! ID: {customer_id}"
                )

            except Exception:
                st.error(
                    "Unable to add customer. Check the details "
                    "and whether the email already exists."
                )


# ==================================================
# VIEW CUSTOMERS
# ==================================================
elif page == "View Customers":

    st.subheader("Customer Directory")

    search = st.text_input("Search by name, email, or company")

    status = st.selectbox(
        "Filter by Status",
        ["all", "active", "inactive", "archived"],
    )

    try:
        customers = get_customers(search=search, status=status)

        if customers:
            df = pd.DataFrame(customers)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download Customers as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="customers.csv",
                mime="text/csv",
            )
        else:
            st.info("No matching customers found.")

    except Exception:
        st.error("Unable to load customers.")


# ==================================================
# EDIT OR ARCHIVE CUSTOMER
# ==================================================
elif page == "Edit / Archive":

    require_role("admin", "manager")

    st.subheader("Update Customer Information")

    try:
        customers = get_customers(status="all")

        if not customers:
            st.info("No customers are available.")
        else:
            options = {
                (
                    f"{c['customer_id']} - "
                    f"{c['first_name']} {c['last_name']} "
                    f"({c['status']})"
                ): c
                for c in customers
            }

            selected_label = st.selectbox(
                "Select Customer",
                list(options.keys()),
            )
            customer = options[selected_label]

            if customer["status"] == "archived":
                st.warning("This customer is archived.")
            else:
                with st.form("edit_customer_form"):
                    first_name = st.text_input(
                        "First Name",
                        value=customer["first_name"] or "",
                    )
                    last_name = st.text_input(
                        "Last Name",
                        value=customer["last_name"] or "",
                    )
                    email = st.text_input(
                        "Email",
                        value=customer["email"] or "",
                    )
                    phone = st.text_input(
                        "Phone",
                        value=customer["phone"] or "",
                    )
                    company = st.text_input(
                        "Company",
                        value=customer["company"] or "",
                    )
                    address = st.text_input(
                        "Address",
                        value=customer.get("address") or "",
                    )

                    source_options = [
                        "Website",
                        "Referral",
                        "Social Media",
                        "Advertisement",
                        "Other",
                    ]
                    current_source = customer.get("source") or "Other"

                    if current_source not in source_options:
                        source_options.append(current_source)

                    source = st.selectbox(
                        "Customer Source",
                        source_options,
                        index=source_options.index(current_source),
                    )

                    save_changes = st.form_submit_button("Update Customer")

                if save_changes:
                    if not first_name.strip() or not last_name.strip():
                        st.error(
                            "First name and last name are required."
                        )
                    else:
                        try:
                            changed = update_customer(
                                customer_id=customer["customer_id"],
                                first_name=first_name,
                                last_name=last_name,
                                email=email or None,
                                phone=phone or None,
                                company=company or None,
                                address=address or None,
                                source=source,
                            )

                            if changed:
                                st.success("Customer updated successfully.")
                                st.rerun()
                            else:
                                st.info(
                                    "No changes were saved, or the "
                                    "customer could not be updated."
                                )

                        except Exception:
                            st.error("Unable to update customer.")

                st.divider()
                st.warning(
                    "Archiving hides a customer from active records "
                    "without permanently deleting historical records."
                )

                confirm_archive = st.checkbox(
                    "I confirm that I want to archive this customer."
                )

                if st.button(
                    "Archive Customer",
                    disabled=not confirm_archive,
                ):
                    try:
                        archived = archive_customer(
                            customer["customer_id"]
                        )

                        if archived:
                            st.success("Customer archived successfully.")
                            st.rerun()
                        else:
                            st.info("Customer is already archived.")

                    except Exception:
                        st.error("Unable to archive customer.")

    except Exception:
        st.error("Unable to load customer details.")


# ==================================================
# LEAD DASHBOARD
# ==================================================
elif page == "Lead Dashboard":

    st.subheader("Lead Management Dashboard")

    try:
        leads = get_leads()

        total_leads = len(leads)

        qualified_leads = sum(
            lead["lead_status"] == "qualified"
            for lead in leads
        )

        lost_leads = sum(
            lead["lead_status"] == "lost"
            for lead in leads
        )

        converted_leads = sum(
            lead["lead_status"] == "converted"
            for lead in leads
        )

        open_pipeline = sum(
            (
                lead["estimated_value"] or 0
                for lead in leads
                if lead["lead_status"] not in ("converted", "lost")
            ),
            start=0,
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Leads", total_leads)
        col2.metric("Qualified Leads", qualified_leads)
        col3.metric("Converted Leads", converted_leads)
        col4.metric("Lost Leads", lost_leads)

        st.metric("Open Pipeline Value", f"{open_pipeline:,.2f}")

        if leads:
            st.subheader("Recent Leads")
            st.dataframe(
                pd.DataFrame(leads).head(10),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No leads found. Add your first lead.")

    except Exception:
        st.error("Unable to load the lead dashboard.")


# ==================================================
# ADD LEAD
# ==================================================
elif page == "Add Lead":

    st.subheader("Create a New Lead")

    try:
        customers = get_customers(status="active")

        if not customers:
            st.warning(
                "No active customers found. Add a customer first."
            )
        else:
            customer_options = {
                (
                    f"{c['customer_id']} - "
                    f"{c['first_name']} {c['last_name']}"
                ): c["customer_id"]
                for c in customers
            }

            user_options = {}

            if role in ("admin", "manager"):
                assignable_users = get_assignable_users()

                user_options = {
                    (
                        f"{u['full_name']} ({u['role']}) "
                        f"- ID {u['user_id']}"
                    ): u["user_id"]
                    for u in assignable_users
                }

                if not user_options:
                    st.warning("No active users are available.")
                    st.stop()

            with st.form("add_lead_form"):
                selected_customer = st.selectbox(
                    "Select Customer",
                    list(customer_options.keys()),
                )

                estimated_value = st.number_input(
                    "Estimated Deal Value",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                )

                expected_close_date = st.date_input(
                    "Expected Close Date",
                    value=None,
                )

                if role in ("admin", "manager"):
                    selected_assignee = st.selectbox(
                        "Assign Lead To",
                        list(user_options.keys()),
                    )
                else:
                    selected_assignee = None
                    st.info("This lead will be assigned to your account.")

                submitted = st.form_submit_button("Create Lead")

            if submitted:
                try:
                    assigned_to = (
                        user_options[selected_assignee]
                        if role in ("admin", "manager")
                        else user["user_id"]
                    )

                    lead_id = create_lead(
                        customer_id=customer_options[selected_customer],
                        estimated_value=estimated_value,
                        expected_close_date=expected_close_date,
                        assigned_to=assigned_to,
                    )

                    st.success(f"Lead created successfully. ID: {lead_id}")
                    st.rerun()

                except Exception as exc:
                    st.error(f"Unable to create lead: {exc}")

    except Exception:
        st.error("Unable to load the lead creation form.")


# ==================================================
# MANAGE LEADS
# ==================================================
elif page == "Manage Leads":

    st.subheader("Manage Leads")

    search = st.text_input(
        "Search by customer name, email, or lead ID"
    )

    lead_statuses = [
        "new",
        "contacted",
        "qualified",
        "proposal",
        "converted",
        "lost",
    ]

    status_filter = st.selectbox(
        "Filter by Lead Status",
        ["all"] + lead_statuses,
    )

    try:
        leads = get_leads(
            search=search,
            status=status_filter,
        )

        if not leads:
            st.info("No matching leads found.")
        else:
            st.dataframe(
                pd.DataFrame(leads),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("Update Lead Status")

            lead_options = {
                (
                    f"Lead {lead['lead_id']} - "
                    f"{lead['first_name']} {lead['last_name']} "
                    f"({lead['lead_status']})"
                ): lead
                for lead in leads
            }

            selected_lead_label = st.selectbox(
                "Select Lead",
                list(lead_options.keys()),
            )
            selected_lead = lead_options[selected_lead_label]

            new_status = st.selectbox(
                "New Status",
                lead_statuses,
                index=lead_statuses.index(
                    selected_lead["lead_status"]
                ),
            )

            if st.button("Update Lead Status"):
                try:
                    changed = update_lead_status(
                        lead_id=selected_lead["lead_id"],
                        new_status=new_status,
                    )

                    if changed:
                        st.success("Lead status updated successfully.")
                        st.rerun()
                    else:
                        st.info(
                            "Lead was not changed. It may already have "
                            "this status or may not be assigned to you."
                        )

                except Exception as exc:
                    st.error(f"Unable to update lead: {exc}")

    except Exception:
        st.error("Unable to load leads.")



# ==================================================
# TASK DASHBOARD
# ==================================================
elif page == "Task Dashboard":

    st.subheader("Task Management Dashboard")

    try:
        tasks = get_tasks()
        now = datetime.now()

        pending_count = sum(task["status"] == "pending" for task in tasks)
        progress_count = sum(task["status"] == "in_progress" for task in tasks)
        completed_count = sum(task["status"] == "completed" for task in tasks)
        overdue_count = sum(
            task.get("due_at") is not None
            and task["due_at"] < now
            and task["status"] not in ("completed", "cancelled")
            for task in tasks
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pending Tasks", pending_count)
        col2.metric("In Progress", progress_count)
        col3.metric("Completed Tasks", completed_count)
        col4.metric("Overdue Tasks", overdue_count)

        if tasks:
            st.subheader("Tasks")
            st.dataframe(
                pd.DataFrame(tasks),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tasks found. Create your first task.")

    except Exception as exc:
        st.error(f"Unable to load the task dashboard: {exc}")


# ==================================================
# CREATE TASK
# ==================================================
elif page == "Create Task":

    st.subheader("Create a New Task")

    try:
        customers = get_customers(status="active")
        customer_options = {"No customer linked": None}
        for customer in customers:
            label = (
                f"{customer['customer_id']} - "
                f"{customer['first_name']} {customer['last_name']}"
            )
            customer_options[label] = customer["customer_id"]

        user_options = {}
        if role in ("admin", "manager"):
            assignees = get_task_assignees()
            user_options = {
                f"{account['full_name']} ({account['role']}) - ID {account['user_id']}":
                    account["user_id"]
                for account in assignees
            }
            if not user_options:
                st.warning("No active users are available for task assignment.")
                st.stop()

        with st.form("create_task_form"):
            title = st.text_input("Task Title *")
            description = st.text_area("Description")
            selected_customer_label = st.selectbox(
                "Related Customer (optional)",
                list(customer_options.keys()),
            )

            if role in ("admin", "manager"):
                selected_assignee_label = st.selectbox(
                    "Assign Task To",
                    list(user_options.keys()),
                )
            else:
                selected_assignee_label = None
                st.info("This task will be assigned to your account.")

            add_due_date = st.checkbox("Set a due date and time")
            due_date = None
            due_time = None
            if add_due_date:
                due_date = st.date_input("Due Date")
                due_time = st.time_input("Due Time")

            submitted = st.form_submit_button("Create Task")

        if submitted:
            if not title.strip():
                st.error("Task title is required.")
            else:
                due_at = (
                    datetime.combine(due_date, due_time)
                    if add_due_date and due_date is not None and due_time is not None
                    else None
                )
                assigned_to = (
                    user_options[selected_assignee_label]
                    if role in ("admin", "manager")
                    else user["user_id"]
                )
                try:
                    task_id = create_task(
                        title=title,
                        customer_id=customer_options[selected_customer_label],
                        description=description,
                        due_at=due_at,
                        assigned_to=assigned_to,
                    )
                    st.success(f"Task created successfully. ID: {task_id}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create task: {exc}")

    except Exception as exc:
        st.error(f"Unable to load the task creation form: {exc}")


# ==================================================
# MANAGE TASKS
# ==================================================
elif page == "Manage Tasks":

    st.subheader("Manage Tasks")

    search = st.text_input("Search by task title, description, customer, or task ID")
    status_options = ["all", "pending", "in_progress", "completed", "cancelled"]
    status_filter = st.selectbox("Filter by Status", status_options)
    due_filter = st.selectbox(
        "Filter by Due Date",
        ["all", "overdue", "today", "upcoming"],
    )

    try:
        tasks = get_tasks(
            search=search,
            status=status_filter,
            due_filter=due_filter,
        )

        if not tasks:
            st.info("No matching tasks found.")
        else:
            st.dataframe(
                pd.DataFrame(tasks),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("Update Task Status")

            task_options = {
                f"Task {task['task_id']} - {task['title']} ({task['status']})": task
                for task in tasks
            }
            selected_task_label = st.selectbox(
                "Select Task",
                list(task_options.keys()),
            )
            selected_task = task_options[selected_task_label]
            new_status = st.selectbox(
                "New Status",
                ["pending", "in_progress", "completed", "cancelled"],
                index=["pending", "in_progress", "completed", "cancelled"].index(
                    selected_task["status"]
                ),
            )

            if st.button("Update Task Status"):
                try:
                    changed = update_task_status(
                        task_id=selected_task["task_id"],
                        new_status=new_status,
                    )
                    if changed:
                        st.success("Task status updated successfully.")
                        st.rerun()
                    else:
                        st.info(
                            "Task was not changed. It may already have this status "
                            "or may not be assigned to your account."
                        )
                except Exception as exc:
                    st.error(f"Unable to update task status: {exc}")

    except Exception as exc:
        st.error(f"Unable to load tasks: {exc}")



# ==================================================
# RECORD CUSTOMER INTERACTION
# ==================================================
elif page == "Record Interaction":

    st.subheader("Record a Customer Interaction")
    st.caption("Log calls, emails, meetings, and notes against a customer.")

    try:
        customers = get_customers(status="active")

        if not customers:
            st.warning("No active customers found. Add a customer first.")
        else:
            customer_options = {
                f"{c['customer_id']} - {c['first_name']} {c['last_name']}": c["customer_id"]
                for c in customers
            }

            with st.form("record_interaction_form"):
                selected_customer = st.selectbox(
                    "Customer *",
                    list(customer_options.keys()),
                )
                interaction_type = st.selectbox(
                    "Interaction Type",
                    INTERACTION_TYPES,
                    format_func=lambda value: value.title(),
                )
                summary = st.text_input("Summary *")
                details = st.text_area("Details / Outcome")
                interaction_date = st.date_input(
                    "Interaction Date",
                    value=datetime.now().date(),
                )
                interaction_time = st.time_input(
                    "Interaction Time",
                    value=datetime.now().replace(second=0, microsecond=0).time(),
                )
                submitted = st.form_submit_button("Save Interaction")

            if submitted:
                if not summary.strip():
                    st.error("Please enter a short summary.")
                else:
                    interaction_at = datetime.combine(
                        interaction_date, interaction_time
                    )
                    try:
                        interaction_id = create_interaction(
                            customer_id=customer_options[selected_customer],
                            interaction_type=interaction_type,
                            summary=summary,
                            details=details,
                            interaction_at=interaction_at,
                        )
                        st.success(
                            f"Interaction saved successfully. ID: {interaction_id}"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Unable to save interaction: {exc}")

    except Exception as exc:
        st.error(f"Unable to load the interaction form: {exc}")


# ==================================================
# CUSTOMER INTERACTION HISTORY
# ==================================================
elif page == "Interaction History":

    st.subheader("Customer Interaction History")

    search = st.text_input(
        "Search by customer, summary, details, or interaction ID"
    )
    interaction_type_filter = st.selectbox(
        "Filter by Interaction Type",
        ["all"] + INTERACTION_TYPES,
        format_func=lambda value: "All types" if value == "all" else value.title(),
    )

    try:
        customers = get_customers(status="all")
        customer_filter_options = {"All customers": None}
        for customer in customers:
            customer_filter_options[
                f"{customer['customer_id']} - "
                f"{customer['first_name']} {customer['last_name']} "
                f"({customer['status']})"
            ] = customer["customer_id"]

        selected_customer_filter = st.selectbox(
            "Filter by Customer",
            list(customer_filter_options.keys()),
        )

        interactions = get_interactions(
            customer_id=customer_filter_options[selected_customer_filter],
            interaction_type=interaction_type_filter,
            search=search,
        )

        if interactions:
            df = pd.DataFrame(interactions)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "Download Interaction History as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="customer_interactions.csv",
                mime="text/csv",
            )
        else:
            st.info(
                "No interactions found for these filters. "
                "Record an interaction to start the history."
            )

    except Exception as exc:
        st.error(f"Unable to load interaction history: {exc}")



# ==================================================
# OPPORTUNITIES DASHBOARD
# ==================================================
elif page == "Opportunities Dashboard":

    st.subheader("Opportunities Dashboard")
    try:
        opportunities = get_opportunities()
        total = len(opportunities)
        won = [o for o in opportunities if o["stage"] == "won"]
        lost = [o for o in opportunities if o["stage"] == "lost"]
        open_deals = [
            o for o in opportunities
            if o["stage"] not in ("won", "lost")
        ]
        pipeline_value = sum(float(o["amount"] or 0) for o in open_deals)
        won_value = sum(float(o["amount"] or 0) for o in won)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Opportunities", total)
        c2.metric("Open Opportunities", len(open_deals))
        c3.metric("Won Deals", len(won))
        c4.metric("Lost Deals", len(lost))

        c5, c6 = st.columns(2)
        c5.metric("Open Pipeline Value", f"{pipeline_value:,.2f}")
        c6.metric("Won Deal Value", f"{won_value:,.2f}")

        if opportunities:
            st.subheader("Recent Opportunities")
            st.dataframe(
                pd.DataFrame(opportunities),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No opportunities found. Create your first opportunity.")
    except Exception as exc:
        st.error(f"Unable to load opportunities dashboard: {exc}")


# ==================================================
# CREATE OPPORTUNITY
# ==================================================
elif page == "Create Opportunity":

    st.subheader("Create a Sales Opportunity")
    try:
        customers = get_customers(status="active")
        if not customers:
            st.warning("No active customers found. Add a customer first.")
        else:
            customer_options = {
                f"{c['customer_id']} - {c['first_name']} {c['last_name']}":
                    c["customer_id"]
                for c in customers
            }

            assignee_options = {}
            if role in ("admin", "manager"):
                assignees = get_opportunity_assignees()
                assignee_options = {
                    f"{a['full_name']} ({a['role']}) - ID {a['user_id']}":
                        a["user_id"]
                    for a in assignees
                }
                if not assignee_options:
                    st.warning("No active users are available for assignment.")
                    st.stop()

            with st.form("create_opportunity_form"):
                selected_customer = st.selectbox(
                    "Customer *", list(customer_options.keys())
                )
                title = st.text_input("Opportunity Title *")
                amount = st.number_input(
                    "Deal Amount",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                )
                set_close_date = st.checkbox("Set expected close date")
                expected_close_date = None
                if set_close_date:
                    expected_close_date = st.date_input("Expected Close Date")

                if role in ("admin", "manager"):
                    selected_assignee = st.selectbox(
                        "Assign Opportunity To", list(assignee_options.keys())
                    )
                else:
                    selected_assignee = None
                    st.info("This opportunity will be assigned to your account.")

                submitted = st.form_submit_button("Create Opportunity")

            if submitted:
                if not title.strip():
                    st.error("Opportunity title is required.")
                else:
                    assigned_to = (
                        assignee_options[selected_assignee]
                        if role in ("admin", "manager")
                        else user["user_id"]
                    )
                    try:
                        opportunity_id = create_opportunity(
                            customer_id=customer_options[selected_customer],
                            title=title,
                            amount=amount,
                            expected_close_date=expected_close_date,
                            assigned_to=assigned_to,
                        )
                        st.success(
                            f"Opportunity created successfully. ID: {opportunity_id}"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Unable to create opportunity: {exc}")
    except Exception as exc:
        st.error(f"Unable to load opportunity form: {exc}")


# ==================================================
# MANAGE OPPORTUNITIES
# ==================================================
elif page == "Manage Opportunities":

    st.subheader("Manage Sales Opportunities")
    search = st.text_input("Search by opportunity title, customer, or ID")
    stage_filter = st.selectbox(
        "Filter by Stage",
        ["all"] + OPPORTUNITY_STAGES,
        format_func=lambda value: "All stages" if value == "all" else value.title(),
    )

    try:
        customers = get_customers(status="all")
        customer_filter_options = {"All customers": None}
        for c in customers:
            customer_filter_options[
                f"{c['customer_id']} - {c['first_name']} {c['last_name']}"
            ] = c["customer_id"]

        selected_customer_filter = st.selectbox(
            "Filter by Customer", list(customer_filter_options.keys())
        )
        opportunities = get_opportunities(
            search=search,
            stage=stage_filter,
            customer_id=customer_filter_options[selected_customer_filter],
        )

        if not opportunities:
            st.info("No matching opportunities found.")
        else:
            st.dataframe(
                pd.DataFrame(opportunities),
                use_container_width=True,
                hide_index=True,
            )
            st.divider()
            st.subheader("Update Opportunity Stage")
            opportunity_options = {
                f"Opportunity {o['opportunity_id']} - {o['title']} ({o['stage']})": o
                for o in opportunities
            }
            selected_label = st.selectbox(
                "Select Opportunity", list(opportunity_options.keys())
            )
            selected_opportunity = opportunity_options[selected_label]
            new_stage = st.selectbox(
                "New Stage",
                OPPORTUNITY_STAGES,
                index=OPPORTUNITY_STAGES.index(selected_opportunity["stage"]),
                format_func=lambda value: value.title(),
            )
            if st.button("Update Opportunity Stage"):
                try:
                    changed = update_opportunity_stage(
                        selected_opportunity["opportunity_id"], new_stage
                    )
                    if changed:
                        st.success("Opportunity stage updated successfully.")
                        st.rerun()
                    else:
                        st.info(
                            "Opportunity was not changed. It may already have "
                            "this stage or may not be assigned to your account."
                        )
                except Exception as exc:
                    st.error(f"Unable to update opportunity: {exc}")
    except Exception as exc:
        st.error(f"Unable to load opportunities: {exc}")


# ==================================================
# ADMIN USER MANAGEMENT
# ==================================================
elif page == "User Management":

    require_role("admin")

    st.subheader("Admin User Management")
    st.write("Create accounts and manage user access.")

    # Create a user
    st.markdown("### Create a New User")

    with st.form("create_user_form"):
        full_name = st.text_input("Full Name")
        new_email = st.text_input("Email Address")

        new_password = st.text_input(
            "Password (minimum 10 characters)",
            type="password",
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
        )

        new_role = st.selectbox(
            "Assign Role",
            ["employee", "manager", "admin"],
        )

        create_submitted = st.form_submit_button("Create User")

    if create_submitted:
        if not full_name.strip() or not new_email.strip():
            st.error("Full name and email are required.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                new_user_id = create_user(
                    full_name=full_name,
                    email=new_email,
                    password=new_password,
                    role=new_role,
                )

                st.success(
                    f"User created successfully. ID: {new_user_id}"
                )
                st.rerun()

            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error(
                    "Unable to create user. Check the email and database."
                )

    st.divider()
    st.markdown("### Existing Users")

    try:
        users = get_users()

        if users:
            st.dataframe(
                pd.DataFrame(users),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.markdown("### Manage Account Status")

            user_options = {
                (
                    f"{account['user_id']} - "
                    f"{account['full_name']} ({account['role']})"
                ): account
                for account in users
            }

            selected_user_label = st.selectbox(
                "Select a user account",
                list(user_options.keys()),
            )

            selected_user = user_options[selected_user_label]
            currently_active = bool(selected_user["is_active"])

            st.write(
                "Current status:",
                "Active" if currently_active else "Inactive",
            )

            new_status = st.selectbox(
                "New status",
                ["Active", "Inactive"],
                index=0 if currently_active else 1,
            )

            if st.button("Update Account Status"):
                try:
                    changed = set_user_active(
                        user_id=selected_user["user_id"],
                        is_active=(new_status == "Active"),
                        actor_user_id=user["user_id"],
                    )

                    if changed:
                        st.success("Account status updated.")
                        st.rerun()
                    else:
                        st.info("Account status was not changed.")

                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Unable to update account status.")

        else:
            st.info("No user accounts found.")

    except Exception:
        st.error("Unable to load user accounts.")
