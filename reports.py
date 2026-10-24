import pandas as pd
import streamlit as st

from backend import get_customers
from lead_backend import get_leads
from opportunity_backend import get_opportunities


def render_reports():
    """Render CRM customer, lead, and sales reports."""
    st.subheader("Reports & Analytics")
    st.caption("Summary reports based on your current CRM records.")

    try:
        customers = get_customers(status="all")
        active_customers = get_customers(status="active")
        inactive_customers = get_customers(status="inactive")
        archived_customers = get_customers(status="archived")
        leads = get_leads()
        opportunities = get_opportunities()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Customers", len(customers))
        col2.metric("Active Customers", len(active_customers))
        col3.metric("Inactive Customers", len(inactive_customers))
        col4.metric("Archived Customers", len(archived_customers))

        st.divider()
        st.markdown("### Lead Summary")
        lead_statuses = ["new", "contacted", "qualified", "proposal", "converted", "lost"]
        lead_counts = {
            status: sum(lead.get("lead_status") == status for lead in leads)
            for status in lead_statuses
        }
        lead_col1, lead_col2, lead_col3 = st.columns(3)
        lead_col1.metric("Total Leads", len(leads))
        lead_col2.metric("Qualified Leads", lead_counts["qualified"])
        lead_col3.metric("Converted Leads", lead_counts["converted"])

        if leads:
            lead_df = pd.DataFrame(leads)
            if "lead_status" in lead_df.columns:
                st.markdown("#### Leads by Status")
                status_df = (
                    lead_df["lead_status"]
                    .value_counts()
                    .reindex(lead_statuses, fill_value=0)
                    .rename_axis("lead_status")
                    .reset_index(name="count")
                )
                st.bar_chart(status_df.set_index("lead_status"))
                st.dataframe(lead_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Lead Report CSV",
                    data=lead_df.to_csv(index=False).encode("utf-8"),
                    file_name="crm_lead_report.csv",
                    mime="text/csv",
                )
        else:
            st.info("No leads are available for reporting yet.")

        st.divider()
        st.markdown("### Sales Opportunity Summary")
        won = [o for o in opportunities if o.get("stage") == "won"]
        lost = [o for o in opportunities if o.get("stage") == "lost"]
        open_opportunities = [
            o for o in opportunities
            if o.get("stage") not in ("won", "lost")
        ]
        pipeline_value = sum(float(o.get("amount") or 0) for o in open_opportunities)
        won_value = sum(float(o.get("amount") or 0) for o in won)

        sales_col1, sales_col2, sales_col3, sales_col4 = st.columns(4)
        sales_col1.metric("Total Opportunities", len(opportunities))
        sales_col2.metric("Open Opportunities", len(open_opportunities))
        sales_col3.metric("Won Deals", len(won))
        sales_col4.metric("Lost Deals", len(lost))
        sales_col5, sales_col6 = st.columns(2)
        sales_col5.metric("Open Pipeline Value", f"{pipeline_value:,.2f}")
        sales_col6.metric("Won Deal Value", f"{won_value:,.2f}")

        if opportunities:
            opp_df = pd.DataFrame(opportunities)
            if "stage" in opp_df.columns:
                stage_order = ["qualification", "proposal", "negotiation", "won", "lost"]
                stage_df = (
                    opp_df["stage"]
                    .value_counts()
                    .reindex(stage_order, fill_value=0)
                    .rename_axis("stage")
                    .reset_index(name="count")
                )
                st.markdown("#### Opportunities by Stage")
                st.bar_chart(stage_df.set_index("stage"))
            st.dataframe(opp_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Opportunity Report CSV",
                data=opp_df.to_csv(index=False).encode("utf-8"),
                file_name="crm_opportunity_report.csv",
                mime="text/csv",
            )
        else:
            st.info("No opportunities are available for reporting yet.")

        st.divider()
        st.markdown("### Customer Report")
        if customers:
            customer_df = pd.DataFrame(customers)
            st.dataframe(customer_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Customer Report CSV",
                data=customer_df.to_csv(index=False).encode("utf-8"),
                file_name="crm_customer_report.csv",
                mime="text/csv",
            )
        else:
            st.info("No customers are available for reporting yet.")

    except Exception as exc:
        st.error(f"Unable to load CRM reports: {exc}")
