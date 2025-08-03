import streamlit as st
from streamlit_mic_recorder import mic_recorder  # if using microphone
# Other necessary imports here...

st.title("Qnest AI Interviewer")


audio = mic_recorder(start_prompt="🎤 Start Interview", stop_prompt="⏹️ Stop", key="interview")

if audio:
    st.audio(audio['bytes'], format="audio/wav")
    
    with st.spinner("Transcribing..."):
        transcript = transcribe_audio(audio['bytes'])
        st.write("📝 Transcript:")
        st.markdown(transcript)

    with st.spinner("Analyzing..."):
        report = analyze_text(transcript)
        st.write("📊 AI Analysis Report:")
        st.markdown(report)

