import streamlit as st
import openai
import tempfile
import os
import json
import base64
import time
from io import BytesIO
from pydub import AudioSegment
from google.cloud import texttospeech

# Load secrets
openai.api_key = st.secrets["openai_api_key"]
creds_dict = st.secrets["google_tts"]

# Set up Google TTS credentials
with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_json:
    json.dump(creds_dict, temp_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json.name

# Title
st.title("🧠 Qnest AI Interviewer")

# Session state
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []
if "summaries" not in st.session_state:
    st.session_state.summaries = []

# Upload JD and Resume
jd_file = st.file_uploader("📄 Upload Job Description", type=["txt", "docx"])
resume_file = st.file_uploader("📄 Upload Candidate Resume", type=["txt", "docx"])

def extract_text(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".txt"):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith(".docx"):
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
    return ""

def generate_questions(jd_text, resume_text):
    prompt = f"""Generate 5 interview questions based on the following JD and Resume.
    
    JD: {jd_text}

    Resume: {resume_text}

    Only return the questions as a numbered list."""
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content
    return [line.strip()[3:] for line in content.split("\n") if line.strip() and line.strip()[0].isdigit()]

def synthesize_speech(text):
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )

    return response.audio_content

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio = AudioSegment.from_file(temp_audio_path, format="webm")
    wav_path = temp_audio_path.replace(".webm", ".wav")
    audio.export(wav_path, format="wav")

    with open(wav_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)["text"]
    return transcript

def summarize_response(transcript, question):
    prompt = f"""You're an interview coach. The candidate was asked: "{question}"

Here is their response: "{transcript}"

Give a 1-line summary and assess its quality on communication, relevance, and depth."""
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# Main flow
if jd_file and resume_file and st.button("📤 Generate Questions"):
    jd_text = extract_text(jd_file)
    resume_text = extract_text(resume_file)

    st.session_state.questions = generate_questions(jd_text, resume_text)
    st.session_state.current_q = 0
    st.success("Questions generated!")

if st.session_state.questions:
    current_q = st.session_state.current_q
    questions = st.session_state.questions

    st.subheader(f"Q{current_q+1}: {questions[current_q]}")

    if st.button("🔊 Speak Question"):
        audio_bytes = synthesize_speech(questions[current_q])
        st.audio(audio_bytes, format="audio/mp3")

    audio = st.audio_recorder("🎙️ Record your answer")

    if audio and st.button("⏹️ Stop & Analyze"):
        transcript = transcribe_audio(audio["bytes"])
        st.session_state.transcripts.append(transcript)

        summary = summarize_response(transcript, questions[current_q])
        st.session_state.summaries.append(summary)

        st.markdown("**📝 Transcript:**")
        st.write(transcript)

        st.markdown("**📋 Summary & Feedback:**")
        st.write(summary)

        if current_q + 1 < len(questions):
            st.session_state.current_q += 1
            time.sleep(1)
            st.rerun()
        else:
            st.success("✅ Interview Completed!")
            st.markdown("### 🧾 Final Summary")
            for i, (q, s) in enumerate(zip(st.session_state.questions, st.session_state.summaries)):
                st.markdown(f"**Q{i+1}: {q}**\n\n{s}")

