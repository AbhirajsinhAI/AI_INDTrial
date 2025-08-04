import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from docx import Document
from io import BytesIO
import base64
import tempfile
from pydub import AudioSegment
import os
import json
from google.cloud import texttospeech

# === INITIAL SETUP ===
st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🧠 Qnest AI Interviewer")
st.markdown("This system asks questions based on JD + resume, records your voice answers, transcribes them, and gives AI feedback.")

client = OpenAI(api_key=st.secrets["openai_api_key"])

# === GOOGLE TTS SETUP ===
def synthesize_speech(text):
    with tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=".json") as temp_json:
        temp_json.write(json.dumps(st.secrets["google_tts"]).encode())
        temp_json.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json.name

        client_tts = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = client_tts.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content

# === HELPERS ===
def read_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

def generate_questions(jd_text, resume_text):
    prompt = f"""
You are a professional interviewer.

Given the following job description and candidate resume, generate 3 interview questions that assess job-relevant skills.

Job Description:
{jd_text}

Resume:
{resume_text}

Only return questions. Number them.
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def analyze_text(answer):
    prompt = f"""
You are an AI interviewer.

Here is the transcript of a candidate's answer. Summarize the key points and assess the communication quality and confidence.

Transcript:
{answer}

Return a short summary and evaluation.
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_bytes)
        f.flush()
        sound = AudioSegment.from_file(f.name, format="webm")
        wav_path = f.name.replace(".webm", ".wav")
        sound.export(wav_path, format="wav")

    audio_file = open(wav_path, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text

# === FILE UPLOAD ===
jd_file = st.file_uploader("Upload Job Description (DOCX)", type="docx")
resume_file = st.file_uploader("Upload Resume (DOCX)", type="docx")

if jd_file and resume_file:
    jd_text = read_docx(jd_file)
    resume_text = read_docx(resume_file)

    if st.button("🎯 Generate Questions"):
        with st.spinner("Generating questions..."):
            questions = generate_questions(jd_text, resume_text)
            st.session_state.questions = questions.split("\n")
            st.session_state.q_index = 0
            st.session_state.answers = []
            st.success("Questions ready!")

# === INTERVIEW SESSION ===
if "questions" in st.session_state:
    current_q = st.session_state.questions[st.session_state.q_index]

    st.markdown(f"**Q{st.session_state.q_index+1}: {current_q}**")

    # Speak question (TTS)
    if st.button("🔊 Speak Question"):
        audio_bytes = synthesize_speech(current_q)
        b64 = base64.b64encode(audio_bytes).decode()
        st.audio(f"data:audio/mp3;base64,{b64}", format="audio/mp3")

    audio = mic_recorder(start_prompt="🎙️ Start Recording", stop_prompt="⏹️ Stop", just_once=True, key=f"rec{st.session_state.q_index}")

    if audio:
        with st.spinner("Transcribing and analyzing your answer..."):
            transcript = transcribe_audio(audio['bytes'])
            feedback = analyze_text(transcript)
            st.markdown("📝 **Your Answer (Transcript):**")
            st.info(transcript)
            st.markdown("📊 **AI Feedback:**")
            st.success(feedback)
            st.session_state.answers.append((transcript, feedback))

        # Move to next question
        if st.session_state.q_index + 1 < len(st.session_state.questions):
            st.session_state.q_index += 1
        else:
            st.success("✅ Interview complete!")
