import streamlit as st
import streamlit.components.v1 as components

st.title("AI Interview Assistant")
st.subheader("Welcome to the audio-based interview interface")
st.write("Click below to record your audio answer:")

# HTML + JavaScript for audio recording (WebRTC not supported natively in Streamlit yet)
components.html("""
    <h4>Audio recording feature coming soon here...</h4>
    <p>This placeholder will become a live mic to record user's audio response.</p>
""", height=200)
