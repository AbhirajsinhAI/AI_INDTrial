import streamlit as st
from streamlit_mic_recorder import mic_recorder
import openai
import tempfile
import os

st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")

# 🔐 Secure API key
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Functions ---

def extract_text_from_docx(uploaded_file):
    from docx import Document
    doc = Document(uploaded_file)
    return "\n".join([para.text for para in doc.paragraphs])

def generate_questions(jd_text, resume_text):
    prompt = f"""You are an intelligent hiring assistant.
Based on the following job description and candidate resume, generate 5 relevant and diverse interview questions.

Job Description:
{jd_text}

Resume:
{resume_text}

Only output the questions in list format, no extra text."""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip().split("\n")

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        tmpfile.write(audio_bytes)
        tmpfile_path = tmpfile.name

    with open(tmpfile_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

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
- Score (out of 10):"""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- UI ---

st.title("🎙️ Qnest AI Interviewer")

with st.sidebar:
    st.header("📄 Upload JD and Resume")
    jd_file = st.file_uploader("Upload Job Description (.docx)", type=["docx"])
    resume_file = st.file_uploader("Upload Candidate Resume (.docx)", type=["docx"])

if jd_file and resume_file:
    jd_text = extract_text_from_docx(jd_file)
    resume_text = extract_text_from_docx(resume_file)

    st.success("✅ Files extracted successfully.")
    if st.button("🎯 Generate Interview Questions"):
        with st.spinner("Generating questions..."):
            questions = generate_questions(jd_text, resume_text)
        st.session_state.questions = questions
        st.session_state.current_q = 0
        st.success("✅ Questions Ready!")

# Show and record current question
if "questions" in st.session_state and st.session_state.current_q < len(st.session_state.questions):
    q_index = st.session_state.current_q
    question = st.session_state.questions[q_index]
    st.subheader(f"🔹 Question {q_index + 1}:")
    st.write(question)

    audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop Recording", key=f"rec_{q_index}")

    if audio and audio["bytes"]:
        with st.spinner("Transcribing..."):
            transcript = transcribe_audio(audio["bytes"])
            st.text_area("📝 Transcribed Answer", transcript, height=150)

        with st.spinner("Evaluating..."):
            feedback = analyze_text(transcript)
            st.markdown("📊 **AI Feedback:**")
            st.code(feedback)

        if st.button("➡️ Next Question"):
            st.session_state.current_q += 1
else:
    if "questions" in st.session_state:
        st.success("🎉 Interview complete!")
