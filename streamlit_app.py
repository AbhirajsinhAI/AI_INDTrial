import streamlit as st
import openai
import tempfile
import os
from docx import Document
from streamlit_mic_recorder import mic_recorder
import whisper
from google.cloud import texttospeech
import base64
import json

# Load secrets
openai.api_key = st.secrets["openai_api_key"]

# Setup Google TTS Client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

def text_to_speech_google(text, filename="question.mp3"):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    
    with open(filename, "wb") as out:
        out.write(response.audio_content)

    audio_bytes = open(filename, 'rb').read()
    return audio_bytes

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def generate_questions(jd_text, resume_text):
    prompt = f"""Generate 5 interview questions based on the following job description and resume:
    
    Job Description:\n{jd_text}\n
    Resume:\n{resume_text}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().split("\n")

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        audio_path = f.name
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

def analyze_text(text):
    prompt = f"""You are an AI interview evaluator. Analyze this answer and give:
    1. Relevance to job role
    2. Communication quality
    3. Confidence level
    4. Suggestions to improve
    5. Overall score out of 10

    Answer: {text}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- Streamlit UI ---
st.title("🎙️ Qnest AI Interviewer")

# Upload JD and Resume
jd_file = st.file_uploader("📄 Upload Job Description (DOCX)", type=["docx"])
resume_file = st.file_uploader("📄 Upload Candidate Resume (DOCX)", type=["docx"])

if jd_file and resume_file:
    jd_text = extract_text_from_docx(jd_file)
    resume_text = extract_text_from_docx(resume_file)

    if st.button("🧠 Generate Questions"):
        questions = generate_questions(jd_text, resume_text)
        st.session_state["questions"] = questions
        st.session_state["current_q"] = 0
        st.success("✅ Questions generated!")

if "questions" in st.session_state:
    questions = st.session_state["questions"]
    current_q = st.session_state["current_q"]

    if current_q < len(questions):
        st.subheader(f"🔹 Question {current_q+1}")
        st.markdown(questions[current_q])

        # Speak question
        audio = text_to_speech_google(questions[current_q])
        st.audio(audio, format="audio/mp3")

        # Record answer
        audio_recorded = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop Recording", key=f"rec_{current_q}", just_once=True)

        if audio_recorded and audio_recorded["bytes"]:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_recorded["bytes"])
                st.markdown(f"🗣️ **Transcript:** {transcript}")

                with st.spinner("Analyzing..."):
                    feedback = analyze_text(transcript)
                    st.markdown("🧠 **AI Feedback:**")
                    st.markdown(feedback)

            if st.button("➡️ Next Question"):
                st.session_state["current_q"] += 1
    else:
        st.success("🎉 Interview completed!")
