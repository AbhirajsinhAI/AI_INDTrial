import streamlit as st
from streamlit_mic_recorder import mic_recorder
import openai
import docx2txt
import tempfile
import os
from pydub import AudioSegment

# Load OpenAI API key
openai.api_key = st.secrets["openai_api_key"]

st.set_page_config(page_title="Qnest AI Interviewer", layout="centered")
st.title("🧠 Qnest AI Interviewer")

st.markdown("This system asks questions, records your voice answer, transcribes it, and gives AI feedback.")

# --- Upload JD and Resume ---
st.header("📁 Upload JD and Resume")
jd_file = st.file_uploader("Upload Job Description (DOCX)", type=["docx"])
resume_file = st.file_uploader("Upload Resume (DOCX)", type=["docx"])

def extract_text(docx_file):
    return docx2txt.process(docx_file)

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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# --- Audio Transcription ---
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio_file = open(temp_audio_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript['text']

# --- AI Analysis ---
def analyze_text(answer):
    prompt = f"""
You are an AI interviewer.

Here is the transcript of a candidate's answer. Summarize the key points and assess the communication quality and confidence.

Transcript:
{answer}

Return a short summary and evaluation.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# --- Main Flow ---
if jd_file and resume_file:
    jd_text = extract_text(jd_file)
    resume_text = extract_text(resume_file)

    st.success("JD and Resume successfully uploaded and extracted.")
    
    if st.button("Ask Questions"):
        questions = generate_questions(jd_text, resume_text)
        st.session_state.questions = questions.split("\n")
        st.session_state.q_index = 0
        st.success("Generated questions. Ready to begin.")
        st.rerun()

if "questions" in st.session_state and st.session_state.questions:
    q_index = st.session_state.get("q_index", 0)
    
    if q_index < len(st.session_state.questions):
        current_q = st.session_state.questions[q_index]
        st.header(f"Q{q_index+1}: {current_q}")
        
        audio = mic_recorder(start_prompt="🎙️ Start Recording", stop_prompt="⏹️ Stop", key=f"rec_{q_index}")
        
        if audio and audio["bytes"]:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio['bytes'])
                st.subheader("📝 Transcript")
                st.write(transcript)
                
                report = analyze_text(transcript)
                st.subheader("📊 AI Feedback")
                st.write(report)
                
                if st.button("Next Question"):
                    st.session_state.q_index += 1
                    st.rerun()
    else:
        st.success("✅ Interview completed!")
