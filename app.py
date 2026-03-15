from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import base64
import pickle
import numpy as np
import cv2
import os
from datetime import datetime
from functools import wraps

# ================== CONFIG ==================
app = Flask(__name__)
app.secret_key = "vel_tech_secret_key_2024" # Required for sessions

# ================== ACADEMIC TIMETABLE ==================
# Overall attendance is strictly 08:15 to 09:00
# Subject periods follow a standard day-order
TIMETABLE = {
    "Overall Attendance": {"start": "08:15", "end": "09:00"},
    "Python Programming": {"start": "09:00", "end": "10:00"},
    "Data Structures": {"start": "10:00", "end": "11:00"},
    "Machine Learning": {"start": "11:15", "end": "12:15"},
    "Cloud Computing": {"start": "12:15", "end": "13:15"},
    "Ethics & Values": {"start": "14:00", "end": "15:00"},
    "Mathematics IV": {"start": "15:00", "end": "16:00"}
}

def is_within_time_window(subject):
    if subject not in TIMETABLE:
        return True, "" # Default to true for unscheduled things
    
    now = datetime.now().strftime("%H:%M")
    start = TIMETABLE[subject]["start"]
    end = TIMETABLE[subject]["end"]
    
    if start <= now <= end:
        return True, ""
    
    if now < start:
        return False, f"Too early! {subject} starts at {start}."
    else:
        return False, f"Too late! {subject} window was {start} to {end}."

# Dummy Admin Credentials (In a real app, store hashed in DB)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function

# ================== AUTH ROUTES ==================
@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASS:
        session["logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("home"))


# ================== FACE RECOGNITION CONFIG ==================
# ... (rest of the config)
# Try to import face_recognition (requires dlib/cmake)
# If it fails, we use OpenCV's built-in Haar Cascades and LBPH
try:
    import face_recognition
    USE_FACE_RECOGNITION = True
    print("[INFO] Using high-accuracy face_recognition library.")
except ImportError:
    USE_FACE_RECOGNITION = False
    print("[WARNING] face_recognition not found. Using OpenCV Fallback.")

# Path to OpenCV Face Detection model (included with opencv-python)
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)

# ================== EMOTION DETECTION ==================
def detect_emotion(text):
    text = text.lower()

    emotions = {
        "Happy 😄": ["happy", "good", "great", "awesome", "excited", "love"],
        "Sad 😢": ["sad", "down", "depressed", "lonely", "cry"],
        "Angry 😡": ["angry", "mad", "hate", "irritated", "annoyed"],
        "Stressed 😟": ["stress", "stressed", "tension", "pressure", "worried", "exam"],
        "Confused 😕": ["confused", "dont understand", "no idea", "doubt"]
    }

    detected_emotions = []

    for emotion, keywords in emotions.items():
        if any(word in text for word in keywords):
            detected_emotions.append(emotion)

    if detected_emotions:
        return ", ".join(detected_emotions)

    return "Neutral 😐"


