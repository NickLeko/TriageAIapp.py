import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="TriageAI MVP", layout="wide")

# Top-Level Disclaimer Banner
st.markdown(
    """
    <div style="background-color: #ffcccc; padding: 15px; border-radius: 10px; margin-bottom: 30px; border-left: 5px solid #ff0000;">
        <strong>🚨 IMPORTANT DISCLAIMER</strong><br>
        This is an <strong>educational prototype only</strong>. It is <strong>NOT medical advice, diagnosis, or treatment</strong>. 
        All outputs are AI-generated from user input and may contain errors or omissions. 
        Always consult a licensed healthcare provider for medical concerns.
    </div>
    """,
    unsafe_allow_html=True
)

st.title("TriageAI — Primary Care Pre-Visit Intake Summarizer (MVP)")

def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OPENAI_API_KEY in Streamlit Secrets.")
        st.stop()
    return OpenAI(api_key=api_key)

SYSTEM_INSTRUCTIONS = (
    "You are a clinical documentation assistant supporting primary care clinicians. "
    "Summarize patient-reported pre-visit intake information into concise, neutral, non-diagnostic clinical language. "
    "Do NOT provide medical advice, diagnoses, risk scores, or treatment recommendations. "
    "Do NOT add facts not provided. Flag missing/unclear details. "
    "Assume all information is patient-reported and unverified. "
    "Always include a disclaimer: 'This is AI-generated from patient-reported information and has not been verified by a clinician.'"
)

CLINICIAN_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "clinical_summary": {"type": "string"},
        "structured_data": {
            "type": "object",
            "properties": {
                "reason_for_visit": {"type": "string"},
                "duration": {"type": "string"},
                "symptom_trend": {"type": "string"},
                "past_medical_history": {"type": "array", "items": {"type": "string"}},
                "medications": {"type": "array", "items": {"type": "string"}},
                "allergies": {"type": "array", "items": {"type": "string"}},
                "social_history_flags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["reason_for_visit", "duration", "symptom_trend", "past_medical_history", "medications", "allergies", "social_history_flags"],
            "additionalProperties": False
        },
        "items_to_clarify": {"type": "array", "items": {"type": "string"}},
        "data_quality_notes": {"type": "array", "items": {"type": "string"}},
        "disclaimer": {"type": "string"}
    },
    "required": ["clinical_summary", "structured_data", "items_to_clarify", "data_quality_notes", "disclaimer"],
    "additionalProperties": False
}

@st.cache_data(show_spinner=False)
def generate_clinician_summary(payload: dict) -> dict:
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": f"Return ONLY valid JSON matching this schema exactly:\n{json.dumps(CLINICIAN_SUMMARY_SCHEMA, indent=2)}\n\nPayload:\n{json.dumps(payload, indent=2)}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)

# Options
COMMON_CONDITIONS = ["Hypertension", "Diabetes", "Asthma", "Depression/Anxiety", "Hypothyroidism", "Hyperlipidemia", "GERD", "COPD", "Chronic kidney disease", "Other"]
ALCOHOL_OPTIONS = ["None", "Occasional", "Weekly", "Daily"]
SYMPTOM_TREND_OPTIONS = ["Better", "Worse", "Unchanged", "Fluctuating", "Not sure"]
YESNO = ["No", "Yes"]

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Patient Intake Form")
    with st.form("intake_form"):
        consent = st.checkbox(
            "I understand this is a prototype for demonstration purposes only and does not provide medical advice.",
            value=False
        )

        with st.expander("Basics", expanded=True):
            age = st.number_input("Age", min_value=0, max_value=120, value=25)
            sex_at_birth = st.selectbox("Sex at birth", ["Female", "Male", "Intersex", "Prefer not to say"])
            height = st.text_input("Height (optional)", placeholder="e.g., 5'6\" or 168 cm")
            weight = st.text_input("Weight (optional)", placeholder="e.g., 160 lb or 73 kg")

        with st.expander("Visit Context", expanded=True):
            reason_for_visit = st.text_area("Main reason for visit today?", height=100)
            symptom_start = st.text_input("When did this start?", placeholder="e.g., 3 days ago")
            symptom_trend = st.selectbox("Symptom trend?", SYMPTOM_TREND_OPTIONS)

        with st.expander("Medical History", expanded=False):
            conditions = st.multiselect("Diagnosed conditions", COMMON_CONDITIONS)
            other_conditions = st.text_input("Other conditions" if "Other" in conditions else "")
            medications = st.text_area("Current medications", placeholder="List with doses if known", height=80)
            has_allergies = st.selectbox("Allergies?", YESNO)
            allergies = st.text_area("List allergies", height=70) if has_allergies == "Yes" else ""

        with st.expander("Social History", expanded=False):
            smoking = st.selectbox("Smoke or vape?", ["No", "Yes - smoke", "Yes - vape", "Yes - both"])
            alcohol = st.selectbox("Alcohol frequency?", ALCOHOL_OPTIONS)
            drugs = st.selectbox("Recreational drugs?", YESNO)

        with st.expander("Anything Else", expanded=False):
            additional_notes = st.text_area("Additional notes?", height=80)

        submitted = st.form_submit_button("Generate Summary")

        # Build payload
        pmh = [c for c in conditions if c != "Other"] + ([other_conditions.strip()] if other_conditions else [])
        payload = {
            "age": age,
            "sex_at_birth": sex
