// ================= BASIC ELEMENTS =================
const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
const voiceBtn = document.getElementById("voice-btn");
const clearBtn = document.getElementById("clear-chat");
const typingIndicator = document.getElementById("typing-indicator");
const suggestionsContainer = document.getElementById("suggestions-container");

// ================= ADD MESSAGE =================
function addMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("chat-msg", sender === "bot" ? "bot-msg" : "user-msg");
    msgDiv.classList.add("animate-in");

    // Process text to support some formatting if needed (like newlines)
    msgDiv.innerHTML = text.replace(/\n/g, "<br>");

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ================= TYPING INDICATOR =================
function showTyping() {
    typingIndicator.classList.remove("hidden");
    chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
    typingIndicator.classList.add("hidden");
}

// ================= SUGGESTIONS =================
async function loadSuggestions() {
    try {
        const res = await fetch("/get_suggestions");
        const suggestions = await res.json();
        suggestionsContainer.innerHTML = "";
        suggestions.forEach(suggestion => {
            const chip = document.createElement("div");
            chip.classList.add("suggestion-chip");
            chip.innerText = suggestion;
            chip.onclick = () => {
                userInput.value = suggestion;
                sendMessage();
            };
            suggestionsContainer.appendChild(chip);
        });
    } catch (err) {
        console.error("Failed to load suggestions", err);
    }
}

// ================= SEND MESSAGE (TEXT) =================
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage("user", message);
    userInput.value = "";

    showTyping();

    try {
        const res = await fetch("/get_response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });

        const data = await res.json();
        hideTyping();
        addMessage("bot", data.reply);
        speakText(data.reply);   // 🔊 bot voice reply

    } catch (err) {
        hideTyping();
        addMessage("bot", "❌ Server error. Please try again.");
    }
}

// Button & Enter key
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (userInput) {
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}

// Clear Chat
if (clearBtn) {
    clearBtn.addEventListener("click", () => {
        chatBox.innerHTML = `
            <div class="chat-msg bot-msg animate-in">
              💬 Chat cleared! How can I help you?
            </div>
        `;
        window.speechSynthesis.cancel();
    });
}

// ================= VOICE RECOGNITION =================
const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition && voiceBtn) {
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
} else if (voiceBtn) {
    voiceBtn.disabled = true;
    voiceBtn.title = "Voice not supported in this browser";
}

// ================= TEXT TO SPEECH (BOT VOICE) =================
function speakText(text) {
    if (!window.speechSynthesis) return;

    // Stop any existing speech
    window.speechSynthesis.cancel();

    // Clean text for better speech (remove some emojis if they cause issues)
    const cleanText = text.replace(/[^\x00-\x7F]/g, "").trim();
    if (!cleanText) return;

    const speech = new SpeechSynthesisUtterance(cleanText);
    speech.lang = "en-IN";
    speech.rate = 1;
    speech.pitch = 1;
    window.speechSynthesis.speak(speech);
}

// ================= CHAT HISTORY =================
async function loadChatHistory() {
    try {
        const res = await fetch("/get_chat_history");
        const history = await res.json();

        if (history.length > 0) {
            // Keep only the last message for initial view if history is too long
            // Or show all. Let's show all relevant recent ones.
            history.forEach(item => {
                addMessage("user", item.user);
                addMessage("bot", item.bot);
            });
        }
    } catch (err) {
        console.error("Failed to load chat history", err);
    }
}

// ================= NOTICES =================
async function loadNotices() {
    const bar = document.getElementById("notice-bar");
    const container = document.getElementById("notice-content");
    if (!bar || !container) return;

    try {
        const res = await fetch("/get_notices");
        const notices = await res.json();

        if (notices.length > 0) {
            bar.style.display = "block";
            container.innerHTML = "";
            notices.forEach(n => {
                const item = document.createElement("span");
                item.className = "notice-item";
                item.innerHTML = `<span class="badge-news">Notice</span> ${n.content} (${n.date})`;
                container.appendChild(item);
            });
            // Re-clone items if needed for continuous loop but CSS animation does the basic job
        }
    } catch (err) {
        console.error("Notice fetch failed", err);
    }
}

// Initialize
window.onload = () => {
    if (suggestionsContainer) loadSuggestions();
    if (chatBox) loadChatHistory();
    loadNotices();
};
