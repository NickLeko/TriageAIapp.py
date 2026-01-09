import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="TriageAI MVP", layout="wide")

# ----------------------------
# Top-Level Disclaimer Banner
# ----------------------------
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

# ----------------------------
# OpenAI client
# ----------------------------
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
    "Assume all information is patient-reported and unverified."
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
                "social_history_flags": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "reason_for_visit",
                "duration",
                "symptom_trend",
                "past_medical_history",
                "medications",
                "allergies",
                "social_history_flags",
            ],
            "additionalProperties": False,
        },
        "items_to_clarify": {"type": "array", "items": {"type": "string"}},
        "data_quality_notes": {"type": "array", "items": {"type": "string"}},
        "disclaimer": {"type": "string"},
    },
    "required": [
        "clinical_summary",
        "structured_data",
        "items_to_clarify",
        "data_quality_notes",
        "disclaimer",
    ],
    "additionalProperties": False,
}

@st.cache_data(show_spinner=False)
def generate_clinician_summary(payload: dict) -> dict:
    client = get_client()

    response = client.responses.create(
        model="gpt-4o-mini",  # Updated to current common cheap/strong model
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Return ONLY valid JSON that matches the provided schema. "
                    "Summarize this intake payload:\n\n"
                    f"{json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "clinician_summary",
                "strict": True,
                "schema": CLINICIAN_SUMMARY_SCHEMA,
            }
        },
    )

    raw = response.output_text
    return json.loads(raw)

# ----------------------------
# Common options
# ----------------------------
COMMON_CONDITIONS = [
    "Hypertension", "Diabetes", "Asthma", "Depression/Anxiety",
    "Hypothyroidism", "Hyperlipidemia", "GERD", "COPD",
    "Chronic kidney disease", "Other"
]
ALCOHOL_OPTIONS = ["None", "Occasional", "Weekly", "Daily"]
SYMPTOM_TREND_OPTIONS = ["Better", "Worse", "Unchanged", "Fluctuating", "Not sure"]
YESNO = ["No", "Yes"]

# ----------------------------
# Layout
# ----------------------------
left, right = st.columns([1, 1], gap="large")

payload = {}
with left:
    st.subheader("Patient Intake Form")

    with st.form("intake_form", clear_on_submit=False):
        # Consent checkbox (required)
        consent = st.checkbox(
            "I understand this is a prototype for demonstration purposes only and does not provide medical advice.",
            value=False
        )

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

        submitted = st.form_submit_button("Generate Clinician Summary")

        # Build payload
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
    st.subheader("Clinician Summary")

    if not submitted:
        st.info("Fill the form, acknowledge the disclaimer, and click **Generate Clinician Summary**.")
    else:
        if not consent:
            st.error("Please acknowledge the disclaimer checkbox before generating a summary.")
        elif not payload.get("reason_for_visit"):
            st.error("Please enter the main reason for visit before generating a summary.")
        else:
            st.caption("Intake payload (debug)")
            with st.expander("View raw payload"):
                st.json(payload)

            with st.spinner("Generating clinician summary..."):
                try:
                    summary = generate_clinician_summary(payload)

                    # Build full markdown summary for download
                    full_markdown = f"""
# TriageAI Pre-Visit Summary

### Clinical Summary
{summary["clinical_summary"]}

### Structured Data
```json
{json.dumps(summary["structured_data"], indent=2)}
