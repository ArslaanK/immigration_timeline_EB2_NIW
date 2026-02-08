import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px

st.set_page_config(page_title="EB2 NIW Green Card Timeline", layout="wide")
st.title("EB2 NIW Green Card Timeline Simulator")

# --------------------------------------------------
# USER INPUT: Country & Visa Bulletin Dates
# --------------------------------------------------
st.header("Visa Bulletin Setup")
st.markdown("Get current dates from: https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html")
country = st.selectbox("Country of Chargeability (EB-2)", ["Rest of World", "China", "India"])
st.subheader(f"EB-2 {country} Visa Bulletin Dates")
filing_cutoff = st.date_input("Date for Filing (I-485 eligibility)", value=date(2024,4,1))
final_cutoff = st.date_input("Final Action Date (Green Card approval)", value=date(2024, 10,1))

# --------------------------------------------------
# USER INPUTS: NIW & I-140
# --------------------------------------------------
st.header("1️⃣ NIW Preparation")
niw_start = st.date_input("NIW Preparation Start Date", value=date(2026,2,1))
letters_months = st.number_input("Recommendation Letters Preparation", 0.0, 3.0, 1.0)
petition_months = st.number_input("I-140 Petition Drafting", 0.0, 2.0, 1.0)

# I-140 filing by user
st.header("2️⃣ I-140 Filing & Approval")
i140_user_filed = st.date_input("I-140 Filing Date (Priority Date)", value=niw_start + timedelta(days=int((letters_months + petition_months) * 30)))
i140_approval_months = st.number_input("Expected I-140 Approval Time (months)", 1.0, 24.0, 6.0)
premium = st.checkbox("Premium Processing (15 days)")

rfe_toggle = st.checkbox("I-140 RFE Issued?")
if rfe_toggle:
    rfe_response_months = st.number_input("RFE Response Preparation Time", 0.0, 12.0, 2.0)
    rfe_review_months = st.number_input("USCIS Review After RFE", 0.0, 12.0, 3.0)
else:
    rfe_response_months = 0.0
    rfe_review_months = 0.0

# --------------------------------------------------
# USER INPUTS: Adjustment of Status
# --------------------------------------------------
st.header("3️⃣ Adjustment of Status")
i485_processing_months = st.number_input("I-485 Processing Time", 6.0, 22.0, 8.0)
ead_months = st.number_input("EAD/AP Processing Time", 1.0, 12.0, 4.0)

# --------------------------------------------------
# CALCULATIONS
# --------------------------------------------------
if niw_start:

    # Convert months to days
    letters_days = int(letters_months * 30)
    petition_days = int(petition_months * 30)
    i140_days = int(i140_approval_months * 30)
    rfe_response_days = int(rfe_response_months * 30)
    rfe_review_days = int(rfe_review_months * 30)
    i485_days = int(i485_processing_months * 30)
    ead_days = int(ead_months * 30)

    # Preparation Phase
    letters_done = niw_start + timedelta(days=letters_days)
    petition_ready = letters_done + timedelta(days=petition_days)

    # I-140 Filing and Priority Date
    i140_filed = i140_user_filed
    priority_date = i140_filed

    # I-140 Approval
    if premium:
        i140_approved = i140_filed + timedelta(days=15)
    else:
        i140_approved = i140_filed + timedelta(days=i140_days)

    if rfe_toggle:
        rfe_issued = i140_filed + timedelta(days=i140_days // 2)
        rfe_response = rfe_issued + timedelta(days=rfe_response_days)
        i140_approved = rfe_response + timedelta(days=rfe_review_days)

    # -------------------------
    # I-485 Filing Eligibility
    # -------------------------
    if priority_date <= filing_cutoff:
        i485_eligible_date = i140_approved
    else:
        backlog_wait_days = (priority_date - filing_cutoff).days
        i485_eligible_date = i140_approved + timedelta(days=backlog_wait_days)

    # -------------------------
    # Final Action Eligibility
    # -------------------------
    if priority_date <= final_cutoff:
        final_action_date = i485_eligible_date
    else:
        backlog_wait_days_final = (priority_date - final_cutoff).days
        final_action_date = i485_eligible_date + timedelta(days=backlog_wait_days_final)

    # EAD + Green Card
    ead_received = i485_eligible_date + timedelta(days=ead_days)
    gc_received = final_action_date + timedelta(days=i485_days)

    # -------------------------
    # Milestones Table
    # -------------------------
    milestones = [
        ("NIW Preparation Started", niw_start),
        ("Letters Completed", letters_done),
        ("I-140 Filed (Priority Date)", priority_date),
        ("I-140 Approved", i140_approved),
        ("I-485 Eligible to File", i485_eligible_date),
        ("EAD/AP Received", ead_received),
        ("Final Action Current", final_action_date),
        ("Green Card Approved", gc_received)
    ]
    df = pd.DataFrame(milestones, columns=["Milestone", "Date"])
    st.header("📅 Key Milestones")
    st.dataframe(df)
    
    # -------------------------
    # Timeline Chart with Colors
    # -------------------------
    timeline_data = [
        ("Preparation Phase", niw_start, petition_ready),
        ("I-140 Pending", i140_filed, i140_approved),
        ("Backlog Wait", i140_approved, i485_eligible_date),
        ("I-485 Pending", i485_eligible_date, gc_received),
        ("Green Card Received", gc_received, gc_received + timedelta(days=15)),
    ]
    
    timeline_df = pd.DataFrame(timeline_data, columns=["Stage", "Start", "End"])
    
    # Define custom colors
    color_map = {
        "Preparation Phase": "blue",
        "I-140 Pending": "orange",
        "Backlog Wait": "salmon",
        "I-485 Pending": "orange",
        "Green Card Received": "green"
    }
    
    st.header("📊 Case Timeline")
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="End",
        y="Stage",
        color="Stage",
        color_discrete_map=color_map
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


    # -------------------------
    # Summary
    # -------------------------
    total_days = (gc_received - niw_start).days
    total_years = round(total_days / 365, 2)
    st.success(f"Estimated Total Time to Green Card: {total_days} days (~{total_years} years)")
    st.info(
        f"Visa Bulletin Used for {country}:\n"
        f"Date for Filing: {filing_cutoff}\n"
        f"Final Action: {final_cutoff}\n"
        f"I-140 Filing Date: {i140_filed}\n"
        f"Expected I-140 Approval: {i140_approved}"
    )
