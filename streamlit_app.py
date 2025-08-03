import streamlit as st
import datetime
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="AI Interview Assistant")

st.title("🎙️ AI Interview Assistant")
st.subheader("Welcome to the audio-based interview interface")
st.markdown("Please click the record button and answer the interview question.")

# Interview question placeholder
st.info("🧠 Interview Question: Tell me about yourself.")

# Record button
audio = mic_recorder(start_prompt="Start Recording", stop_prompt="Stop Recording", just_once=True)

# Save recorded audio
if audio is not None:
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_response_{now}.wav"
    with open(filename, "wb") as f:
        f.write(audio["bytes"])
    st.success(f"Audio recorded and saved as {filename}")
    st.audio(audio["bytes"], format="audio/wav")


