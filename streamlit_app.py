import streamlit as st
import openai
import os
import tempfile
import json
from PyPDF2 import PdfReader
import docx
from google.cloud import texttospeech
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
import base64

st.set_page_config(page_title="Qnest AI Interviewer")

st.title("🧠 Qnest AI Interviewer")
st.write("This system asks questions with voice, records your voice answer, transcribes it, and gives AI feedback.")

# Load API keys
openai.api_key = st.secrets["openai_api_key"]

# --- Function: Extract text from DOCX ---
def extract_text_from_docx(uploaded_file):
    doc = docx.Document(uploaded_file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- Function: Generate Questions from JD & Resume ---
def generate_questions(jd_text, resume_text):
    prompt = f"""
You are an HR interviewer. Based on the job description and candidate resume below, generate 5 detailed technical and behavioral questions.

Job Description:
{jd_text}

Candidate Resume:
{resume_text}

Format:
Q1:
Q2:
Q3:
Q4:
Q5:
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return [q.strip() for q in response.choices[0].message.content.strip().split("\n") if q.strip()]

# --- Function: Google Cloud TTS ---
def synthesize_speech(text):
    creds_dict = json.loads(st.secrets["google_tts"].to_str())
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_json:
        temp_json.write(json.dumps(creds_dict).encode())
        temp_json_path = temp_json.name

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json_path
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return response.audio_content

# --- Function: Transcribe ---
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(audio_bytes)
        f_path = f.name
    audio_file = open(f_path, "rb")
    transcript = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

# --- Function: Analyze ---
def analyze_text(text):
    prompt = f"""
You are an AI interview coach. Analyze the candidate's answer below and give a 3-line summary, soft skills cues, and any gaps.

Answer:
{text}
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- File Upload Section ---
st.subheader("Upload JD and Resume")
jd_file = st.file_uploader("Upload Job Description (.docx)", type=["docx"])
resume_file = st.file_uploader("Upload Resume (.docx)", type=["docx"])

if jd_file and resume_file:
    jd_text = extract_text_from_docx(jd_file)
    resume_text = extract_text_from_docx(resume_file)

    if st.button("🔍 Generate Questions"):
        questions = generate_questions(jd_text, resume_text)
        st.session_state.questions = questions
        st.session_state.current_q = 0
        st.success("Questions generated!")

# --- Question Asking Section ---
if "questions" in st.session_state:
    questions = st.session_state.questions
    current_q = st.session_state.get("current_q", 0)

    if current_q < len(questions):
        st.subheader(f"Q{current_q + 1}: {questions[current_q]}")

        if st.button("🔊 Speak Question"):
            audio_bytes = synthesize_speech(questions[current_q])
            st.audio(audio_bytes, format="audio/mp3")

        audio = mic_recorder(start_prompt="🎤 Record your answer", stop_prompt="⏹️ Stop", key=f"rec_{current_q}")

        if audio:
            st.audio(audio["bytes"], format="audio/wav")
            transcript = transcribe_audio(audio["bytes"])
            st.markdown("**📝 Transcript:**")
            st.write(transcript)

            report = analyze_text(transcript)
            st.markdown("**📋 Feedback:**")
            st.write(report)

            if st.button("➡️ Next Question"):
                st.session_state.current_q += 1
                st.rerun()
    else:
        st.success("✅ Interview completed. Well done!")
