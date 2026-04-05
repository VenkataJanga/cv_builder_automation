console.log("CV Builder app.js loading - v2");

const apiBaseInput = document.getElementById("apiBaseUrl");
const startSessionBtn = document.getElementById("startSessionBtn");
const saveBaseUrlBtn = document.getElementById("saveBaseUrlBtn");
const getPreviewBtn = document.getElementById("getPreviewBtn");
const getValidationBtn = document.getElementById("getValidationBtn");
const getContextBtn = document.getElementById("getContextBtn");
const downloadDocxBtn = document.getElementById("downloadDocxBtn");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");
const resetSessionBtn = document.getElementById("resetSessionBtn");

console.log("Elements found:", {
  getValidationBtn: !!getValidationBtn,
  getContextBtn: !!getContextBtn,
  resetSessionBtn: !!resetSessionBtn
});
const answerForm = document.getElementById("answerForm");
const answerInput = document.getElementById("answerInput");
const chatMessages = document.getElementById("chatMessages");
const sessionIdLabel = document.getElementById("sessionIdLabel");
const responseBox = document.getElementById("responseBox");
const previewBox = document.getElementById("previewBox");
const contextBox = document.getElementById("contextBox");
const uploadForm = document.getElementById("uploadForm");
const cvFile = document.getElementById("cvFile");
const chatStatus = document.getElementById("chatStatus");
const voiceBtn = document.getElementById("voiceBtn");

let apiBaseUrl = localStorage.getItem("cv_builder_api_url") || "http://127.0.0.1:8000";
let sessionId = localStorage.getItem("cv_builder_session_id") || "";

// Voice recording state
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

apiBaseInput.value = apiBaseUrl;
sessionIdLabel.textContent = sessionId || "Not started";

function setResponse(data) {
  responseBox.textContent = JSON.stringify(data, null, 2);
}

function setPreview(data) {
  previewBox.textContent = JSON.stringify(data, null, 2);
}

