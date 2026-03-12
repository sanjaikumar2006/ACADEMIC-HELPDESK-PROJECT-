# 🎓 Academic Chatbot with Face Attendance 

## Features
- 💬 AI-powered academic chatbot for VEL TECH HIGH TECH College
- 😊 Emotion detection (happy, sad, stressed, etc.)
- 🎤 Voice input & 🔊 text-to-speech bot replies
- 📷 Face Detection Attendance System (webcam-based)
- 📊 Attendance report with date filter

## Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
> **Note**: `face_recognition` requires `cmake` and `dlib`.  
> On Windows run: `pip install cmake` before installing `face_recognition`.

### 2. Start the App
```bash
python app.py
```

### 3. Open in Browser
```
http://127.0.0.1:5000
```

## Pages
| URL | Description |
|-----|-------------|
| `/` | Academic Chatbot |
| `/register` | Register student face |
| `/attendance` | Mark attendance via webcam |
| `/report` | View attendance records |

## Tech Stack
- **Backend**: Python, Flask, SQLite
- **Face Recognition**: OpenCV, face_recognition (dlib)
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Speech**: Web Speech API (voice input + TTS)

## Developed By
Students of VEL TECH HIGH TECH College of Engineering & Technology  
© 2025 Academic Helps
