import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="TriageAI MVP", layout="wide")
st.title("TriageAI — Primary Care Pre-Visit Intake (MVP)")

# ----------------------------
# OpenAI client (reads from Streamlit secrets)
# ----------------------------
def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error("Missing OPENAI_API_KEY in Streamlit Secrets.")
        st.stop()
    return OpenAI(apiKey=api_key)

# ----------------------------
# Strict JSON Schema for Structured Outputs
# ----------------------------
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

SYSTEM_INSTRUCTIONS = (
    "You are a clinical documentation assistant supporting primary care clinicians. "
    "Summarize patient-reported pre-visit intake into concise, neutral, non-diagnostic language. "
    "Do NOT provide medical advice, diagnoses, risk scores, or treatment recommendations. "
    "Do NOT add facts not provided. Flag missing/unclear info. Assume all info is patient-reported and unverified."
)

def generate_clinician_summary(payload: dict) -> dict:
    client = get_client()

    # We pass the payload as the "input" text (json string) to keep it simple.
    # Using Structured Outputs via text.format with json_schema. :contentReference[oaicite:4]{index=4}
    response = client.responses.create(
        model="gpt-5",  # you can change later; keep stable for MVP
        store=False,    # avoid retaining responses by default in this demo
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Summarize this primary care intake payload into the required JSON schema.\n\n"
                    f"INTAKE_PAYLOAD_JSON:\n{json.dumps(payload, ensure_ascii=False)}"
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

    # With Structured Outputs, output_text should be valid JSON that matches schema.
    raw = response.output_text
    return json.loads(raw)

# ----------------------------
# Intake form (your existing MVP)
# ----------------------------
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

        submitted = st.form_submit_button("Generate Clinician Summary")

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
        "additional_notes": additional_notes.strip(),
    }

    st.caption("Debug: intake payload")
    st.json(payload)

with right:
    st.subheader("Clinician Summary")

    if submitted:
        # Basic guardrails: don’t call model on empty core fields
        if not payload["reason_for_visit"]:
            st.error("Please fill in the main reason for visit before generating a summary.")
        else:
            with st.spinner("Generating summary..."):
                try:
                    summary = generate_clinician_summary(payload)
                    st.success("Generated.")
                    st.markdown("### Clinical Summary")
                    st.write(summary["clinical_summary"])

                    st.markdown("### Structured Data")
                    st.json(summary["structured_data"])

                    st.markdown("### Items to Clarify")
                    st.write(summary["items_to_clarify"])

                    st.markdown("### Data Quality Notes")
                    st.write(summary["data_quality_notes"])

                    st.caption(summary["disclaimer"])
                except Exception as e:
                    st.error("LLM call failed or returned unexpected output.")
                    st.exception(e)
    else:
        st.info("Submit the form to generate the clinician-facing summary.")
