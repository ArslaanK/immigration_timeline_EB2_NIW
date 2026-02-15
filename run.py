import plotly.express as px
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import requests
from io import StringIO


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_latest_visa_bulletin_url():
    base = "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin"
    today = date.today()

    for i in [1, 0]:
        target = today.replace(day=1) + timedelta(days=32 * i)

        month_name = target.strftime("%B").lower()
        year = target.year

        url = f"{base}/{year}/visa-bulletin-for-{month_name}-{year}.html"
        r = requests.get(url)

        if r.status_code == 200:
            return url, month_name.capitalize(), year

    return None, None, None


def parse_visa_date(val):

    if pd.isna(val):
        return None

    # already date/datetime
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()

    if isinstance(val, date):
        return val

    val = str(val).strip()

    if val == "C":
        return date.today()

    if val == "U":
        return None

    return datetime.strptime(val, "%d%b%y").date()


def normalize_df(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("\xa0", "", regex=False)
        .str.upper()
    )

    df.index = (
        df.index.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("\xa0", "", regex=False)
        .str.upper()
    )

    return df


# --------------------------------------------------
# Scraper
# --------------------------------------------------

def scrape_visa_bulletin(url, country, eb_type):

    response = requests.get(url)
    tables = pd.read_html(StringIO(response.text))

    employment_tables = []

    for table in tables:
        if len(table) > 2:
            first_row = table.iloc[0].astype(str)
            if first_row.str.contains("Employment", case=False, na=False).any():
                employment_tables.append(table)

    if len(employment_tables) < 2:
        st.error("Employment tables not found")
        return None, None

    action_df = employment_tables[1]
    filing_df = employment_tables[0]

    action_df.columns = action_df.iloc[0]
    filing_df.columns = filing_df.iloc[0]

    action_df = action_df.iloc[1:].set_index(action_df.columns[0])
    filing_df = filing_df.iloc[1:].set_index(filing_df.columns[0])

    action_df = normalize_df(action_df)
    filing_df = normalize_df(filing_df)

    country_dict = {
        "Rest of World": "ALL CHARGEABILITY AREAS EXCEPT THOSE LISTED",
        "CHINA": "CHINA- MAINLAND BORN",
        "INDIA": "INDIA",
        "MEXICO": "MEXICO",
        "PHILIPPINES": "PHILIPPINES",
    }

    eb_dict = {
        "EB-1": "1ST",
        "EB-2": "2ND",
        "EB-3": "3RD"
    }

    country_id = country_dict[country].upper()
    eb_id = eb_dict[eb_type]

    try:
        f_date = parse_visa_date(filing_df.loc[eb_id, country_id])
        a_date = parse_visa_date(action_df.loc[eb_id, country_id])
    except KeyError:
        st.error("Column mismatch after normalization")
        st.write(filing_df.columns)
        st.write(filing_df.index)
        return None, None

    return f_date, a_date


# --------------------------------------------------
# UI
# --------------------------------------------------

st.set_page_config(page_title="Green Card Timeline", layout="wide")
st.title("Green Card Timeline Simulator")



# --------------------------------------------------
# USER INPUTS: NIW & I-140
# --------------------------------------------------
st.header("Case Preparation")
niw_start = st.date_input("Case Preparation Start Date ", value=date(2026,2,1))
letters_months = st.number_input("Recommendation Letters Preparation (months) [if applicable]", 0.0, 3.0, 0.0)
petition_months = st.number_input("I-140 Petition Drafting (months)", 0.0, 2.0, 1.0)
premium = st.checkbox("Filling Premium?")

i140_approval_months = 4
rfe_toggle = st.checkbox("Expect I-140 RFE?")

if rfe_toggle:
    rfe_response_months = 2.0
    rfe_review_months = 3.0
else:
    rfe_response_months = 0.0
    rfe_review_months = 0.0

# --------------------------------------------------
# USER INPUTS: Adjustment of Status
# --------------------------------------------------
st.header("Adjustment of Status")
i485_processing_months = st.number_input("I-485 Processing Time (months)", 6.0, 22.0, 8.0)
ead_months = st.number_input("EAD/AP Processing Time (months)", 1.0, 12.0, 4.0)


# --------------------------------------------------
# USER INPUTS: Adjustment of Status
# --------------------------------------------------
st.header("VISA CLASS")
country = st.selectbox(
    "Country of Chargeability",
    ["Rest of World", "CHINA", "INDIA", "MEXICO", "PHILIPPINES"]
)

eb_type = st.selectbox(
    "Preference",
    ["EB-1", "EB-2", "EB-3"],
    index=["EB-1", "EB-2", "EB-3"].index("EB-2")
)


i140_user_filed = st.date_input("I-140 Priority Date", value=date.today())


if "filing_cutoff" not in st.session_state:
    st.session_state.filing_cutoff = None
    st.session_state.final_cutoff = None

url, bulletin_month, bulletin_year = get_latest_visa_bulletin_url()

#if st.button("Fetch Latest Visa Bulletin Dates"):

if url:
    st.info(f"Using Visa Bulletin: {bulletin_month} {bulletin_year}")

    f, a = scrape_visa_bulletin(url, country, eb_type)

    st.session_state.filing_cutoff = a
    st.session_state.final_cutoff = f

    #st.success("Visa Bulletin Retrieved")

