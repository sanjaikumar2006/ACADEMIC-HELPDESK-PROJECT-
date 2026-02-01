// ================= BASIC ELEMENTS =================
const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
const voiceBtn = document.getElementById("voice-btn");

// ================= ADD MESSAGE =================
function addMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("chat-msg", sender === "bot" ? "bot-msg" : "user-msg");
    msgDiv.innerText = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ================= SEND MESSAGE (TEXT) =================
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage("user", message);
    userInput.value = "";

    try {
        const res = await fetch("/get_response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });

        const data = await res.json();
        addMessage("bot", data.reply);
        speakText(data.reply);   // 🔊 bot voice reply

    } catch (err) {
        addMessage("bot", "❌ Server error. Please try again.");
    }
}

// Button & Enter key
sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});

// ================= VOICE RECOGNITION =================
const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;

    voiceBtn.addEventListener("click", () => {
        voiceBtn.classList.add("listening");
        recognition.start();
    });

    recognition.onresult = (event) => {
        const voiceText = event.results[0][0].transcript;
        userInput.value = voiceText;
        sendMessage();
    };

    recognition.onend = () => {
        voiceBtn.classList.remove("listening");
    };

    recognition.onerror = () => {
        voiceBtn.classList.remove("listening");
        addMessage("bot", "🎤 Voice recognition error.");
    };
} else {
    voiceBtn.disabled = true;
    voiceBtn.title = "Voice not supported in this browser";
}

// ================= TEXT TO SPEECH (BOT VOICE) =================
function speakText(text) {
    if (!window.speechSynthesis) return;

    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-IN";
    speech.rate = 1;
    speech.pitch = 1;
    window.speechSynthesis.speak(speech);
}
