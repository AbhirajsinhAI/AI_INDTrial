import streamlit as st
from streamlit_mic_recorder import mic_recorder
from docx import Document
import openai
import tempfile
import os
import base64
from io import BytesIO

# Load API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🎙️ Qnest AI Interviewer")
st.write("Upload JD and Resume to begin interview. AI will ask questions, record your answers, transcribe them, and provide feedback.")

# --- Helper Functions ---

def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    return "\n".join([para.text for para in doc.paragraphs])

def generate_questions(jd_text, resume_text):
    prompt = f"""You are an intelligent hiring assistant.
Based on the following job description and candidate resume, generate 5 relevant and diverse interview questions.

Job Description:
{jd_text}

Resume:
{resume_text}

Only output questions in a list format.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().split("\n")

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        tmpfile.write(audio_bytes)
        tmpfile_path = tmpfile.name

    audio_file = open(tmpfile_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

def analyze_text(transcript):
    prompt = f"""You are a professional interviewer AI.
Evaluate the following answer for communication skills, relevance to job, and clarity. Give an honest rating out of 10 and suggestions for improvement.

Answer:
{transcript}

Return in this format:
- Relevance:
- Communication:
- Confidence:
- Suggestions:
- Score (out of 10):
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- Upload Section ---

st.header("📄 Step 1: Upload JD and Resume")

jd_file = st.file_uploader("Upload Job Description (.docx)", type="docx")
resume_file = st.file_uploader("Upload Resume (.docx)", type="docx")

if jd_file and resume_file:
    jd_text = extract_text_from_docx(jd_file)
    resume_text = extract_text_from_docx(resume_file)

    st.success("✅ JD and Resume uploaded successfully.")
    st.write("Generating interview questions...")

    questions = generate_questions(jd_text, resume_text)
    st.session_state["questions"] = questions
    st.session_state["current_q"] = 0
    st.session_state["answers"] = []
    st.success("✅ Questions generated.")

# --- Interview Section ---

if "questions" in st.session_state:
    questions = st.session_state["questions"]
    q_index = st.session_state["current_q"]

    if q_index < len(questions):
        st.header(f"🎤 Question {q_index + 1}")
        st.write(questions[q_index])

        audio = mic_recorder(
            start_prompt="Start Recording", 
            stop_prompt="Stop", 
            key=f"recorder_{q_index}", 
            just_once=True
        )

        if audio:
            transcript = transcribe_audio(audio["bytes"])
            feedback = analyze_text(transcript)

            st.markdown("📝 **Transcript:**")
            st.write(transcript)
            st.markdown("📊 **Feedback:**")
            st.write(feedback)

            st.session_state["answers"].append({
                "question": questions[q_index],
                "transcript": transcript,
                "feedback": feedback
            })
            st.session_state["current_q"] += 1
            st.experimental_rerun()
    else:
        st.success("✅ Interview Completed!")
        st.write("Here’s the summary of your performance:")

        for i, answer in enumerate(st.session_state["answers"]):
            st.subheader(f"Q{i+1}: {answer['question']}")
            st.markdown(f"**Your Answer:** {answer['transcript']}")
            st.markdown(f"**Feedback:** {answer['feedback']}")

# End of Script