st.write("📌 USCIS Filing Date:", st.session_state.filing_cutoff)
st.write("📌 USCIS Final Action Date:", st.session_state.final_cutoff)


# --------------------------------------------------
# Priority Date Check
# --------------------------------------------------


filing_cutoff = st.session_state.filing_cutoff
final_cutoff = st.session_state.final_cutoff

if filing_cutoff:

    if i140_user_filed > filing_cutoff:
        backlog_days = (i140_user_filed - filing_cutoff).days
        backlog_days_decision = (i140_user_filed - final_cutoff).days
        
        reg_i140_decision = i140_user_filed + timedelta(days=8*30)
        prem_i140_decision = i140_user_filed + timedelta(days=45)
        st.write("Average processing time: 8 months or 45 days with premium processing")
        st.write(f"📌 Expected I-140 decision [regular]: {reg_i140_decision}")
        st.write(f"📌 Expected I-140 decision [premium]: {prem_i140_decision}")
        st.write(f"📌 Change of Status in Backlog [Filling]: {backlog_days/30:.1f} months")
        st.write(f"📌 Change of Status in Backlog [Decision]: {backlog_days_decision/30:.1f} months")
        st.warning("Change of Status cannot be submitted.")
        st.warning(f"Change of Status can be filed on {date.today()+timedelta(days=backlog_days_decision)}")
        
        green_card_decision = date.today() +  timedelta(days=backlog_days) + timedelta(days=8*30)
        
        #st.warning(f"Expect green card: {green_card_decision}")
        
        
        
    else:
        st.success("Priority Date is current for filing.")
        backlog_days = (i140_user_filed - filing_cutoff).days
        backlog_days_decision = (i140_user_filed - final_cutoff).days
        reg_i140_decision = i140_user_filed + timedelta(days=8*30)
        prem_i140_decision = i140_user_filed + timedelta(days=45)
        st.write(f"📌 Expected I-140 decision [regular]: {reg_i140_decision}")
        st.write(f"📌 Expected I-140 decision [premium]: {prem_i140_decision}")
        st.write(f"📌 Change of Status in Backlog [Filling]: {backlog_days/30:.1f} months")
        st.write(f"📌 Change of Status in Backlog [Decision]: {backlog_days_decision/30:.1f} months")
        
        st.success("Change of Status can be submitted.")
        st.success(f"Change of Status can be filed on {date.today()+timedelta(days=backlog_days_decision)}")
        
        green_card_decision = final_cutoff +  timedelta(days=backlog_days) + timedelta(days=8*30)
        
        #st.warning(f"Expect green card: {green_card_decision}")
        
# -------------------------
# CALCULATIONS (Corrected for Backlog)
# -------------------------
if niw_start:

    # Convert months to days
    letters_days = int(letters_months * 30)
    petition_days = int(petition_months * 30)
    i140_days = int(i140_approval_months * 30)
    rfe_response_days = int(rfe_response_months * 30)
    rfe_review_days = int(rfe_review_months * 30)
    i485_days = int(i485_processing_months * 30)
    ead_days = int(ead_months * 30)

    # -------------------------
    # NIW Preparation Phase
    # -------------------------
    letters_done = niw_start + timedelta(days=letters_days)
    petition_ready = letters_done + timedelta(days=petition_days)

    # -------------------------
    # I-140 Filing and Approval
    # -------------------------
    i140_filed = i140_user_filed
    priority_date = i140_filed

    if premium:
        i140_approved = i140_filed + timedelta(days=45)
    else:
        i140_approved = i140_filed + timedelta(days=i140_days)

    if rfe_toggle:
        rfe_issued = i140_filed + timedelta(days=i140_days // 2)
        rfe_response = rfe_issued + timedelta(days=rfe_response_days)
        i140_approved = rfe_response + timedelta(days=rfe_review_days)

    # -------------------------
    # Backlog Calculations
    # -------------------------
    backlog_filing_days = max(0, (priority_date - filing_cutoff).days)
    backlog_final_days = max(0, (priority_date - final_cutoff).days)

    # -------------------------
    # I-485 Eligibility (cannot file before backlog clears)
    # -------------------------
    i485_eligible_date = i140_approved + timedelta(days=backlog_filing_days)

    # -------------------------
    # Final Action / Green Card
    # -------------------------
    final_action_date = i485_eligible_date + timedelta(days=backlog_final_days)
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
    # Timeline Chart
    # -------------------------
    timeline_data = [
        ("Preparation Phase", niw_start, petition_ready),
        ("I-140 Pending", i140_filed, i140_approved),
        ("Backlog Wait", i140_approved, i485_eligible_date),
        ("I-485 Pending", i485_eligible_date, gc_received),
        ("EAD/AP card", i485_eligible_date, ead_received),
        ("Green Card Received", gc_received, gc_received + timedelta(days=15)),
    ]
    timeline_df = pd.DataFrame(timeline_data, columns=["Stage", "Start", "End"])

    color_map = {
        "Preparation Phase": "blue",
        "I-140 Pending": "orange",
        "Backlog Wait": "salmon",
        "I-485 Pending": "orange",
        "EAD/AP card": "cyan",
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




