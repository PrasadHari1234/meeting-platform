/**
 * Browser Mic Recorder
 * Uses the MediaRecorder API to capture mic audio as WebM/Opus,
 * then POSTs it to /meetings/record for pipeline processing.
 */

let mediaRecorder = null;
let audioChunks   = [];
let timerInterval = null;
let secondsElapsed = 0;

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Prefer opus codec for smaller files
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';

    mediaRecorder = new MediaRecorder(stream, { mimeType });
    audioChunks   = [];

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.start(1000); // collect in 1-second chunks

    // Show active UI
    document.getElementById('rec-idle').classList.add('hidden');
    document.getElementById('rec-active').classList.remove('hidden');

    // Timer
    secondsElapsed = 0;
    timerInterval = setInterval(() => {
      secondsElapsed++;
      const m = Math.floor(secondsElapsed / 60);
      const s = String(secondsElapsed % 60).padStart(2, '0');
      document.getElementById('rec-timer').textContent = `${m}:${s}`;
    }, 1000);

  } catch (err) {
    alert('Could not access microphone: ' + err.message);
  }
}

async function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

  clearInterval(timerInterval);

  return new Promise(resolve => {
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      await uploadRecording(blob);
      resolve();
    };
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  });
}

async function uploadRecording(blob) {
  // Show uploading state
  document.getElementById('rec-active').classList.add('hidden');
  document.getElementById('rec-uploading').classList.remove('hidden');

  const name    = document.getElementById('rec-name').value;
  const buckets = document.getElementById('rec-buckets').value;

  const form = new FormData();
  form.append('file',          blob,    'recording.webm');
  form.append('name',          name);
  form.append('extra_buckets', buckets);

  try {
    const res  = await fetch('/meetings/record', { method: 'POST', body: form });
    const data = await res.json();
    // Redirect to the new meeting page
    window.location.href = `/meetings/${data.meeting_id}`;
  } catch (err) {
    alert('Upload failed: ' + err.message);
    document.getElementById('rec-uploading').classList.add('hidden');
    document.getElementById('rec-idle').classList.remove('hidden');
  }
}
