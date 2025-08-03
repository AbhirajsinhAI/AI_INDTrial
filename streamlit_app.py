import streamlit as st
import openai
import os
from gtts import gTTS
import tempfile
from streamlit_mic_recorder import mic_recorder

# Load your API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🎤 Qnest AI Interviewer")

questions = [
    "Tell me about yourself.",
    "What are your strengths and weaknesses?",
    "Describe a challenge you've faced at work and how you handled it.",
    "Where do you see yourself in five years?",
    "Why should we hire you?"
]

# Helper function to convert text to speech using gTTS
def ask_question(index):
    question_text = questions[index]
    st.subheader(f"Question {index + 1}")
    st.markdown(f"**{question_text}**")

    tts = gTTS(text=question_text)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)

    with open(temp_audio.name, "rb") as audio_file:
        st.audio(audio_file.read(), format="audio/mp3")

    return question_text

# Transcription function
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

# Feedback/Analysis using GPT
def analyze_text(transcript):
    prompt = f"""Analyze this interview response for clarity, confidence, and relevance to the job:
    
    "{transcript}"
    
    Give a summary and improvement suggestions."""
    
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

# Main loop
if "question_index" not in st.session_state:
    st.session_state.question_index = 0

if st.session_state.question_index < len(questions):
    question_text = ask_question(st.session_state.question_index)

    audio = mic_recorder(start_prompt="🎙️ Start Recording", stop_prompt="⏹️ Stop", key="recorder")

    if audio and "bytes" in audio:
        with st.spinner("Transcribing and analyzing..."):
            transcript = transcribe_audio(audio["bytes"])
            report = analyze_text(transcript)

            st.success("📝 Transcript:")
            st.write(transcript)

            st.success("📊 Feedback:")
            st.markdown(report)

        if st.button("Next Question ➡️"):
            st.session_state.question_index += 1
else:
    st.success("✅ Interview Completed!")
