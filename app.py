import streamlit as st
import requests

st.set_page_config(page_title="SOFTEC Copilot", layout="wide")

BACKEND_URL = "http://127.0.0.1:8000"

st.title("📧 Powerpuff Girls Inbox Copilot")


# =========================
# STUDENT PROFILE FORM
# =========================

st.header("Student Profile")

name = st.text_input("Name")
gpa = st.number_input("GPA", 0.0, 4.0, step=0.1)
degree = st.text_input("Degree")
semester = st.number_input("Semester", step=1)

skills = st.text_input("Skills (comma separated)")
interests = st.text_input("Interests (comma separated)")
preferences = st.text_input("Preferences (comma separated)")

financial_need = st.selectbox("Financial Need", ["low", "medium", "high"])
location = st.text_input("Location")

past_experiences = st.text_area("Past Experiences (comma separated)")


# =========================
# EMAIL FILE UPLOAD (NEW)
# =========================

st.header("Emails Input (Upload Files)")

uploaded_files = st.file_uploader(
    "Upload email files (.txt)",
    type=["txt"],
    accept_multiple_files=True
)

emails = []

if uploaded_files:
    for file in uploaded_files:
        content = file.read().decode("utf-8")

        emails.append({
            "subject": file.name,
            "body": content
        })


# =========================
# SUBMIT BUTTON
# =========================

if st.button("Analyze Opportunities"):

    profile = {
        "name": name,
        "gpa": gpa,
        "degree": degree,
        "semester": semester,
        "skills": [s.strip() for s in skills.split(",") if s],
        "interests": [i.strip() for i in interests.split(",") if i],
        "preferences": [p.strip() for p in preferences.split(",") if p],
        "financial_need": financial_need,
        "location": location,
        "past_experiences": [e.strip() for e in past_experiences.split(",") if e]
    }

    payload = {
        "profile": profile,
        "emails": emails
    }

    with st.spinner("Analyzing via backend..."):

        response = requests.post(
            f"{BACKEND_URL}/analyze",
            json=payload
        )

        if response.status_code != 200:
            st.error("Backend failed")
            st.write(response.text)
            st.stop()

        result = response.json()


    # =========================
    # DISPLAY RESULTS
    # =========================

    st.success("Analysis Complete!")
    st.header("🏆 Ranked Opportunities")

    opps = result.get("ranked_opportunities", [])

    if not opps:
        st.warning("No opportunities found")
    else:
        for item in opps:
            st.subheader(item.get("subject", "No Subject"))
            st.write("Score:", item.get("score"))
            st.write(item.get("reason"))
            st.divider()