function setContext(data) {
  contextBox.textContent = JSON.stringify(data, null, 2);
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${apiBaseUrl}${path}`, options);
  const contentType = res.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await res.json();
  }

  return await res.blob();
}

saveBaseUrlBtn.addEventListener("click", () => {
  apiBaseUrl = apiBaseInput.value.trim();
  localStorage.setItem("cv_builder_api_url", apiBaseUrl);
  setResponse({ message: "API base URL saved", apiBaseUrl });
});

startSessionBtn.addEventListener("click", async () => {
  const data = await apiFetch("/session/start", {
    method: "POST"
  });

  sessionId = data.session_id;
  localStorage.setItem("cv_builder_session_id", sessionId);
  sessionIdLabel.textContent = sessionId;
  chatStatus.textContent = "Active";
  setResponse(data);

  chatMessages.innerHTML = "";
  addMessage("bot", data.question || "Session started");
});

answerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!sessionId) {
    setResponse({ error: "Start a session first" });
    return;
  }

  const answer = answerInput.value.trim();
  if (!answer) return;

  addMessage("user", answer);
  answerInput.value = "";

  const data = await apiFetch("/session/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_id: sessionId,
      answer
    })
  });

  setResponse(data);
  if (data.cv_data) {
    setPreview(data.cv_data);
  }
  if (data.retrieved_context) {
    setContext(data.retrieved_context);
  }

  if (data.followup_question) {
    addMessage("bot", data.followup_question);
  } else if (data.question) {
    addMessage("bot", data.question);
  } else if (data.message) {
    addMessage("bot", data.message);
  }
});

if (voiceBtn) {
  voiceBtn.addEventListener("click", async () => {
    if (!sessionId) {
      setResponse({ error: "Start a session first" });
      alert("Please start a session first");
      return;
    }

    // If not currently recording, start recording
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            recordedChunks.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(recordedChunks, { type: "audio/webm" });

          chatStatus.textContent = "Processing (voice)...";
          addMessage("bot", "Processing your voice answer...");

          try {
            const formData = new FormData();
            formData.append("file", audioBlob, "voice.webm");
            formData.append("session_id", sessionId);

            const res = await fetch(`${apiBaseUrl}/speech/transcribe`, {
              method: "POST",
              body: formData
            });

            const payload = await res.json();
            
            // Extract transcript from response
            const transcript = payload.raw_transcript || payload.normalized_transcript || payload.transcript || payload.text || payload.result;

            if (transcript) {
              answerInput.value = transcript;
              addMessage("bot", "✅ Transcript captured. Review it and click Send to submit.");
            } else {
              addMessage("bot", "Could not capture your voice. Please try again or type your answer.");
            }
          } catch (error) {
            console.error("Error processing voice input:", error);
            addMessage("bot", "❌ Error processing voice input. You can type your answer instead.");
          } finally {
            chatStatus.textContent = sessionId ? "Active" : "Idle";
            voiceBtn.disabled = false;
            voiceBtn.textContent = "🎤";
          }
        };

        mediaRecorder.start();
        isRecording = true;

        voiceBtn.textContent = "⏺️";
        chatStatus.textContent = "Recording (voice)...";
        addMessage("bot", "Recording... click the Voice button again to stop and send.");
      } catch (error) {
        console.error("Error starting microphone:", error);
        setResponse({ error: "Could not access microphone", details: error.message });
        alert("Could not access microphone. Check browser permissions.");
      }

      return;
    }

    // If already recording, stop and trigger onstop handler to send audio
    if (isRecording && mediaRecorder) {
      isRecording = false;
      voiceBtn.disabled = true;
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    }
  });
}



getPreviewBtn.addEventListener("click", async () => {
  if (!sessionId) {
    setResponse({ error: "Start a session first" });
    return;
  }

  const data = await apiFetch(`/preview/${sessionId}`);
  setResponse(data);
  setPreview(data.preview || data);
});

console.log("Attaching getValidationBtn event listener");
getValidationBtn.addEventListener("click", async () => {
  console.log("Get Validation button clicked");
  if (!sessionId) {
    const errorMsg = { error: "Start a session first" };
    setResponse(errorMsg);
    alert("Please start a session first");
    return;
  }

  try {
    console.log(`Fetching validation for session: ${sessionId}`);
    const data = await apiFetch(`/validation/${sessionId}`);
    console.log("Validation data received:", data);
    setResponse(data);
  } catch (error) {
    console.error("Error fetching validation:", error);
    setResponse({ error: "Failed to fetch validation", details: error.message });
  }
});

console.log("Attaching getContextBtn event listener");
getContextBtn.addEventListener("click", async () => {
  console.log("Get Retrieval Context button clicked");
  try {
    const query = answerInput.value.trim() || "skills";
    console.log(`Fetching context for query: ${query}`);
    const data = await apiFetch(`/retrieval/context?query=${encodeURIComponent(query)}`);
    console.log("Context data received:", data);
    setResponse(data);
    setContext(data.results || []);
  } catch (error) {
    console.error("Error fetching context:", error);
    setResponse({ error: "Failed to fetch context", details: error.message });
  }
});

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!cvFile.files.length) {
    setResponse({ error: "Choose a file first" });
    return;
  }

  // Show visual loading/processing state
  const originalText = uploadForm.querySelector("button[type='submit']")?.textContent || "Upload and Merge CV";
  const submitButton = uploadForm.querySelector("button[type='submit']");
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Processing...";
  }
  chatStatus.textContent = "Processing CV upload...";
  addMessage("bot", "Processing uploaded CV, please wait...");

  try {
    const formData = new FormData();
    formData.append("file", cvFile.files[0]);
    if (sessionId) {
      formData.append("session_id", sessionId);
    }

    const res = await fetch(`${apiBaseUrl}/cv/upload`, {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    setResponse(data);
    if (data.cv_data) {
      setPreview(data.cv_data);
      addMessage("bot", "✅ Uploaded CV parsed and merged into current session.");
    } else if (data.error) {
      addMessage("bot", `⚠️ CV upload failed: ${data.error}`);
    }
  } catch (error) {
    console.error("Error during CV upload:", error);
    setResponse({ error: "Failed to upload and merge CV", details: error.message });
    addMessage("bot", "❌ Error while processing CV upload. Please try again.");
  } finally {
    // Reset loading state
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = originalText;
    }
    chatStatus.textContent = sessionId ? "Active" : "Idle";
  }
});

downloadDocxBtn.addEventListener("click", () => {
  if (!sessionId) {
    setResponse({ error: "Start a session first" });
    return;
  }
  window.open(`${apiBaseUrl}/export/docx/${sessionId}`, "_blank");
});

downloadPdfBtn.addEventListener("click", () => {
  if (!sessionId) {
    setResponse({ error: "Start a session first" });
    return;
  }
  window.open(`${apiBaseUrl}/export/pdf/${sessionId}`, "_blank");
});

console.log("Attaching resetSessionBtn event listener");
resetSessionBtn.addEventListener("click", async () => {
  console.log("Reset Demo button clicked");
  const confirmReset = confirm("Are you sure you want to reset the demo? This will clear all session data.");
  if (!confirmReset) {
    console.log("Reset cancelled by user");
    return;
  }

  try {
    if (sessionId) {
      console.log(`Deleting session: ${sessionId}`);
      const response = await fetch(`${apiBaseUrl}/session/${sessionId}`, { method: "DELETE" });
      const data = await response.json();
      console.log("Server response:", data);
      setResponse(data);
    } else {
      console.log("No active session to delete");
    }
    
    sessionId = "";
    localStorage.removeItem("cv_builder_session_id");
    sessionIdLabel.textContent = "Not started";
    chatMessages.innerHTML = "";
    previewBox.textContent = "{}";
    responseBox.textContent = "{}";
    contextBox.textContent = "[]";
    chatStatus.textContent = "Idle";
    answerInput.value = "";
    cvFile.value = "";
    
    addMessage("bot", "✅ Demo reset successfully. Click 'Start Session' to begin again.");
    setResponse({ message: "Demo reset successfully", timestamp: new Date().toISOString() });
    console.log("Reset completed successfully");
  } catch (error) {
    console.error("Error during reset:", error);
    setResponse({ error: "Failed to reset session", details: error.message });
    alert("Error resetting session. Check console for details.");
  }
});