# ================== DATABASE ==================
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Chat history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_reply TEXT
        )
    """)

    # Student face registration table
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            face_encoding BLOB NOT NULL,
            registered_at TEXT
        )
    """)

    # Attendance table (Subject-Wise & Biometric)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            student_name TEXT,
            roll_number TEXT,
            subject TEXT,
            date TEXT,
            time TEXT,
            status TEXT DEFAULT 'Present',
            captured_face BLOB,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    # Notices table
    c.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            posted_at TEXT
        )
    """)

    conn.commit()
    conn.close()

# ================== NOTICES ROUTES ==================
@app.route("/get_notices")
def get_notices():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT content, posted_at FROM notices ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"content": r[0], "date": r[1]} for r in rows])

@app.route("/post_notice", methods=["POST"])
@login_required
def post_notice():
    content = request.json.get("content")
    if not content:
        return jsonify({"success": False})
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO notices (content, posted_at) VALUES (?, ?)", 
              (content, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ================== HOME ==================
@app.route("/")
def home():
    return render_template("index.html")


# ================== ATTENDANCE PAGES ==================
@app.route("/register")
@login_required
def register_page():
    return render_template("register.html")


@app.route("/attendance")
def attendance_page():
    return render_template("attendance.html")


@app.route("/report")
@login_required
def report_page():
    return render_template("report.html")


# ================== EXTRA FEATURES ==================
@app.route("/gpa")
def gpa_page():
    return render_template("gpa.html")

@app.route("/student_view")
def student_view_page():
    return render_template("student_profile.html")


# ================== CHATBOT DATA ==================
SUGGESTIONS = ["About College", "Courses", "Placements", "Admissions", "Hostel", "Attendance Rules"]

RESPONSES = {
    # Greetings
    "hi": "👋 Hi! Welcome to VEL TECH HIGH TECH College Academic Helpdesk.",
    "hello": "👋 Hello! This is VEL TECH HIGH TECH College AI Academic Assistant.",
    "hey": "😊 Hey! How can I help you with VEL TECH HIGH TECH College today?",
    "bye": "👋 Goodbye! Feel free to come back for more info about VEL TECH HIGH TECH College.",
    "how are you": "😊 I’m doing great and ready to help you with VEL TECH HIGH TECH College info.",

    # College Info
    "college": "🏫 VEL TECH HIGH TECH College of Engineering and Technology, Chennai – NAAC A+ accredited, affiliated to Anna University.",
    "vision": "🎯 Vision: To empower students with innovative education and real-world exposure.",
    "mission": "🚀 Mission: To deliver excellence in education, ethics, and employability.",
    "principal": "👨‍🏫 Principal: Dr.E.Kamalanaban, Ph.D., with 28 years of experience.",
    "chairman": "👔 Chairman: Col.Prof.Dr.Vel.Shri.R.Rangarajan.",
    "established": "📅 Established in 2002 in Aavadi, Chennai.",
    "code": "🆔 Anna University College Code is 2710.",
    "accreditation": "🏆 Accredited by NAAC A+ and NBA for major departments.",

    # Academics
    "academic": "📚 VEL TECH maintains high academic standards with continuous assessment and mentoring.",
    "attendance": "🕒 Minimum 75% attendance is required for semester exams.",
    "semester": "🗓️ The college follows the Anna University CBCS semester system.",
    "exam": "📝 End semester exams are conducted by Anna University. Result on COE portal.",
    "internal": "📊 Internal marks are based on cycle tests, assignments, and lab work.",
    "mentoring": "👩‍🏫 Each student is assigned a mentor for academic and personal support.",

    # Placements
    "placement": "💼 92% placement rate with top recruiters like TCS, Infosys, Wipro, and Zoho.",
    "package": "💰 Average salary package is around ₹4 LPA, with the highest exceeding ₹10 LPA.",
    "training": "🧠 Placement training (aptitude & soft skills) starts from the 2nd year.",

    # Courses
    "course": "🎓 UG & PG programs available: CSE, AI & DS, IT, ECE, EEE, MECH, CIVIL, MBA, MCA.",
    "cse": "💻 Computer Science & Engineering focuses on AI, Data Science, and Software Development.",
    "ai": "🤖 Artificial Intelligence & Data Science focuses on ML, Deep Learning, and Analytics.",

    # Facilities
    "library": "📚 Central Library open from 8:00 AM to 8:00 PM with huge digital resources.",
    "hostel": "🏠 Separate hostels for boys and girls with Wi-Fi, mess, and 24/7 security.",
    "transport": "🚌 College buses cover all major areas of Chennai and suburbs.",
    "wifi": "🌐 High-speed Wi-Fi available across the campus.",
    "canteen": "🍽️ Hygienic canteen serving healthy food for students.",

    # Discipline
    "discipline": "⚖️ Strict discipline is maintained. Uniform and ID cards are mandatory.",
    "ragging": "🚫 Ragging is strictly prohibited as per UGC norms.",

    # Admissions
    "admission": "📥 Admissions available via Anna University (TNEA) counselling and management quota.",
    "eligibility": "🎓 Eligibility criteria follow Anna University and AICTE norms.",
    "scholarship": "🎓 Government and merit-based scholarships are supported.",

    "default": "🤖 Sorry, I didn’t get that. Try asking about courses, faculty, placements, or admissions!"
}

# ================== CHATBOT LOGIC ==================
def chatbot_logic(user_message):
    user_message = user_message.lower().strip()
    emotion = detect_emotion(user_message)
    
    # Check for academic keywords
    reply = None
    for key, response in RESPONSES.items():
        if key in user_message:
            reply = response
            break
    
    # Logic Fix: Combine emotion and academic reply
    if reply:
        if emotion != "Neutral 😐":
            return f"🧠 Detected Emotion: {emotion}\n\n{reply}"
        return reply
    
    if emotion != "Neutral 😐":
        return f"🧠 Detected Emotion: {emotion}"

    return RESPONSES["default"]

@app.route("/get_suggestions")
def get_suggestions():
    return jsonify(SUGGESTIONS)


# ================== TEXT CHAT ==================
@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.json.get("message", "")
    bot_reply = chatbot_logic(user_message)

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (user_message, bot_reply) VALUES (?, ?)",
        (user_message, bot_reply)
    )
    conn.commit()
    conn.close()

    return jsonify({"reply": bot_reply})


# ================== CHAT HISTORY ==================
@app.route("/get_chat_history")
def get_chat_history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT user_message, bot_reply FROM messages ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    
    # Return in reverse order (oldest first for display)
    history = [{"user": r[0], "bot": r[1]} for r in reversed(rows)]
    return jsonify(history)


# ================== DASHBOARD STATS ==================
@app.route("/get_stats")
def get_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
    present_today = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": max(0, total_students - present_today)
    })


@app.route("/bulk_register", methods=["POST"])
@login_required
def bulk_register():
    data = request.json.get("students", [])
    if not data:
        return jsonify({"success": False, "message": "No student data provided."})
    
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    count = 0
    for s in data:
        name = s.get("name")
        roll = s.get("roll")
        if name and roll:
            # Check if exists
            c.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
            if not c.fetchone():
                c.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)", (name, roll))
                count += 1
    
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Successfully imported {count} students."})


# ================== VOICE CHAT ==================
@app.route("/voice_chat", methods=["POST"])
def voice_chat():
    user_message = request.json.get("message", "")
    bot_reply = chatbot_logic(user_message)
    return jsonify({"reply": bot_reply})


# ================== ATTENDANCE API ==================
@app.route("/register_student", methods=["POST"])
def register_student():
    try:
        data = request.json
        name = data.get("name")
        roll = data.get("roll")
        image_data = data.get("image")

        if not name or not roll or not image_data:
            return jsonify({"success": False, "message": "Missing name, roll number, or image."})

        # Decode base64 image
        header, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if USE_FACE_RECOGNITION:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_img)
            if not face_locations:
                return jsonify({"success": False, "message": "No face detected. Please try again."})
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            encoding_to_save = face_encodings[0]
        else:
            # OpenCV Fallback Detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Try detection with multiple settings for sensitivity
            # Setting 1: Standard
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
            
            # Setting 2: If failed, try with equalization and more sensitivity
            if len(faces) == 0:
                gray_eq = cv2.equalizeHist(gray)
                faces = face_cascade.detectMultiScale(gray_eq, 1.05, 3, minSize=(80, 80))
                if len(faces) > 0:
                    gray = gray_eq
            
            if len(faces) == 0:
                return jsonify({"success": False, "message": "No face detected. Please ensure you are in a well-lit area and looking directly at the camera."})
            
            # Take the largest face found
            faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            # Resize to standard size
            encoding_to_save = cv2.resize(face_roi, (150, 150))

        encoding_blob = pickle.dumps(encoding_to_save)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO students (name, roll_number, face_encoding, registered_at) VALUES (?, ?, ?, ?)",
                (name, roll, encoding_blob, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            return jsonify({"success": True, "message": f"Successfully registered {name}!"})
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Roll number already registered."})
        finally:
            conn.close()

    except Exception as e:
        print(f"Error in registration: {e}")
        return jsonify({"success": False, "message": "Error during registration. Check lighting."})


@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    try:
        data = request.json
        encoded = data.get("image")
        selected_subject = data.get("subject", "Overall Attendance")

        # 🕒 Check Time Window FIRST
        is_valid, time_msg = is_within_time_window(selected_subject)
        if not is_valid:
            return jsonify({"success": False, "message": time_msg})

        if not encoded:
            return jsonify({"success": False, "message": "No image data received."})

        # Decode base64 image
        header, encoded_base64 = encoded.split(",", 1)
        image_bytes = base64.b64decode(encoded_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, name, roll_number, face_encoding FROM students")
        known_students = c.fetchall()
        conn.close()

        if not known_students:
            return jsonify({"success": False, "message": "Database empty. Please register first."})

        if USE_FACE_RECOGNITION:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_img)
            if not face_locations:
                return jsonify({"success": False, "message": "Face not detected clearly."})
            current_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            
            known_encodings = [pickle.loads(s[3]) for s in known_students]
            
            for current_encoding in current_encodings:
                matches = face_recognition.compare_faces(known_encodings, current_encoding, tolerance=0.6)
                if True in matches:
                    match_index = matches.index(True)
                    return record_attendance(known_students[match_index], encoded_base64, selected_subject)
        else:
            # Enhanced OpenCV Fallback Matching
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Multi-pass detection sensitivity
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
            if len(faces) == 0:
                gray_eq = cv2.equalizeHist(gray)
                faces = face_cascade.detectMultiScale(gray_eq, 1.05, 3, minSize=(80, 80))
                if len(faces) > 0:
                    gray = gray_eq

            if len(faces) == 0:
                return jsonify({"success": False, "message": "Face not found. Keep steady and ensure sufficient lighting."})
            
            # Use largest face
            faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
            x, y, w, h = faces[0]
            current_face = cv2.resize(gray[y:y+h, x:x+w], (150, 150))

            best_match = None
            max_val = -1 # Higher correlation is better

            for student in known_students:
                stored_face = pickle.loads(student[3])
                
                # Verify it's an image block and not a high-level encoding
                if not isinstance(stored_face, np.ndarray) or stored_face.shape != (150, 150):
                    continue
                
                # Template matching (Correlation)
                res = cv2.matchTemplate(current_face, stored_face, cv2.TM_CCOEFF_NORMED)
                _, val, _, _ = cv2.minMaxLoc(res)
                
                if val > max_val:
                    max_val = val
                    best_match = student

            # Correlation threshold (0.5 to 0.7 is usually good for face patterns)
            if best_match and max_val > 0.65:
                return record_attendance(best_match, encoded_base64, selected_subject)

        return jsonify({"success": False, "message": "Face not matched. Try again or re-register."})

    except Exception as e:
        print(f"Error in attendance scan: {e}")
        return jsonify({"success": False, "message": "System Error. Stabilize the image."})

@app.route("/face_login", methods=["POST"])
def face_login():
    try:
        data = request.json
        encoded = data.get("image")
        if not encoded:
            return jsonify({"success": False, "message": "No image data."})

        header, encoded_base64 = encoded.split(",", 1)
        image_bytes = base64.b64decode(encoded_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, name, roll_number, face_encoding FROM students")
        known_students = c.fetchall()
        conn.close()

        if USE_FACE_RECOGNITION:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_img)
            if not face_locations:
                return jsonify({"success": False, "message": "No face detected."})
            current_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            known_encodings = [pickle.loads(s[3]) for s in known_students]
            
            for current_encoding in current_encodings:
                matches = face_recognition.compare_faces(known_encodings, current_encoding, tolerance=0.6)
                if True in matches:
                    match_index = matches.index(True)
                    return jsonify({"success": True, "roll": known_students[match_index][2]})
        else:
            # OpenCV Fallback
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
            if len(faces) > 0:
                faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
                x, y, w, h = faces[0]
                current_face = cv2.resize(gray[y:y+h, x:x+w], (150, 150))
                best_match = None
                max_val = -1
                for student in known_students:
                    stored_face = pickle.loads(student[3])
                    if not isinstance(stored_face, np.ndarray): continue
                    res = cv2.matchTemplate(current_face, stored_face, cv2.TM_CCOEFF_NORMED)
                    _, val, _, _ = cv2.minMaxLoc(res)
                    if val > max_val:
                        max_val = val
                        best_match = student
                if best_match and max_val > 0.65:
                    return jsonify({"success": True, "roll": best_match[2]})

        return jsonify({"success": False, "message": "Identity not verified. Unrecognized face."})
    except Exception as e:
        return jsonify({"success": False, "message": f"System Error: {str(e)}"})

def record_attendance(student_data, image_b64, subject):
    student_id, name, roll, _ = student_data
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # Updated: Check if already present FOR THIS SUBJECT today
    c.execute("SELECT id FROM attendance WHERE student_id = ? AND date = ? AND subject = ?", (student_id, today, subject))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "message": f"Already marked for {subject}."})

    now = datetime.now()
    c.execute(
        "INSERT INTO attendance (student_id, student_name, roll_number, subject, date, time, captured_face) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (student_id, name, roll, subject, today, now.strftime("%H:%M:%S"), image_b64)
    )
    conn.commit()
    conn.close()
    return jsonify({
        "success": True, 
        "message": f"Welcome {name}! Attendance for {subject} recorded.",
        "student_name": name
    })


@app.route("/get_attendance")
def get_attendance():
    date = request.args.get("date")
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    subject_filter = request.args.get("subject")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # 1. Total unique class days so far (Global)
    c.execute("SELECT COUNT(DISTINCT date) FROM attendance")
    total_class_days = c.fetchone()[0] or 1 
    
    # 2. Get all registered students
    c.execute("SELECT id, name, roll_number FROM students")
    all_students = c.fetchall()
    
    # 3. Get total present count for ALL time per student
    c.execute("SELECT student_id, COUNT(DISTINCT date) FROM attendance GROUP BY student_id")
    all_time_present = {row[0]: row[1] for row in c.fetchall()}

    # 4. Get present students for THIS specific date and potentially THIS subject
    if subject_filter:
        c.execute("SELECT student_id, time, captured_face, subject FROM attendance WHERE date = ? AND subject = ?", (date, subject_filter))
    else:
        c.execute("SELECT student_id, time, captured_face, subject FROM attendance WHERE date = ?", (date,))
    
    present_rows = c.fetchall()
    
    present_data = {}
    for row in present_rows:
        sid, time, face, subject = row
        face_str = face.decode('utf-8') if (face and isinstance(face, bytes)) else face
        if sid not in present_data: present_data[sid] = []
        present_data[sid].append({"time": time, "face": face_str, "subject": subject})
    
    conn.close()

    results = []
    for student_id, name, roll in all_students:
        present_days = all_time_present.get(student_id, 0)
        percentage = round((present_days / total_class_days) * 100, 1)

        if student_id in present_data:
            # We take the record that matches the filter or the most recent
            rec = present_data[student_id][-1]
            results.append({
                "name": name,
                "roll": roll,
                "date": date,
                "time": rec["time"],
                "subject": rec["subject"],
                "status": "Present",
                "face": rec["face"],
                "percentage": percentage
            })
        else:
            results.append({
                "name": name,
                "roll": roll,
                "date": date,
                "time": "-",
                "subject": subject_filter if subject_filter else "-",
                "status": "Absent",
                "face": None,
                "percentage": percentage
            })
            
    # Sort: Present first, then roll number
    results.sort(key=lambda x: (x["status"] != "Present", x["roll"]))
    
    return jsonify(results)

@app.route("/student_profile/<roll>")
def student_profile(roll):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # Get student info
    c.execute("SELECT id, name FROM students WHERE roll_number = ?", (roll,))
    student = c.fetchone()
    
    if not student:
        conn.close()
        return jsonify({"success": False, "message": "Student not found."})
    
    student_id, name = student
    
    # Get total days class was held (unique dates in attendance table)
    c.execute("SELECT COUNT(DISTINCT date) FROM attendance")
    total_class_days = c.fetchone()[0] or 1 # Avoid division by zero
    
    # Get student's present days
    c.execute("SELECT date, time FROM attendance WHERE student_id = ? ORDER BY date DESC", (student_id,))
    history = c.fetchall()
    present_days = len(history)
    
    percentage = round((present_days / total_class_days) * 100, 1)
    
    conn.close()
    
    return jsonify({
        "success": True,
        "name": name,
        "roll": roll,
        "percentage": percentage,
        "present_count": present_days,
        "total_days": total_class_days,
        "history": [{"date": h[0], "time": h[1]} for h in history]
    })


# ================== MAIN ==================
import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
