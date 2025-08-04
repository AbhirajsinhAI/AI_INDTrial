import streamlit as st
import openai
import tempfile
import os
import json
from google.cloud import texttospeech
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder
from io import BytesIO

# ----------------- Secret Setup -----------------
openai.api_key = st.secrets["openai_api_key"]

# Convert TOML secrets object to dict before dumping
google_tts_dict = dict(st.secrets["google_tts"])

with tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=".json") as temp_json:
    temp_json.write(json.dumps(google_tts_dict).encode())
    temp_json_path = temp_json.name

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_json_path

# ----------------- Google TTS -----------------
def synthesize_speech(text, lang="en-US"):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=lang, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    return response.audio_content

# ----------------- Whisper Transcription -----------------
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    audio_file = open(temp_audio_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

# ----------------- AI Feedback -----------------
def analyze_text(text):
    prompt = f"""You are an interview evaluator. Here's the candidate's response: {text}

Give a short analysis of their communication, confidence, clarity, and relevance. Then rate them out of 10 in each.

Format:
- Communication:
- Confidence:
- Clarity:
- Relevance:
- Overall Rating (out of 10):"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]

# ----------------- Streamlit App -----------------
st.title("🧠 Qnest AI Interviewer")
st.markdown("This system **asks questions with voice**, records your voice answer, **transcribes it**, and gives AI feedback.")

questions = [
    "Tell me about yourself and your current role.",
    "What are your key strengths relevant to this position?",
    "How do you handle deadlines and pressure?",
    "Can you describe a successful project you've led?",
    "Why should we hire you for this role?"
]

if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "interview_data" not in st.session_state:
    st.session_state.interview_data = []

if st.session_state.question_index < len(questions):
    current_q = questions[st.session_state.question_index]
    
    st.subheader(f"Q{st.session_state.question_index + 1}: {current_q}")
    
    if st.button("🔊 Ask Question"):
        audio_content = synthesize_speech(current_q)
        st.audio(audio_content, format="audio/mp3")

    audio = mic_recorder(start_prompt="🎤 Click to Answer", stop_prompt="🛑 Stop Recording", key=f"rec_{st.session_state.question_index}")

    if audio:
        st.audio(audio["bytes"], format="audio/webm")
        with st.spinner("Transcribing..."):
            transcript = transcribe_audio(audio["bytes"])
            st.success(f"📝 Transcript: {transcript}")

        with st.spinner("Analyzing..."):
            feedback = analyze_text(transcript)
            st.info(f"🧾 Feedback:\n{feedback}")

        st.session_state.interview_data.append({
            "question": current_q,
            "answer": transcript,
            "feedback": feedback
        })

        st.session_state.question_index += 1
        st.experimental_rerun()

else:
    st.success("🎉 Interview complete!")
    for i, entry in enumerate(st.session_state.interview_data):
        st.markdown(f"### Q{i+1}: {entry['question']}")
        st.markdown(f"**Answer:** {entry['answer']}")
        st.markdown(f"**Feedback:**\n{entry['feedback']}")
