import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
import openai
import tempfile
import os
import json
from google.cloud import texttospeech
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# Load API Keys
openai.api_key = st.secrets["openai_api_key"]

# Title
st.set_page_config(page_title="Qnest AI Interviewer", layout="wide")
st.title("🧠 Qnest AI Interviewer")

# --------------------------- Function Definitions ---------------------------

def read_file_text(file):
    if file.name.endswith('.pdf'):
        pdf = PdfReader(file)
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.name.endswith('.docx'):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return file.read().decode("utf-8")

def generate_questions(jd_text, resume_text):
    prompt = f"""
    Based on the following job description and resume, generate 5 relevant interview questions that assess job fit and skills.

    Job Description:
    {jd_text}

    Resume:
    {resume_text}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return [q.strip() for q in response.choices[0].message.content.split('\n') if q.strip()]

def synthesize_speech(text):
    creds_dict = json.loads(st.secrets["google_tts"])
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

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio = AudioSegment.from_file(temp_audio_path, format="webm")
    wav_path = temp_audio_path.replace(".webm", ".wav")
    audio.export(wav_path, format="wav")

    with open(wav_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

def analyze_text(text):
    prompt = f"""
    You are an AI interviewer. Analyze the following response from a candidate and give brief feedback on:

    1. Communication Clarity
    2. Confidence
    3. Relevance to the question
    4. English fluency
    5. Technical or domain-specific strength

    Response:
    {text}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --------------------------- App Flow ---------------------------

st.subheader("Step 1: Upload Job Description and Resume")

jd_file = st.file_uploader("📄 Upload Job Description (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
resume_file = st.file_uploader("📄 Upload Candidate Resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])

if jd_file and resume_file:
    jd_text = read_file_text(jd_file)
    resume_text = read_file_text(resume_file)

    if st.button("🧠 Generate Interview Questions"):
        with st.spinner("Thinking..."):
            questions = generate_questions(jd_text, resume_text)
            st.session_state.questions = questions
            st.session_state.current_q = 0
            st.success("Questions generated successfully!")

if "questions" in st.session_state:
    st.subheader("Step 2: Interview")

    questions = st.session_state.questions
    current_q = st.session_state.current_q

    if current_q < len(questions):
        st.markdown(f"**Q{current_q+1}:** {questions[current_q]}")

        if st.button("🔊 Speak Question"):
            with st.spinner("Generating voice..."):
                audio_bytes = synthesize_speech(questions[current_q])
                st.audio(audio_bytes, format="audio/mp3")

        audio = mic_recorder(start_prompt="🎙️ Start Recording", stop_prompt="⏹️ Stop", key="recorder")

        if audio:
            st.audio(audio["bytes"], format="audio/webm")
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio["bytes"])
                st.markdown("**Your Answer:**")
                st.write(transcript)

                st.markdown("**AI Feedback:**")
                feedback = analyze_text(transcript)
                st.success(feedback)

            if st.button("➡️ Next Question"):
                st.session_state.current_q += 1
                st.experimental_rerun()
    else:
        st.success("✅ Interview completed. Thank you!")
