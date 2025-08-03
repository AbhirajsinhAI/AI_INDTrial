import streamlit as st
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
import os
from io import BytesIO
import openai
from tempfile import NamedTemporaryFile

# Set page title
st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🎤 Qnest AI Voice Interviewer")

# --- Load your OpenAI API Key from secrets ---
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- Step 1: Set your question here or dynamically generate later ---
question = "Tell me about your experience related to this job role."

# --- Step 2: Convert question to speech using gTTS ---
tts = gTTS(text=question, lang='en')
tts_path = "question.mp3"
tts.save(tts_path)

# --- Step 3: Play the audio question ---
st.subheader("🔊 AI is asking...")
with open(tts_path, "rb") as audio_file:
    st.audio(audio_file.read(), format='audio/mp3')

# --- Step 4: Record the user's answer ---
st.subheader("🎙️ Your Turn to Answer")
audio = mic_recorder(
    start_prompt="Click to start recording your answer",
    stop_prompt="Stop recording",
    key="recorder"
)

# --- Step 5: Transcribe the recorded audio ---
def transcribe_audio(audio_bytes):
    with NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    audio_file = open(tmp_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

# --- Step 6: Analyze transcript using GPT ---
def analyze_text(text):
    prompt = f"Analyze the following interview answer for clarity, relevance, confidence, and language:\n\n{text}\n\nGive a brief report."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# --- Step 7: Show transcript and analysis report ---
if audio:
    st.audio(audio['bytes'], format='audio/wav')
    with st.spinner("Transcribing..."):
        transcript = transcribe_audio(audio['bytes'])
        st.markdown("**📝 Transcript:**")
        st.success(transcript)

    with st.spinner("Analyzing response..."):
        report = analyze_text(transcript)
        st.markdown("**📊 Interview Analysis:**")
        st.info(report)
