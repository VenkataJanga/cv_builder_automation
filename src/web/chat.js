const CHAT_URL = 'http://localhost:8000/chat';
const chatDiv = document.getElementById('chat');
const messageInput = document.getElementById('message');
const sendBtn = document.getElementById('send');

function addBubble(text, role = 'bot') {
  const el = document.createElement('div');
  el.className = `bubble ${role}`;
  el.textContent = text;
  chatDiv.appendChild(el);
  chatDiv.scrollTop = chatDiv.scrollHeight;
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;
  addBubble(message, 'user');
  messageInput.value = '';
  try {
    const res = await fetch(CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: 'mvp1-session-1' })
    });
    if (!res.ok) {
      addBubble(`Error ${res.status}`, 'bot');
      return;
    }
    const data = await res.json();
    addBubble(data.bot || 'No bot response', 'bot');
  } catch (error) {
    addBubble('Network error: ' + error.message, 'bot');
  }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});