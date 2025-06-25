from flask import Flask, render_template, request, redirect, session
import json
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 🔒 Session should expire on browser close
app.config['SESSION_PERMANENT'] = False
app.permanent_session_lifetime = timedelta(minutes=30)  # Optional: logout after 30 mins of idle

# ✅ Load or Create users.json
if os.path.exists("users.json"):
    with open("users.json", "r") as f:
        users = json.load(f)
else:
    users = {}

# 🏠 Home Route
@app.route('/')
def home():
    return render_template("home.html")

# 📝 Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        preparation = request.form['preparation']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']

        if email in users:
            return "⚠️ Email already exists. Try logging in."

        users[email] = {
            "name": name,
            "preparation": preparation,
            "mobile": mobile,
            "password": password,
            "picture": ""
        }

        with open("users.json", "w") as f:
            json.dump(users, f, indent=4)

        return redirect('/login')

    return render_template('signup.html')

# 🔐 Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.get(email)
        if user and user['password'] == password:
            session['user'] = email
            session.permanent = False  # 🔒 Session ends on browser close
            return redirect('/dashboard')
        else:
            return "❌ Invalid email or password."

    return render_template('login.html')

# 🚪 Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# 👤 Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return redirect('/search')
    else:
        return redirect('/login')

# 🔍 Search Page Route
@app.route('/search', methods=['GET'])
def search_page():
    if 'user' not in session:
        return redirect('/login')

    if os.path.exists("quizzes.json"):
        with open("quizzes.json", "r") as f:
            quiz_data = json.load(f)
    else:
        quiz_data = {}

    return render_template('search.html', quiz_data=quiz_data)

# 🔍 Search Quiz Submission
@app.route('/search_quiz', methods=['POST'])
def search_quiz():
    subject = request.form['subject']
    part = request.form['part']
    section = request.form['section']
    return redirect(f"/quiz/{subject}/{part}/{section}")

# 📥 Load Quiz Data
@app.route('/quiz/<subject>/<part>/<section>', methods=["GET", "POST"])
def section_quiz(subject, part, section):
    if 'user' not in session:
        return redirect('/login')

    if os.path.exists("quizzes.json"):
        with open("quizzes.json", "r") as f:
            quizzes = json.load(f)
    else:
        return "❌ No quizzes found."

    quiz_data = quizzes.get(subject, {}).get(part, {}).get(section, [])

    if request.method == "POST":
        user_answers = []
        score = 0

        for i, q in enumerate(quiz_data):
            selected = request.form.get(f"q{i}")
            user_answers.append(selected)
            if selected == q["answer"]:
                score += 1

        result = {
            "user": session['user'],
            "subject": f"{subject} → {part} → {section}",
            "score": score,
            "total": len(quiz_data),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if os.path.exists("results.json"):
            with open("results.json", "r") as f:
                results = json.load(f)
        else:
            results = []

        results.append(result)
        with open("results.json", "w") as f:
            json.dump(results, f, indent=4)

        return render_template("result.html", score=score, total=len(quiz_data))

    return render_template("quiz.html", quiz=quiz_data, quiz_title=f"{subject} / {part} / {section}", time_limit=10)

# 📄 History Route
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    user_email = session['user']

    if os.path.exists("results.json"):
        with open("results.json", "r") as f:
            all_results = json.load(f)
    else:
        all_results = []

    user_results = [res for res in all_results if res["user"] == user_email]

    return render_template("history.html", results=user_results)

# 📊 Leaderboard Route
@app.route('/leaderboard')
def leaderboard():
    if not os.path.exists("results.json"):
        return "No results yet."

    with open("results.json", "r") as f:
        all_results = json.load(f)

    leaderboard_scores = {}
    for result in all_results:
        user = result["user"]
        leaderboard_scores[user] = leaderboard_scores.get(user, 0) + result["score"]

    sorted_leaderboard = sorted(leaderboard_scores.items(), key=lambda x: x[1], reverse=True)

    return render_template("leaderboard.html", leaderboard=sorted_leaderboard)

# 👤 Profile Page
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')

    email = session['user']
    user = users.get(email)

    if request.method == 'POST':
        user['name'] = request.form['name']
        user['preparation'] = request.form['preparation']
        user['mobile'] = request.form['mobile']

        if 'picture' in request.files:
            picture_file = request.files['picture']
            if picture_file and picture_file.filename != "":
                filename = secure_filename(picture_file.filename)
                picture_path = os.path.join("static/profiles", filename)
                picture_file.save(picture_path)
                user['picture'] = filename

        users[email] = user
        with open("users.json", "w") as f:
            json.dump(users, f, indent=4)

        return redirect('/profile')

    return render_template('profile.html', user=user)

# 🔐 Admin Login Route
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':
            session['admin'] = True
            return redirect('/admin/add_quiz')
        else:
            return "❌ Wrong admin password"
    return render_template('admin_login.html')

# ➕ Add Quiz Route
@app.route('/admin/add_quiz', methods=['GET', 'POST'])
def add_quiz():
    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':
        subject = request.form['subject']
        part = request.form['part']
        section = request.form['section']
        question = request.form['question']
        options = request.form.getlist('options')
        answer = request.form['answer']

        if os.path.exists("quizzes.json"):
            with open("quizzes.json", "r") as f:
                quizzes = json.load(f)
        else:
            quizzes = {}

        quizzes.setdefault(subject, {}).setdefault(part, {}).setdefault(section, []).append({
            "question": question,
            "options": options,
            "answer": answer
        })

        with open("quizzes.json", "w") as f:
            json.dump(quizzes, f, indent=4)

        return "✅ Quiz added successfully!"

    return render_template("add_quiz.html")

# 🟢 Run the App
if __name__ == '__main__':
    app.run(debug=True)
