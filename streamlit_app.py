import streamlit as st
import openai
import tempfile
import json
import os
from google.cloud import texttospeech
from streamlit_mic_recorder import mic_recorder
from io import BytesIO
from pydub import AudioSegment

# Set OpenAI Key
openai.api_key = st.secrets["openai_api_key"]

# Set Google TTS credentials
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_json:
    temp_json.write(json.dumps(st.secrets["google_tts"]).encode())
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json.name

# Initialize TTS client
tts_client = texttospeech.TextToSpeechClient()

def speak_text(text, filename="output.mp3"):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(filename, "wb") as out:
        out.write(response.audio_content)

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    with open(temp_audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    return transcript['text']

def analyze_text(transcript):
    prompt = f"Analyze the following candidate's answer in an interview:\n\n{transcript}\n\nProvide a rating out of 10, strengths, weaknesses, and overall comments."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# --- UI ---
st.title("🎤 Qnest: Voice-based AI Interviewer")

# --- JD & Resume Upload ---
jd_file = st.file_uploader("📄 Upload Job Description", type=["pdf", "docx"])
resume_file = st.file_uploader("📄 Upload Candidate Resume", type=["pdf", "docx"])

def extract_text(doc_file):
    from docx import Document
    return "\n".join([p.text for p in Document(doc_file).paragraphs])

if jd_file and resume_file:
    jd_text = extract_text(jd_file)
    resume_text = extract_text(resume_file)

    # Generate questions
    prompt = f"""Generate 5 technical and behavioral interview questions for a candidate based on this job description and resume:

Job Description:
{jd_text}

Resume:
{resume_text}

Questions:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    questions = response["choices"][0]["message"]["content"].strip().split("\n")

    st.success("✅ Questions Generated!")
    st.write("### 📋 Interview Questions:")
    for i, q in enumerate(questions, 1):
        st.write(f"**Q{i}:** {q}")

    if "index" not in st.session_state:
        st.session_state.index = 0
        st.session_state.feedback = []

    if st.session_state.index < len(questions):
        question = questions[st.session_state.index]
        st.markdown(f"## 🎙️ Question {st.session_state.index + 1}")
        st.markdown(f"**{question}**")

        if st.button("🔊 Speak Question"):
            speak_text(question, "question.mp3")
            st.audio("question.mp3", format="audio/mp3")

        audio = mic_recorder(start_prompt="🎤 Answer Now", stop_prompt="⏹️ Stop", key=f"mic_{st.session_state.index}")

        if audio:
            transcript = transcribe_audio(audio["bytes"])
            st.markdown("### 📄 Transcript:")
            st.write(transcript)

            st.markdown("### 📊 AI Evaluation:")
            report = analyze_text(transcript)
            st.write(report)

            st.session_state.feedback.append({
                "question": question,
                "transcript": transcript,
                "report": report
            })

            st.session_state.index += 1
            st.experimental_rerun()
    else:
        st.success("✅ Interview Completed")
        for i, item in enumerate(st.session_state.feedback, 1):
            st.write(f"### Q{i}: {item['question']}")
            st.write(f"🗣️ Answer: {item['transcript']}")
            st.write(f"📊 Feedback: {item['report']}")
