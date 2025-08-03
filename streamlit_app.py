import streamlit as st
from streamlit_mic_recorder import mic_recorder
import openai
from io import BytesIO
import docx2txt
import PyPDF2

st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🎙️ Qnest AI Interviewer")

# Read API key from .streamlit/secrets.toml
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- Step 1: JD & Resume Upload ---
st.subheader("📄 Upload Job Description and Resume")

jd_file = st.file_uploader("Upload Job Description", type=["pdf", "docx"])
resume_file = st.file_uploader("Upload Candidate Resume", type=["pdf", "docx"])

def read_file(file):
    if file is not None:
        if file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif file.name.endswith(".docx"):
            return docx2txt.process(file)
    return ""

jd_text = read_file(jd_file)
resume_text = read_file(resume_file)

if jd_text and resume_text:
    st.success("✅ JD and Resume uploaded successfully!")
    st.text_area("📝 JD Content", jd_text, height=200)
    st.text_area("🧾 Resume Content", resume_text, height=200)

# --- Step 2: Audio Interview Section ---
st.subheader("🎤 Interview Question")

question = "Tell me about yourself and why you are a good fit for this role."
st.markdown(f"**🧠 AI Question:** {question}")

audio = mic_recorder(
    start_prompt="▶️ Start Recording",
    stop_prompt="⏹️ Stop Recording",
    key="recorder",
)

def transcribe_audio(audio_bytes):
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    transcript = openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text

def analyze_text(text):
    prompt = f"""
You are an AI interviewer. Analyze the following answer for communication quality, clarity, relevance to job description, and confidence.

Answer: {text}

Provide a summary and constructive feedback in simple bullet points.
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )
    return response.choices[0].message.content

if audio:
    st.success("🔊 Audio recorded successfully!")
    transcript = transcribe_audio(audio['bytes'])
    st.markdown("**🗒️ Transcript:**")
    st.write(transcript)

    report = analyze_text(transcript)
    st.markdown("**📊 AI Feedback Report:**")
    st.write(report)
