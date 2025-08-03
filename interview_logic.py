# interview_logic.py

import openai

# Load your OpenAI API key (optional if set as environment variable)
import streamlit as st
openai.api_key = st.secrets["OPENAI_API_KEY"]

def transcribe_audio(audio_bytes):
    # Use Whisper API for transcription
    audio_file = open("temp_audio.wav", "wb")
    audio_file.write(audio_bytes)
    audio_file.close()

    with open("temp_audio.wav", "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)

    return transcript["text"]

def analyze_text(text):
    # Use GPT-4 to analyze the transcript
    prompt = f"""You are an AI recruiter. Analyze this interview transcript:
    ---
    {text}
    ---
    Give scores for:
    - Communication
    - Job Fit
    - Confidence
    And provide a 3-line summary."""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    content = response['choices'][0]['message']['content']
    return content
