import streamlit as st
import openai
import tempfile
import os
import json
import docx2txt
from google.cloud import texttospeech
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="Qnest AI Interviewer", layout="wide")
st.title("🧠 Qnest AI Interviewer")
st.markdown("This system asks questions with voice, records your voice answer, transcribes it, and gives AI feedback.")

# ---- SETUP KEYS ----
openai.api_key = st.secrets["openai_api_key"]

# ---- SPEECH FUNCTION ----
def synthesize_speech(text):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_json:
        json.dump(st.secrets["google_tts"], temp_json)
        temp_json_path = temp_json.name

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json_path
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return response.audio_content

# ---- QUESTION GENERATION ----
def generate_questions(jd_text, resume_text):
    prompt = f"""
You are an AI interviewer. Based on the job description and resume below, create 5 job interview questions.

Job Description:
{jd_text}

Resume:
{resume_text}

Only list the questions. Do not answer them.
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().split("\n")

# ---- AUDIO TRANSCRIPTION ----
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio_file = open(temp_audio_path, "rb")
    transcript = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

# ---- AI FEEDBACK ----
def analyze_text(text):
    prompt = f"""
You are a professional HR expert. Analyze the candidate's response below and give:
1. A brief summary.
2. Communication rating out of 10.
3. Confidence level out of 10.
4. Job Fitment score out of 10.
5. Suggestions for improvement.

Response:
{text}
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ---- SESSION STATE ----
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_index = 0
    st.session_state.answers = []
    st.session_state.transcripts = []
    st.session_state.reports = []

# ---- FILE UPLOAD ----
st.sidebar.header("📄 Upload Files")
jd_file = st.sidebar.file_uploader("Upload Job Description (.docx)", type=["docx"])
resume_file = st.sidebar.file_uploader("Upload Candidate Resume (.docx)", type=["docx"])

if jd_file and resume_file and not st.session_state.questions:
    jd_text = docx2txt.process(jd_file)
    resume_text = docx2txt.process(resume_file)
    with st.spinner("Generating interview questions..."):
        st.session_state.questions = generate_questions(jd_text, resume_text)
    st.success("Questions generated!")

# ---- INTERVIEW FLOW ----
if st.session_state.questions:
    idx = st.session_state.current_index
    if idx < len(st.session_state.questions):
        current_q = st.session_state.questions[idx]
        st.subheader(f"Q{idx + 1}: {current_q}")

        if st.button("🔊 Speak Question"):
            audio_bytes = synthesize_speech(current_q)
            st.audio(audio_bytes, format="audio/mp3")

        audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop", just_once=True, key=f"rec_{idx}")

        if audio and "bytes" in audio:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio['bytes'])
                st.session_state.transcripts.append(transcript)

                st.subheader("📝 Transcript")
                st.write(transcript)

                report = analyze_text(transcript)
                st.session_state.reports.append(report)

                st.subheader("📊 AI Feedback")
                st.markdown(report)

                st.session_state.current_index += 1
                st.rerun()
    else:
        st.success("✅ Interview completed!")
        st.header("📋 Final Report")

        for i, (q, a, r) in enumerate(zip(st.session_state.questions, st.session_state.transcripts, st.session_state.reports)):
            st.markdown(f"**Q{i+1}:** {q}")
            st.markdown(f"**Your Answer:** {a}")
            st.markdown(f"**AI Feedback:** {r}")
            st.markdown("---")
