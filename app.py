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

USER_PROMPT_TEMPLATE = (
    "Return ONLY valid JSON that EXACTLY matches this schema (no extra text, no markdown):\n"
    "{schema}\n\n"
    "Summarize this intake payload:\n\n{payload}"
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
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                schema=json.dumps(CLINICIAN_SUMMARY_SCHEMA, indent=2),
                payload=json.dumps(payload, ensure_ascii=False, indent=2)
            )}
        ],
        response_format={"type": "json_object"},
        temperature=0.3  # Low for consistency
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from model")
    return json.loads(raw_content)

# ----------------------------
# Common options (same as before)
# ----------------------------
COMMON_CONDITIONS = ["Hypertension", "Diabetes", "Asthma", "Depression/Anxiety", "Hypothyroidism", "Hyperlipidemia", "GERD", "COPD", "Chronic kidney disease", "Other"]
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

    with st.form("intake_form"):
        consent = st.checkbox(
            "I understand this is a prototype for demonstration purposes only and does not provide medical advice.",
            value=False
        )

        # (Form fields unchanged from previous revision for brevity—copy your existing ones here)
        # ... [insert your full form code from original/previous here] ...

        submitted = st.form_submit_button("Generate Clinician Summary")

        # (Payload building unchanged—use your existing logic)

with right:
    st.subheader("Clinician Summary")

    if not submitted:
        st.info("Fill the form, acknowledge the disclaimer, and click Generate.")
    elif not consent:
        st.error("Please acknowledge the disclaimer checkbox.")
    elif not payload.get("reason_for_visit"):
        st.error("Main reason for visit required.")
    else:
        st.caption("Intake payload (debug)")
        with st.expander("View raw payload"):
            st.json(payload)

        with st.spinner("Generating..."):
            try:
                summary = generate_clinician_summary(payload)

                full_markdown = f"""# TriageAI Summary\n\n### Clinical Summary\n{summary['clinical_summary']}\n\n### Structured Data\n```json\n{json.dumps(summary['structured_data'], indent=2)}\n```\n\n### Items to Clarify\n- {'\n- '.join(summary['items_to_clarify']) if summary['items_to_clarify'] else 'None'}\n\n### Data Quality Notes\n- {'\n- '.join(summary['data_quality_notes']) if summary['data_quality_notes'] else 'None'}\n\n**{summary['disclaimer']}**"""

                st.success("Generated!")

                st.markdown("### 📋 Clinical Summary")
                st.markdown(summary["clinical_summary"])

                st.markdown("### 🗂️ Structured Data")
                st.json(summary["structured_data"])

                st.markdown("### ❓ Items to Clarify")
                st.write("- " + "\n- ".join(summary["items_to_clarify"]) if summary["items_to_clarify"] else "None")

                st.markdown("### ⚠️ Data Quality Notes")
                st.write("- " + "\n- ".join(summary["data_quality_notes"]) if summary["data_quality_notes"] else "None")

                st.markdown(f"**{summary['disclaimer']}**")

                st.markdown("### 📥 Downloads")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("Download Markdown", full_markdown, "triage_summary.md", "text/markdown")
                with col2:
                    st.download_button("Download JSON", json.dumps(summary["structured_data"], indent=2), "structured_data.json", "application/json")

            except Exception as e:
                st.error("Generation failed—check API key or try again.")
                st.exception(e)
