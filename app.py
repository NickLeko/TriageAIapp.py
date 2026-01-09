import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="TriageAI MVP", layout="wide")

# ----------------------------
# Banner disclaimer
# ----------------------------
st.markdown(
    """
    <div style="background-color:#ffcccc; padding:14px; border-radius:10px; margin-bottom:14px; border-left:5px solid #ff0000;">
      <strong>🚨 IMPORTANT DISCLAIMER</strong><br>
      This is an <strong>educational prototype only</strong>. It is <strong>NOT medical advice, diagnosis, or treatment</strong>.
      All outputs are AI-generated from user input and may contain errors or omissions.
      Always consult a licensed healthcare provider for medical concerns.
    </div>
    """,
    unsafe_allow_html=True,
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
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Return ONLY valid JSON matching the schema.\n\n"
                    f"PAYLOAD:\n{json.dumps(payload, ensure_ascii=False)}"
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
    return json.loads(response.output_text)

# ----------------------------
# Options
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
# Sidebar form (native scrolling)
# ----------------------------
payload = {}
submitted = False
consent = False

with st.sidebar:
    st.header("Patient Intake Form")

    with st.form("intake_form", clear_on_submit=False):
        consent = st.checkbox(
            "I understand this is a prototype for demonstration purposes only and does not provide medical advice.",
            value=False,
        )

        st.subheader("Basics")
        age = st.number_input("Age", min_value=0, max_value=120, value=25)
        sex_at_birth = st.selectbox("Sex at birth", ["Female", "Male", "Intersex", "Prefer not to say"])
        height = st.text_input("Height (optional)", placeholder='e.g., 5\'6" or 168 cm')
        weight = st.text_input("Weight (optional)", placeholder="e.g., 160 lb or 73 kg")

        st.subheader("Visit Context")
        reason_for_visit = st.text_area("Main reason for visit today?", height=90)
        symptom_start = st.text_input("When did this start?", placeholder="e.g., 3 days ago")
        symptom_trend = st.selectbox("Symptom trend?", SYMPTOM_TREND_OPTIONS)

        st.subheader("Medical History")
        conditions = st.multiselect("Diagnosed conditions", COMMON_CONDITIONS)
        other_conditions = ""
        if "Other" in conditions:
            other_conditions = st.text_input("Other conditions", placeholder="e.g., migraines, IBS")

        medications = st.text_area(
            "Current medications",
            placeholder="Enter one per line. Include doses if known.",
            height=90,
        )

        has_allergies = st.selectbox("Allergies?", YESNO)
        allergies = ""
        if has_allergies == "Yes":
            allergies = st.text_area(
                "List allergies",
                placeholder="Enter one per line (medication/food/other).",
                height=80,
            )

        st.subheader("Social History")
        smoking = st.selectbox("Smoke or vape?", ["No", "Yes - smoke", "Yes - vape", "Yes - both"])
        alcohol = st.selectbox("Alcohol frequency?", ALCOHOL_OPTIONS)
        drugs = st.selectbox("Recreational drugs?", YESNO)

        st.subheader("Anything Else")
        additional_notes = st.text_area("Additional notes?", height=90)

        submitted = st.form_submit_button("Generate Summary")

        # Build payload
        pmh = [c for c in conditions if c != "Other"]
        if other_conditions.strip():
            pmh.append(other_conditions.strip())

        med_list = [m.strip() for m in medications.splitlines() if m.strip()]
        allergy_list = [a.strip() for a in allergies.splitlines() if a.strip()] if allergies else []

        social_flags = []
        if smoking != "No":
            social_flags.append(smoking)
        if alcohol != "None":
            social_flags.append(f"Alcohol: {alcohol}")
        if drugs == "Yes":
            social_flags.append("Recreational drugs")

        payload = {
            "age": str(age),
            "sex_at_birth": sex_at_birth,
            "height": height.strip() or "Not provided",
            "weight": weight.strip() or "Not provided",
            "reason_for_visit": reason_for_visit.strip(),
            "symptom_start": symptom_start.strip() or "Not provided",
            "symptom_trend": symptom_trend,
            "past_medical_history": pmh,
            "medications": med_list,
            "allergies": allergy_list,
            "social_history_flags": social_flags,
            "additional_notes": additional_notes.strip(),
        }

# ----------------------------
# Main output
# ----------------------------
st.subheader("Clinician Summary")

if not submitted:
    st.info("Fill the form in the sidebar, acknowledge consent, then click **Generate Summary**.")
elif not consent:
    st.error("Please acknowledge the consent checkbox before generating a summary.")
    with st.expander("Raw payload (debug)"):
        st.json(payload)
elif not payload.get("reason_for_visit"):
    st.error("Reason for visit is required.")
    with st.expander("Raw payload (debug)"):
        st.json(payload)
else:
    with st.expander("Raw payload (debug)"):
        st.json(payload)

    with st.spinner("Generating..."):
        try:
            summary = generate_clinician_summary(payload)

            full_md = (
                "# Clinical Summary\n\n"
                f"{summary['clinical_summary']}\n\n"
                "## Structured Data\n"
                "```json\n"
                f"{json.dumps(summary['structured_data'], indent=2)}\n"
                "```\n\n"
                "## Items to Clarify\n"
                + ("\n".join([f"- {x}" for x in summary["items_to_clarify"]]) if summary["items_to_clarify"] else "- None")
                + "\n\n## Data Quality Notes\n"
                + ("\n".join([f"- {x}" for x in summary["data_quality_notes"]]) if summary["data_quality_notes"] else "- None")
                + f"\n\n**{summary['disclaimer']}**\n"
            )

            st.success("Done!")

            st.markdown("### 📋 Clinical Summary")
            st.write(summary["clinical_summary"])

            st.markdown("### 🗂️ Structured Data")
            st.json(summary["structured_data"])

            st.markdown("### ❓ Items to Clarify")
            if summary["items_to_clarify"]:
                for item in summary["items_to_clarify"]:
                    st.write(f"- {item}")
            else:
                st.write("None")

            st.markdown("### ⚠️ Data Quality Notes")
            if summary["data_quality_notes"]:
                for note in summary["data_quality_notes"]:
                    st.write(f"- {note}")
            else:
                st.write("None")

            st.markdown(f"**{summary['disclaimer']}**")

            st.markdown("### 📥 Downloads")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "Download Markdown",
                    data=full_md,
                    file_name="summary.md",
                    mime="text/markdown",
                )
            with c2:
                st.download_button(
                    "Download JSON",
                    data=json.dumps(summary["structured_data"], indent=2),
                    file_name="data.json",
                    mime="application/json",
                )

        except Exception as e:
            st.error("Generation failed — check your API key/billing or try again.")
            st.exception(e)
