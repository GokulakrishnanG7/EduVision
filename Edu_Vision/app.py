import os
import tempfile
from flask import Flask, render_template, request, jsonify
from member2 import explain_text  # NLP function
from gtts import gTTS
from langdetect import detect  # For language detection
import google.generativeai as genai

app = Flask(__name__)

# ===== Supported Languages (~50) =====
LANGUAGES = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam",
    "kn": "Kannada", "gu": "Gujarati", "mr": "Marathi", "bn": "Bengali", "pa": "Punjabi",
    "ur": "Urdu", "ne": "Nepali", "si": "Sinhala", "or": "Odia", "as": "Assamese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian", "pt": "Portuguese",
    "nl": "Dutch", "pl": "Polish", "ru": "Russian", "uk": "Ukrainian", "ro": "Romanian",
    "cs": "Czech", "sk": "Slovak", "sl": "Slovenian", "bg": "Bulgarian", "hr": "Croatian",
    "sr": "Serbian", "hu": "Hungarian", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
    "no": "Norwegian", "tr": "Turkish", "el": "Greek", "ar": "Arabic", "fa": "Persian",
    "zh-cn": "Chinese (Simplified)", "zh-tw": "Chinese (Traditional)", "ja": "Japanese",
    "ko": "Korean", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
    "sw": "Swahili", "af": "Afrikaans"
}

# ===== Sample Folder =====
SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), "sample_texts")
os.makedirs(SAMPLE_FOLDER, exist_ok=True)

# ===== Favorites Store (in-memory) =====
favorites_set = set()

# ===== Home Route =====
@app.route("/")
def home():
    return render_template("index.html")

# ===== Explanation Page =====
@app.route("/explanation")
def explanation_page():
    file_name = request.args.get("file")
    if not file_name:
        return "No file specified.", 400
    file_path = os.path.join(SAMPLE_FOLDER, file_name)
    if not os.path.exists(file_path):
        return "File not found.", 404
    return render_template("explanation.html")

# ===== Viewer Page =====
@app.route("/viewer")
def viewer_page():
    file_name = request.args.get("file")
    if not file_name:
        return "No file specified.", 400
    file_path = os.path.join(SAMPLE_FOLDER, file_name)
    if not os.path.exists(file_path):
        return "File not found.", 404
    return render_template("viewer.html", file_name=file_name)

# ===== Translator Page =====
@app.route("/translator")
def translator_page():
    return render_template("translator.html", languages=LANGUAGES)

# ===== Upload Files =====
@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    uploaded_files = request.files.getlist("files")
    file_names = []
    for f in uploaded_files:
        save_path = os.path.join(SAMPLE_FOLDER, f.filename)
        f.save(save_path)
        file_names.append(f.filename)
    return jsonify({"uploaded_files": file_names})

# ===== Text-to-Speech Endpoint =====
@app.route("/speak", methods=["POST"])
def speak_text():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", None)
    if not text:
        return jsonify({"error": "No text provided"}), 400
    try:
        if not lang:
            detected_lang = detect(text)
            lang = detected_lang

        if lang not in LANGUAGES:
            lang = "en"

        tts = gTTS(text=text, lang=lang)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        audio_filename = os.path.basename(temp_file.name)
        static_path = os.path.join("static", "tts")
        os.makedirs(static_path, exist_ok=True)
        saved_path = os.path.join(static_path, audio_filename)
        os.replace(temp_file.name, saved_path)
        audio_url = f"/static/tts/{audio_filename}"
        return jsonify({"audio_url": audio_url, "lang": lang})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== List All Uploaded Files =====
@app.route("/list_files")
def list_files():
    try:
        files = sorted(os.listdir(SAMPLE_FOLDER))
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== Add Favorite =====
@app.route("/add_favorite", methods=["POST"])
def add_favorite():
    data = request.get_json()
    file = data.get("file")
    if file:
        favorites_set.add(file)
        return jsonify({"status": "added"})
    return jsonify({"error": "No file specified"}), 400

