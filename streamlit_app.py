import streamlit as st
from streamlit_mic_recorder import mic_recorder
import tempfile
import os

from openai import OpenAI
client = OpenAI()

# === UI ===
st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🎙️ Qnest AI Interviewer")
st.markdown("Answer the AI's questions verbally. This is a voice-based mock interview.")

# === Define Questions ===
questions = [
    "Tell me about yourself.",
    "Why do you want to work with us?",
    "Describe a challenging situation you faced and how you handled it.",
    "What are your strengths and weaknesses?",
    "Where do you see yourself in five years?"
]

# === State to Keep Track of Progress ===
if 'q_index' not in st.session_state:
    st.session_state.q_index = 0
if 'interview_done' not in st.session_state:
    st.session_state.interview_done = False

# === Ask Question via Text-to-Speech ===
def ask_question(index):
    st.subheader(f"Question {index+1}:")
    st.markdown(f"**{questions[index]}**")

# === Transcribe Audio ===
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    os.remove(tmp_path)
    return transcript.text

# === Analyze Text ===
def analyze_text(text):
    prompt = f"""You are an AI Interview coach. Analyze the following answer and give feedback on tone, clarity, confidence, and content quality. Also mention if the answer is aligned with a strong candidate profile.

Answer: {text}"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful and critical interview evaluator."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# === Interview Logic ===
if not st.session_state.interview_done:
    current_question = st.session_state.q_index
    ask_question(current_question)

    audio = mic_recorder(
        start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop", just_once=True, key=f"rec_{current_question}"
    )

    if audio:
        st.success("Audio recorded. Transcribing...")
        transcript = transcribe_audio(audio['bytes'])
        st.markdown(f"**You said:** {transcript}")
        st.write("Analyzing answer...")
        feedback = analyze_text(transcript)
        st.info(feedback)

        st.session_state.q_index += 1

        if st.session_state.q_index >= len(questions):
            st.session_state.interview_done = True
            st.success("Interview complete! You can refresh to try again.")

else:
    st.balloons()
    st.success("All questions answered. Interview session is complete.")
