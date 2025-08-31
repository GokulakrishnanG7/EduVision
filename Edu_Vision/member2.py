# member2.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

# 🔹 Load .env file
load_dotenv()

# 🔹 Configure Gemini with API key from .env
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 🔹 Use Gemini Flash for higher free-tier quotas
MODEL_NAME = "gemini-1.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

def explain_text(text: str):
    """
    Generate a student-friendly explanation + glossary for input text.
    Handles quota errors gracefully.
    Returns:
    - 📄 Simplified Explanation
    - 📝 Key Points
    - 💡 Example/Analogy
    - glossary: {term: simple meaning}
    """
    prompt = f"""
    You are EduVision AI, a teaching assistant.
    Read the content below and generate a structured explanation and glossary.

    Content:
    {text}

    Format the response exactly like this:
    📄 Simplified Explanation: <clear explanation in simple words>

    📝 Key Points:
    - <point 1>
    - <point 2>
    - <point 3>

    💡 Example/Analogy:
    <short example or analogy if possible; if not, say "Not applicable">

    Glossary:
    - <term 1>: <short simple meaning>
    - <term 2>: <short simple meaning>
    """

    try:
        response = model.generate_content(prompt)
        explanation = response.text.strip() if response and response.text else "⚠️ No response from model."

        # 🔹 Parse glossary lines like "- term: meaning"
        glossary = {}
        for line in explanation.splitlines():
            if line.startswith("- ") and ":" in line:
                term, meaning = line[2:].split(":", 1)
                glossary[term.strip()] = meaning.strip()

    except Exception as e:
        # 🔹 Handle quota errors and other exceptions
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower():
            explanation = "⚠️ Too many requests! Gemini Flash free-tier quota reached. Please wait a moment or try again later."
        else:
            explanation = f"⚠️ Error generating explanation: {error_message}"
        glossary = {}

    return {
        "explanation": explanation,
        "glossary": glossary
    }


def handle_voice_command(command: str):
    """
    Handle voice commands like:
    - "Read Science Chapter 2"
    - "Explain photosynthesis"
    Returns the explanation dictionary: {"explanation": ..., "glossary": {...}}
    """
    command = command.lower()

    # --- Case 1: Read a specific file ---
    match_read = re.search(r"read (.+)", command)
    if match_read:
        filename = match_read.group(1).strip().replace(" ", "_") + ".txt"
        file_path = os.path.join("sample_texts", filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return explain_text(text)
        else:
            # fallback to latest sample if specific file not found
            sample_files = sorted([f for f in os.listdir("sample_texts") if f.endswith(".txt")])
            if sample_files:
                with open(os.path.join("sample_texts", sample_files[-1]), "r", encoding="utf-8") as f:
                    text = f.read()
                return explain_text(text)
            else:
                return {"explanation": "⚠️ No files found to read.", "glossary": {}}

    # --- Case 2: Explain a term ---
    match_explain = re.search(r"explain (.+)", command)
    if match_explain:
        term = match_explain.group(1).strip()
        # Just ask Gemini to explain the term
        prompt = f"Explain the term '{term}' in simple words for a student."
        try:
            response = model.generate_content(prompt)
            explanation = response.text.strip() if response and response.text else f"⚠️ Couldn't explain {term}."
        except Exception as e:
            explanation = f"⚠️ Error: {str(e)}"

        return {"explanation": explanation, "glossary": {}}

    return {"explanation": "⚠️ Sorry, I didn't understand your command.", "glossary": {}}
