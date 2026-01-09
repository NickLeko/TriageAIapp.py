import json
import streamlit as st
from openai import OpenAI

# Add CSS for left column scrolling
st.markdown(
    """
    <style>
        [data-testid="column"]:nth-of-type(1) {
            overflow-y: auto;
            max-height: 80vh;  /* Adjust to 90vh or 100vh if needed for more space */
            padding-right: 10px;  /* Optional: scrollbar space */
        }
    </style>
    """,
    unsafe_allow_html=True
)

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
            {"role": "user", "content": f"Return ONLY valid JSON matching this schema exactly:\n{json.dumps(CLINICIAN_SUMMARY_SCHEMA, indent=2)}\n\n
