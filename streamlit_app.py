import streamlit as st
import openai
from openai import OpenAI
from google.cloud import texttospeech
import json
import tempfile
import os
from pydub import AudioSegment
import base64
import whisper

st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🧠 Qnest AI Interviewer")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Load Whisper
whisper_model = whisper.load_model("base")

# ---- Upload JD and Resume ----
st.sidebar.header("Upload Files")
jd_file = st.sidebar.file_uploader("📄 Upload Job Description (JD)", type=["docx", "txt"])
resume_file = st.sidebar.file_uploader("📄 Upload Resume", type=["docx", "txt"])

# ---- Extract Text ----
def extract_text(uploaded_file):
    if uploaded_file is None:
        return ""
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode()
    elif uploaded_file.name.endswith(".docx"):
        from docx import Document
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

# ---- Generate Questions ----
def generate_questions(jd_text, resume_text):
    prompt = f"""
Given the following job description and resume, generate 5 relevant and intelligent interview questions. 
They should evaluate job fit, skill match, and communication ability.

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    questions = response.choices[0].message.content.strip().split("\n")
    return [q.strip("- ").strip() for q in questions if q.strip()]

# ---- Google TTS (Text-to-Speech) ----
def synthesize_speech(text):
    creds_dict = st.secrets["google_tts"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_json:
        json.dump(creds_dict, temp_json)
        temp_json.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json.name

        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content

# ---- Transcribe Audio ----
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        f.flush()
        audio = whisper.load_audio(f.name)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(whisper_model.device)
        options = whisper.DecodingOptions(fp16=False)
        result = whisper.decode(whisper_model, mel, options)
        return result.text

# ---- Record Audio ----
def record_audio():
    st.write("🎙️ Recording... Please speak.")
    audio = st.audio_recorder("Click to start/stop recording", format="audio/wav", key="audio")
    if audio:
        st.audio(audio, format="audio/wav")
        return {"bytes": audio.getvalue(), "filename": "response.wav"}
    return None

# ---- Session Variables ----
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "responses" not in st.session_state:
    st.session_state.responses = []

# ---- Trigger Question Generation ----
if jd_file and resume_file and st.button("🧠 Generate Interview Questions"):
    jd_text = extract_text(jd_file)
    resume_text = extract_text(resume_file)
    st.session_state.questions = generate_questions(jd_text, resume_text)
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.success("✅ Questions generated!")

# ---- Interview Flow ----
if st.session_state.questions:
    current_q = st.session_state.current_q
    total_q = len(st.session_state.questions)

    st.markdown(f"### Q{current_q + 1}: {st.session_state.questions[current_q]}")

    col1, col2 = st.columns(2)

    if col1.button("🔊 Speak Question"):
        audio_bytes = synthesize_speech(st.session_state.questions[current_q])
        st.audio(audio_bytes, format="audio/wav")

    audio = record_audio()

    if col2.button("✅ Submit Answer"):
        if audio:
            transcript = transcribe_audio(audio["bytes"])
            st.session_state.responses.append(transcript)
            st.success("Answer Recorded ✅")

            if current_q + 1 < total_q:
                st.session_state.current_q += 1
            else:
                st.success("🎉 Interview Complete!")
                st.markdown("### 📝 Your Responses:")
                for i, (q, r) in enumerate(zip(st.session_state.questions, st.session_state.responses)):
                    st.markdown(f"**Q{i + 1}: {q}**")
                    st.markdown(f"🗣️ {r}")
        else:
            st.warning("Please record your answer before submitting.")
