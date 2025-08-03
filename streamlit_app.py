import streamlit as st
import datetime
import base64

st.set_page_config(page_title="AI Interview Assistant")

st.title("🎙️ AI Interview Assistant")
st.subheader("Welcome to the audio-based interview interface")
st.markdown("Please click the record button and answer the interview question.")

st.info("🧠 Interview Question: Tell me about yourself.")

# HTML/JS for recording
st.markdown("""
<script>
let mediaRecorder;
let recordedBlobs;

function startRecording() {
  recordedBlobs = [];
  let options = { mimeType: 'audio/webm' };
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorder.ondataavailable = event => {
        if (event.data && event.data.size > 0) {
          recordedBlobs.push(event.data);
        }
      };
      mediaRecorder.start();
      document.getElementById('status').innerText = "Recording...";
    });
}

function stopRecording() {
  mediaRecorder.stop();
  document.getElementById('status').innerText = "Recording stopped. Saving...";
  mediaRecorder.onstop = () => {
    const blob = new Blob(recordedBlobs, { type: 'audio/webm' });
    const reader = new FileReader();
    reader.readAsDataURL(blob); 
    reader.onloadend = function() {
      const base64data = reader.result;
      const input = window.parent.document.createElement('input');
      input.type = 'hidden';
      input.name = 'audio_data';
      input.value = base64data;
      window.parent.document.forms[0].appendChild(input);
      window.parent.document.forms[0].submit();
    }
  };
}
</script>

<p id="status">Click record to start.</p>
<button onclick="startRecording()">🎙️ Start Recording</button>
<button onclick="stopRecording()">⏹️ Stop Recording</button>
""", unsafe_allow_html=True)

# Receive and save audio if submitted
audio_data = params = st.query_params.get("audio_data")
if audio_data:
    audio_base64 = audio_data[0].split(',')[1]
    audio_bytes = base64.b64decode(audio_base64)
    filename = f"interview_response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    with open(filename, "wb") as f:
        f.write(audio_bytes)
    st.success(f"Audio recorded and saved as {filename}")
    st.audio(audio_bytes, format="audio/webm")

