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

with left:
    st.subheader("Patient Intake Form")

    with st.form("intake_form", clear_on_submit=False):
        st.markdown("### Basics")
        age = st.number_input("Age", min_value=0, max_value=120, value=30, step=1)
        sex_at_birth = st.selectbox("Sex at birth", ["Female", "Male", "Intersex", "Prefer not to say"])
        height = st.text_input("Height (optional)", placeholder="e.g., 5'6\" or 168 cm")
        weight = st.text_input("Weight (optional)", placeholder="e.g., 160 lb or 73 kg")

        st.markdown("### Visit Context")
        reason_for_visit = st.text_area(
            "What is the main reason for your visit today?",
            placeholder="Describe your concern in your own words.",
            height=120
        )
        symptom_start = st.text_input("When did this concern start?", placeholder="e.g., 3 days ago / 2 months ago")
        symptom_trend = st.selectbox("Is it getting better, worse, or unchanged?", SYMPTOM_TREND_OPTIONS)

        st.markdown("### Medical History")
        conditions = st.multiselect("Do you have any diagnosed medical conditions?", COMMON_CONDITIONS)
        other_conditions = ""
        if "Other" in conditions:
            other_conditions = st.text_input("If other, list conditions", placeholder="e.g., migraine, IBS")

        medications = st.text_area("What medications are you currently taking?", placeholder="List meds + dose if known.", height=90)

        has_allergies = st.selectbox("Do you have any allergies?", YESNO)
        allergies = ""
        if has_allergies == "Yes":
            allergies = st.text_area("List allergies (medications/foods/other)", height=80)

        st.markdown("### Social History")
        smoking = st.selectbox("Do you currently smoke or vape?", ["No", "Yes - smoke", "Yes - vape", "Yes - both"])
        alcohol = st.selectbox("How often do you drink alcohol?", ALCOHOL_OPTIONS)
        drugs = st.selectbox("Do you use recreational drugs?", YESNO)

        st.markdown("### Anything Else")
        additional_notes = st.text_area(
            "Is there anything else you want your clinician to know before the visit?",
            placeholder="Optional",
            height=90
        )

        submitted = st.form_submit_button("Generate Intake JSON")

    if submitted:
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

        st.success("Payload created.")
        st.json(payload)

with right:
    st.subheader("Clinician Summary (Next Step)")
    st.info("Once the JSON is stable, we’ll add the LLM call and render the summary here.")
