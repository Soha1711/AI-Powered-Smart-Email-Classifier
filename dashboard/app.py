import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import random
from datetime import datetime
from fpdf import FPDF
import io

def create_pdf_report(df):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(77, 166, 255) # Match app blue
    pdf.cell(0, 15, "EmailIntel AI Intelligence Report", ln=True, align="C")
    pdf.ln(5)
    
    # Date
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="R")
    pdf.ln(10)
    
    # Summary Metrics
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 12)
    
    total = len(df)
    complaints = len(df[df['category'] == 'complaint'])
    top_cat = df['category'].mode()[0].title() if not df.empty else "N/A"
    
    stats = [
        f"Total Emails Analyzed: {total}",
        f"Active Complaints: {complaints}",
        f"Primary Category: {top_cat}"
    ]
    
    for stat in stats:
        pdf.cell(0, 8, f" - {stat}", ln=True)
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(45, 10, "Sender", border=1, fill=True)
    pdf.cell(75, 10, "Subject", border=1, fill=True)
    pdf.cell(35, 10, "Category", border=1, fill=True)
    pdf.cell(35, 10, "Urgency", border=1, fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Helvetica", "", 10)
    for index, row in df.head(20).iterrows(): # Show top 20
        sender = str(row['sender']).encode('latin-1', 'replace').decode('latin-1')[:20]
        subj = str(row['subject']).encode('latin-1', 'replace').decode('latin-1')[:35]
        cat = str(row['category'])
        urg = str(row['urgency'])
        
        pdf.cell(45, 10, sender, border=1)
        pdf.cell(75, 10, subj, border=1)
        pdf.cell(35, 10, cat, border=1)
        pdf.cell(35, 10, urg, border=1)
        pdf.ln()
        
    return bytes(pdf.output())


import os
API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Email Classifier", layout="wide", initial_sidebar_state="collapsed")


# ===== BASE CSS (Always Applied) =====
st.markdown("""
<style>
/* Base container spacing */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 95%;
}

/* Header Styling */
.title-text {
    font-size: 32px;
    font-weight: 800;
    padding-bottom: 10px;
    margin-bottom: 20px;
    border-bottom: 1px solid #333;
}

/* Card layout for spacing out elements */
.card {
    padding: 22px;
    border-radius: 14px;
    margin-bottom: 15px;
}

/* Hide sidebar navigation completely */
[data-testid="stSidebar"] {
    display: none;
}

/* Tabs styling */
[data-baseweb="tab-list"] {
    gap: 15px;
    background-color: transparent !important;
}
[data-baseweb="tab"] {
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
    background-color: transparent;
}


/* Mobile Responsiveness Improvements */
@media screen and (max-width: 768px) {
    .block-container {
        padding-top: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .title-text {
        font-size: 26px !important;
        text-align: center;
    }
    .card {
        padding: 15px !important;
    }
    [data-baseweb="tab-list"] {
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 5px;
        -webkit-overflow-scrolling: touch;
    }
}
</style>
""", unsafe_allow_html=True)


# ===== BADGE FORMAT =====
def badge(cat, urg):
    if cat == "complaint": cat_badge = f"🟥 {cat}"
    elif cat == "request": cat_badge = f"🟦 {cat}"
    elif cat == "feedback": cat_badge = f"🟩 {cat}"
    else: cat_badge = f"⬛ {cat}"

    if urg == "high": urg_badge = f"🔴 {urg}"
    elif urg == "medium": urg_badge = f"🟡 {urg}"
    else: urg_badge = f"🟢 {urg}"

    return cat_badge, urg_badge


# ===== FETCH EMAILS =====
def fetch_emails():
    try:
        r = requests.get(f"{API_URL}/emails")
        if r.status_code == 200:
            st.session_state.emails = r.json().get("emails", [])
    except Exception:
        pass

def clear_emails_api():
    try:
        r = requests.delete(f"{API_URL}/emails")
        if r.status_code == 200:
            st.session_state.emails = []
            st.toast("Database cleared successfully!")
    except Exception as e:
        st.error(f"Error clearing data: {e}")


# ===== TEST DATA TEMPLATES =====
TEST_TEMPLATES = [
    {"sender": "customer1@gmail.com", "subject": "Late Delivery", "text": "My package was supposed to arrive 3 days ago but it is still not here. Please help!"},
    {"sender": "soha@infosys.com", "subject": "Access Request", "text": "Hi team, I need access to the internal AWS portal for the new project. Thanks."},
    {"sender": "user99@yahoo.com", "subject": "Great UI!", "text": "I really love the new dark mode design on the dashboard. It looks amazing and works very smoothly."},
    {"sender": "win-prize@spam.com", "subject": "YOU WON A GIFT!", "text": "Congratulations! You have been selected as the winner of a $500 Amazon Gift card. Response immediately to claim!"},
    {"sender": "angry-buyer@test.net", "subject": "Terrible Product", "text": "This product broke within 10 minutes of use. I want my money back immediately and will be leaving a one-star review."},
    {"sender": "partner@consultancy.com", "subject": "Meeting Invite", "text": "Hello, I would like to schedule a quick sync to discuss the upcoming partnership strategy for Q3."},
]

# ===== SESSION STATE =====
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

if "emails" not in st.session_state:
    st.session_state.emails = []
    fetch_emails()

if "input_sender" not in st.session_state:
    st.session_state.input_sender = ""
if "input_subject" not in st.session_state:
    st.session_state.input_subject = ""
if "input_text" not in st.session_state:
    st.session_state.input_text = ""


# ===== BACKEND CALL =====
def classify(sender, subject, text):
    try:
        r = requests.post(f"{API_URL}/predict", json={
            "sender": sender,
            "subject": subject,
            "text": text
        })
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error(f"Backend Error: {e}")
        return None


# ===== MAIN APPLICATION =====
def main():
    
    # --- HEADER & TOGGLE ---
    hA, hB = st.columns([5, 1])
    with hA:
        st.markdown("<div class='title-text'>EmailIntel AI</div>", unsafe_allow_html=True)
    with hB:
        st.markdown("<br>", unsafe_allow_html=True)
        # Checkbox behaves similar to a toggle switch
        is_dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_toggle")

        # Update session state if changed
        if is_dark != st.session_state.dark_mode:
            st.session_state.dark_mode = is_dark
            st.rerun()

    # --- DYNAMIC THEME CSS INJECTION ---
    plotly_font_color = "white"
    plotly_bg_color = "rgba(0,0,0,0)"

    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp { background: #121212; }
        .title-text { color: #4da6ff; border-bottom: 1px solid #333; }
        .card { background: #1e1e24; border: 1px solid #333333; color: #fafafa; }
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div { background-color: #2b2b36; border-color: #444; }
        div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea { color: #fafafa !important; }
        [data-testid="stMetricValue"] { color: #fafafa !important; }
        [data-testid="stMetricLabel"] { color: #a1a1a1 !important; }
        div[data-baseweb="popover"] { background-color: #1e1e24 !important; }
        </style>
        """, unsafe_allow_html=True)
        plotly_font_color = "white"
        plotly_bg_color = "rgba(0,0,0,0)"
    else:
        st.markdown("""
        <style>
        .stApp { background: #f8f9fa !important; }
        .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp label, .stMarkdownContainer p { color: #212529 !important; }
        .title-text { color: #0d6efd !important; border-bottom: 1px solid #dee2e6; }
        .card { background: #ffffff !important; border: 1px solid #dee2e6 !important; color: #212529 !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div { background-color: #ffffff !important; border-color: #ced4da !important; }
        div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, div[data-baseweb="select"] span, div[data-baseweb="select"] div { color: #212529 !important; }
        [data-testid="stMetricValue"] { color: #212529 !important; }
        [data-testid="stMetricLabel"] { color: #6c757d !important; }
        thead tr th { color: #212529 !important; }
        tbody tr td { color: #212529 !important; }
        div[data-baseweb="popover"] > div { background-color: #ffffff !important; }
        ul[role="listbox"] { background-color: #ffffff !important; padding: 0 !important; }
        li[role="option"] { background-color: #ffffff !important; color: #212529 !important; }
        li[role="option"]:hover { background-color: #f0f2f6 !important; }
        /* Fix Buttons and Tabs */
        .stButton > button { background-color: #ffffff !important; border: 1px solid #ced4da !important; color: #212529 !important; }
        .stButton > button * { color: #212529 !important; }
        .stDownloadButton > button { background-color: #ffffff !important; border: 1px solid #ced4da !important; color: #212529 !important; }
        .stDownloadButton > button * { color: #212529 !important; }
        button[data-baseweb="tab"] p { color: #212529 !important; }
        </style>
        """, unsafe_allow_html=True)
        plotly_font_color = "black"
        plotly_bg_color = "rgba(255,255,255,1)"


    # --- RESPONSIVE TABS NAVIGATION ---
    tab_dash, tab_class, tab_inbox, tab_set = st.tabs(["📊 Dashboard", "🔍 Classify", "📥 Inbox", "⚙️ Settings"])

    # === T1: DASHBOARD ===
    with tab_dash:
        fetch_emails()
        df = pd.DataFrame(st.session_state.emails)

        if not df.empty:
            complaints_count = len(df[df['category'] == 'complaint'])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Emails", len(df))
            c2.metric("Top Category", df["category"].mode()[0].title())
            c3.metric("Most Urgent", df["urgency"].mode()[0].title())
            c4.metric("Complaints", complaints_count)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df, x="category", title="Category Distribution", color_discrete_sequence=['#4da6ff' if st.session_state.dark_mode else '#0d6efd'])
                fig.update_layout(paper_bgcolor=plotly_bg_color, plot_bgcolor=plotly_bg_color, font_color=plotly_font_color)
                st.plotly_chart(fig, use_container_width=True, theme=None)
            with col2:
                fig2 = px.pie(df, names="urgency", title="Urgency Levels", color_discrete_sequence=px.colors.sequential.RdBu)
                fig2.update_layout(paper_bgcolor=plotly_bg_color, plot_bgcolor=plotly_bg_color, font_color=plotly_font_color)
                st.plotly_chart(fig2, use_container_width=True, theme=None)

            # Trends
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            trends_df = df.groupby('date').size().reset_index(name='count')
            
            tcol1, tcol2 = st.columns([3, 1])
            with tcol1:
                st.markdown("### Email Trends")
            with tcol2:
                # PDF Download Button
                pdf_data = create_pdf_report(df)
                st.download_button(
                    label="📥 Export Report (PDF)",
                    data=pdf_data,
                    file_name=f"email_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            fig3 = px.line(trends_df, x='date', y='count', title="Emails Over Time", markers=True)
            fig3.update_layout(paper_bgcolor=plotly_bg_color, plot_bgcolor=plotly_bg_color, font_color=plotly_font_color)
            st.plotly_chart(fig3, use_container_width=True, theme=None)
        else:
            st.info("No emails classified yet. Go to '🔍 Classify' to start testing!")

    # === T2: CLASSIFY ===
    with tab_class:
        t1, t2 = st.columns([3, 1])
        with t1:
            st.markdown("### AI Email Classification")
        with t2:
            if st.button("🧪 Random Case", use_container_width=True):
                tpl = random.choice(TEST_TEMPLATES)
                st.session_state.input_sender = tpl["sender"]
                st.session_state.input_subject = tpl["subject"]
                st.session_state.input_text = tpl["text"]
                st.rerun()

        sender = st.text_input("Sender", value=st.session_state.input_sender)
        subject = st.text_input("Subject", value=st.session_state.input_subject)
        text = st.text_area("Email Content", height=200, value=st.session_state.input_text)

        if st.button("🚀 Analyze Email", use_container_width=True, type="primary"):
            if not sender or not text:
                st.warning("Please fill in the required fields.")
            else:
                res = classify(sender, subject, text)
                if res:
                    cat = res.get("category", "")
                    urg = res.get("urgency", "")
                    cat_badge, urg_badge = badge(cat, urg)
                    
                    st.session_state.emails.insert(0, res)
                    st.success("Analysis Complete!")
                    st.info(f"Category: {cat_badge} | Urgency: {urg_badge}")
                    
                    st.session_state.input_sender = ""
                    st.session_state.input_subject = ""
                    st.session_state.input_text = ""

    # === T3: INBOX ===
    with tab_inbox:
        fetch_emails()
        st.markdown("### Live Email Feed")
        df = pd.DataFrame(st.session_state.emails)

        if df.empty:
            st.info("No emails in database.")
        else:
            f1, f2 = st.columns(2)
            priorities = ["All"] + list(df['urgency'].unique())
            selected_urgency = f1.selectbox("Priority Filter", priorities)
            
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            dates = ["All"] + sorted(list(df['date'].unique()))
            selected_date = f2.selectbox("Date Filter", dates)

            filtered_df = df.copy()
            if selected_urgency != "All":
                filtered_df = filtered_df[filtered_df['urgency'] == selected_urgency]
            if selected_date != "All":
                filtered_df = filtered_df[filtered_df['date'] == selected_date]

            if filtered_df.empty:
                st.warning("No matches found.")
            else:
                st.dataframe(
                    filtered_df[["sender", "subject", "category", "urgency", "timestamp"]],
                    use_container_width=True
                )

                st.markdown("---")
                s = st.selectbox("View Email Details", filtered_df.subject, key="inbox_selector")
                mail = filtered_df[filtered_df.subject == s].iloc[0]
                cat_badge, urg_badge = badge(mail.category, mail.urgency)

                st.markdown(f"""
                <div class='card'>
                <strong>From:</strong> {mail.sender}<br>
                <strong>Classification:</strong> {cat_badge} | {urg_badge}<br><br>
                <strong>Message:</strong><br>{mail.body}
                </div>
                """, unsafe_allow_html=True)

    # === T4: SETTINGS ===
    with tab_set:
        st.markdown("### ⚙️ System Settings")
        st.markdown("Manage database and system preferences.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🗑️ Clear Email Database", use_container_width=True, type="primary"):
            clear_emails_api()
            st.rerun()


if __name__ == "__main__":
    main()
