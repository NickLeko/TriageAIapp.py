import streamlit as st

st.set_page_config(page_title="TriageAI MVP", layout="wide")
st.title("TriageAI — Primary Care Pre-Visit Intake (MVP)")

COMMON_CONDITIONS = [
    "Hypertension", "Diabetes", "Asthma", "Depression/Anxiety",
    "Hypothyroidism", "Hyperlipidemia", "GERD", "COPD",
    "Chronic kidney disease", "Other"
]
ALCOHOL_OPTIONS = ["None", "Occasional", "Weekly", "Daily"]
SYMPTOM_TREND_OPTIONS = ["Better", "Worse", "Unchanged", "Fluctuating", "Not sure"]
YESNO = ["No", "Yes"]

left, right = st.columns([1, 1], gap="large")

# Initialize defaults so variables exist before submit
payload = {}

with left:
    st.subheader("Patient Intake Form")

    with st.form("intake_form", clear_on_submit=False):
        submitted = st.form_submit_button("Generate Intake JSON")

        with st.expander("Basics", expanded=True):
            age = st.number_input("Age", min_value=0, max_value=120, value=25, step=1)
            sex_at_birth = st.selectbox("Sex at birth", ["Female", "Male", "Intersex", "Prefer not to say"])
            height = st.text_input("Height (optional)", placeholder="e.g., 5'6\" or 168 cm")
            weight = st.text_input("Weight (optional)", placeholder="e.g., 160 lb or 73 kg")

        with st.expander("Visit Context", expanded=True):
            reason_for_visit = st.text_area(
                "What is the main reason for your visit today?",
                placeholder="Describe your concern in your own words.",
                height=100
            )
            symptom_start = st.text_input("When did this concern start?", placeholder="e.g., 3 days ago / 2 months ago")
            symptom_trend = st.selectbox("Is it getting better, worse, or unchanged?", SYMPTOM_TREND_OPTIONS)

        with st.expander("Medical History", expanded=False):
            conditions = st.multiselect("Diagnosed medical conditions", COMMON_CONDITIONS)
            other_conditions = ""
            if "Other" in conditions:
                other_conditions = st.text_input("If other, list conditions", placeholder="e.g., migraine, IBS")
            medications = st.text_area("Current medications", placeholder="List meds + dose if known.", height=80)
            has_allergies = st.selectbox("Any allergies?", YESNO)
            allergies = ""
            if has_allergies == "Yes":
                allergies = st.text_area("List allergies", height=70)

        with st.expander("Social History", expanded=False):
            smoking = st.selectbox("Do you currently smoke or vape?", ["No", "Yes - smoke", "Yes - vape", "Yes - both"])
            alcohol = st.selectbox("How often do you drink alcohol?", ALCOHOL_OPTIONS)
            drugs = st.selectbox("Do you use recreational drugs?", YESNO)

        with st.expander("Anything Else", expanded=False):
            additional_notes = st.text_area(
                "Anything else you want your clinician to know?",
                placeholder="Optional",
                height=80
            )

        # Normalize PMH
        pmh = [c for c in conditions if c != "Other"]
        if other_conditions.strip():
            pmh.append(other_conditions.strip())

        payload = {
            "age": str(age),
            "sex_at_birth": sex_at_birth,
            "height": height.strip(),
            "weight": weight.strip(),
            "reason_for_visit": reason_for_visit.strip(),
            "symptom_start": symptom_start.strip(),
            "symptom_trend": symptom_trend,
            "conditions": pmh,
            "medications": medications.strip(),
            "allergies": allergies.strip() if has_allergies == "Yes" else "",
            "smoking": smoking,
            "alcohol": alcohol,
            "drugs": drugs,
            "additional_notes": additional_notes.strip()
        }

with right:
    st.subheader("Clinician Summary (Next Step)")

    if submitted:
        st.success("Intake JSON generated")
        st.json(payload)
    else:
        st.info("Fill the form and click **Generate Intake JSON**.")

