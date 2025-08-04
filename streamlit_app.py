import streamlit as st
import openai
import tempfile
import json
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder
from google.cloud import texttospeech
from google.oauth2 import service_account

# Set OpenAI API key
openai.api_key = st.secrets["openai"]["api_key"]

# Create Google TTS client from Streamlit secrets
google_creds = service_account.Credentials.from_service_account_info(st.secrets["google_tts"])
tts_client = texttospeech.TextToSpeechClient(credentials=google_creds)

# --- Helper: Synthesize speech ---
def synthesize_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

# --- Helper: Transcribe audio ---
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_file_path = tmp_file.name

    audio_segment = AudioSegment.from_file(tmp_file_path)
    wav_path = tmp_file_path.replace(".mp3", ".wav")
    audio_segment.export(wav_path, format="wav")

    audio_file = open(wav_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

# --- Helper: Analyze response ---
def analyze_text(text):
    prompt = f"Evaluate the following job interview answer and provide feedback:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- Streamlit UI ---
st.title("🧠 Qnest AI Interviewer")
st.write("This system asks questions with voice, records your voice answer, transcribes it, and gives AI feedback.")

if "questions" not in st.session_state:
    st.session_state.questions = ["Tell me about yourself and your current role."]
    st.session_state.current_q = 0

if st.button("🔊 Ask Next Question"):
    if st.session_state.current_q < len(st.session_state.questions):
        question = st.session_state.questions[st.session_state.current_q]
        st.audio(synthesize_speech(question), format="audio/mp3")
        st.session_state.current_q += 1
    else:
        st.success("✅ All questions completed.")

audio = mic_recorder(start_prompt="Start recording", stop_prompt="Stop recording", key="recorder")

if audio and "bytes" in audio:
    st.audio(audio["bytes"], format="audio/wav")
    transcript = transcribe_audio(audio["bytes"])
    st.subheader("📜 Transcription")
    st.write(transcript)

    report = analyze_text(transcript)
    st.subheader("🧠 AI Feedback")
    st.write(report)
