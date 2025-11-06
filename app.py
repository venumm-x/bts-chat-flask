from flask import Flask, render_template, request, jsonify, send_file, session
from openai import OpenAI
import os, datetime
from werkzeug.utils import secure_filename
from flask_session import Session

app = Flask(__name__, static_folder="static", template_folder="templates")

app.secret_key = "btsuniversekey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
LOG_FOLDER = os.path.join(app.static_folder, "logs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-your_api_key_here"))

CHARACTERS = {
    "jungkook": "You are Jungkook — playful, confident, and caring.",
    "jimin": "You are Jimin — gentle, sweet, and affectionate.",
    "v": "You are V — artistic, poetic, and mysterious.",
    "rm": "You are RM — thoughtful and wise.",
    "jin": "You are Jin — funny, confident, and caring.",
    "suga": "You are Suga — calm, honest, and supportive.",
    "jhope": "You are J-Hope — bright, energetic, and positive.",
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat")
def chat():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session["session_file"] = f"chat_{timestamp}.html"
    log_path = os.path.join(LOG_FOLDER, session["session_file"])

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"""<html><head><meta charset='UTF-8'>
        <title>BTS Chat Log</title>
        <style>
        body{{font-family:Poppins,sans-serif;background:#0d0d12;color:#f0e6ff;padding:20px;}}
        .user,.bot{{padding:10px;border-radius:10px;margin:10px 0;max-width:70%;word-wrap:break-word;}}
        .user{{background:#373753;float:right;clear:both;}}
        .bot{{background:#242437;float:left;clear:both;}}
        img{{border-radius:10px;max-width:200px;}}
        .time{{font-size:0.8rem;opacity:0.7;}}
        </style></head><body>
        <h2>💜 BTS Chat Session — {timestamp}</h2><hr>
        """)
    return render_template("chat.html")


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    message = data.get("message", "")
    character = data.get("character", "jungkook").lower()
    prompt = CHARACTERS.get(character, CHARACTERS["jungkook"])

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
        max_tokens=60,
        temperature=0.8,
    )
    reply = completion.choices[0].message.content.strip()

    save_chat_html(character, message, reply)
    return jsonify({"reply": reply})


@app.route("/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
    file = request.files["image"]
    character = request.form.get("character", "jungkook").lower()

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    image_url = f"../static/uploads/{filename}"
    prompt = CHARACTERS.get(character, CHARACTERS["jungkook"])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt} React naturally to the user's uploaded photo."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Here's the uploaded image."},
                        {"type": "image_url", "image_url": {"url": f"http://127.0.0.1:5000/static/uploads/{filename}"}},
                    ],
                },
            ],
            max_tokens=60,
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception:
        ai_reply = "That looks amazing! 💜"

    save_chat_html(character, f"[Image uploaded: {filename}]", ai_reply, image_url)
    return jsonify({"url": f"/static/uploads/{filename}", "reply": ai_reply})


def save_chat_html(character, user_msg, reply, image_url=None):
    if "session_file" not in session or not session["session_file"].endswith(".html"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session["session_file"] = f"chat_{timestamp}.html"

    log_path = os.path.join(LOG_FOLDER, session["session_file"])
    time_now = datetime.datetime.now().strftime("%I:%M %p")

    with open(log_path, "a", encoding="utf-8") as f:
        if image_url:
            f.write(f"<div class='user'><b>You:</b><br><img src='{image_url}'><div class='time'>{time_now}</div></div>\n")
        else:
            f.write(f"<div class='user'><b>You:</b> {user_msg}<div class='time'>{time_now}</div></div>\n")
        f.write(f"<div class='bot'><b>{character.title()}:</b> {reply}<div class='time'>{time_now}</div></div>\n")


@app.route("/download/<character>")
def download_chat(character):
    if "session_file" not in session:
        return "No chat session yet!", 404

    log_path = os.path.join(LOG_FOLDER, session["session_file"])
    if not os.path.exists(log_path):
        return "No chat found!", 404

    with open(log_path, "r+", encoding="utf-8") as f:
        content = f.read()
        if not content.strip().endswith("</body></html>"):
            f.write("</body></html>")

    return send_file(
        log_path,
        as_attachment=True,
        download_name=session["session_file"],
        mimetype="text/html"
    )


if __name__ == "__main__":
    app.run(debug=True)