# ===== Remove Favorite =====
@app.route("/remove_favorite", methods=["POST"])
def remove_favorite():
    data = request.get_json()
    file = data.get("file")
    if file and file in favorites_set:
        favorites_set.remove(file)
        return jsonify({"status": "removed"})
    return jsonify({"error": "File not in favorites"}), 400

# ===== Get Favorites =====
@app.route("/get_favorites")
def get_favorites():
    return jsonify({"favorites": list(favorites_set)})

# ===== Delete File =====
@app.route("/delete_file", methods=["DELETE"])
def delete_file():
    file_name = request.args.get("file")
    if not file_name:
        return jsonify({"success": False, "error": "No file specified"}), 400

    file_path = os.path.join(SAMPLE_FOLDER, file_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            if file_name in favorites_set:
                favorites_set.remove(file_name)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return jsonify({"success": False, "error": "File not found"}), 404

# ===== Fetch File Content for Frontend =====
@app.route("/get_file_content")
def get_file_content():
    file_name = request.args.get("file")
    target_lang = request.args.get("target_lang", None)
    if not file_name:
        return jsonify({"error": "No file specified"}), 400
    file_path = os.path.join(SAMPLE_FOLDER, file_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        detected_lang = detect(text)
        if target_lang and target_lang in LANGUAGES:
            lang_prompt = f"Translate and explain fully in {LANGUAGES[target_lang]} only."
        else:
            lang_prompt = f"Explain fully in {LANGUAGES.get(detected_lang,'English')} (detected language)."

        final_text = f"{text}\n\nIMPORTANT: {lang_prompt}"
        result = explain_text(final_text)
        explanation = result.get("explanation", "")
        glossary = result.get("glossary", {})

        # Prepare speech language
        speech_lang = target_lang if target_lang in LANGUAGES else detected_lang
        if speech_lang not in LANGUAGES:
            speech_lang = "en"

        TTS_LANG_MAP = {"zh-cn": "zh-CN", "zh-tw": "zh-TW"}
        speech_lang = TTS_LANG_MAP.get(speech_lang, speech_lang)

        # Generate TTS
        try:
            tts = gTTS(text=explanation, lang=speech_lang)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(temp_file.name)
            audio_filename = os.path.basename(temp_file.name)
            static_path = os.path.join("static", "tts")
            os.makedirs(static_path, exist_ok=True)
            saved_path = os.path.join(static_path, audio_filename)
            os.replace(temp_file.name, saved_path)
            audio_url = f"/static/tts/{audio_filename}"
        except Exception:
            audio_url = None

        return jsonify({
            "file_name": file_name,
            "text": text,
            "explanation": explanation,
            "glossary": glossary,
            "lang": speech_lang,
            "audio_url": audio_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== Summarize + Translate + Speak (for Translator page) =====
@app.route("/api/summarize_translate_speak", methods=["POST"])
def summarize_translate_speak():
    data = request.get_json()
    text = data.get("text", "")
    target_lang = data.get("target_lang", "en")
    voice_engine = data.get("voice_engine", "online")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = explain_text(text)
        summary = result.get("explanation", "")
        translated = summary

        if target_lang != "en":
            translated_prompt = f"Translate the following text to {LANGUAGES.get(target_lang,target_lang)}:\n\n{summary}"
            translated_result = explain_text(translated_prompt)
            translated = translated_result.get("explanation", summary)

        audio_url = None
        speech_lang = target_lang if target_lang in LANGUAGES else "en"
        TTS_LANG_MAP = {"zh-cn": "zh-CN", "zh-tw": "zh-TW"}
        speech_lang = TTS_LANG_MAP.get(speech_lang, speech_lang)
        try:
            if voice_engine == "online":
                tts = gTTS(text=translated, lang=speech_lang)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                tts.save(temp_file.name)
                audio_filename = os.path.basename(temp_file.name)
                static_path = os.path.join("static", "tts")
                os.makedirs(static_path, exist_ok=True)
                saved_path = os.path.join(static_path, audio_filename)
                os.replace(temp_file.name, saved_path)
                audio_url = f"/static/tts/{audio_filename}"
        except Exception:
            audio_url = None

        return jsonify({
            "summary": summary,
            "translated": translated,
            "audio_url": audio_url,
            "lang": speech_lang
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
