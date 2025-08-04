import streamlit as st
import openai
import json
import tempfile
import os
from google.cloud import texttospeech
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder

# Load API Keys
openai.api_key = st.secrets["openai_api_key"]

# Set Google TTS credentials
creds_dict = st.secrets["google_tts"]
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_json:
    json.dump(creds_dict, temp_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json.name

# --- Functions ---

def generate_questions(jd_text, resume_text):
    prompt = f"""You're an AI interviewer. Based on the job description and candidate resume, ask 3 technical and 2 behavioral questions.

Job Description:
{jd_text}

Candidate Resume:
{resume_text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content'].split('\n')

def synthesize_speech(text):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return response.audio_content

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio = AudioSegment.from_file(temp_audio_path, format="wav")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_file:
        audio.export(mp3_file.name, format="mp3")
        with open(mp3_file.name, "rb") as f:
            transcript_response = openai.Audio.transcribe("whisper-1", f)
    return transcript_response["text"]

# --- UI ---

st.title("🧠 Qnest AI Interviewer")

if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []

jd_text = st.text_area("Paste Job Description (JD)", height=150)
resume_text = st.text_area("Paste Resume Text", height=150)

if st.button("Generate Questions"):
    st.session_state.questions = generate_questions(jd_text, resume_text)
    st.success("✅ Questions generated. Click 'Ask Next Question'.")

if st.session_state.questions:
    current_q = st.session_state.current_q
    question_text = st.session_state.questions[current_q]

    st.subheader(f"Q{current_q+1}: {question_text}")

    if st.button("🔊 Speak Question"):
        audio_bytes = synthesize_speech(question_text)
        st.audio(audio_bytes, format="audio/wav")

    audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop", key=f"recorder_{current_q}", format="wav")

    if audio:
        st.audio(audio['bytes'], format='audio/wav')
        if st.button("📝 Submit Answer"):
            transcript = transcribe_audio(audio['bytes'])
            st.session_state.answers.append({
                "question": question_text,
                "answer_text": transcript
            })
            st.success("Answer saved ✅")
            st.session_state.current_q += 1

# --- Final Summary ---
if st.session_state.current_q >= len(st.session_state.questions) and st.session_state.answers:
    st.subheader("📋 Interview Summary")
    for i, ans in enumerate(st.session_state.answers):
        st.markdown(f"**Q{i+1}: {ans['question']}**")
        st.markdown(f"🗣️ *{ans['answer_text']}*")
