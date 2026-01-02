import base64
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types


# =================================================================
# GEMINI_API_KEY = "AIzaSyA_xTDkSb4bsYCgnoCFKWbnmyUAU2QygpA"
# run command $env:GEMINI_API_KEY="AIzaSyA_xTDkSb4bsYCgnoCFKWbnmyUAU2QygpA"
# =================================================================

# --- Ρυθμίσεις Flask ---
app = Flask(__name__)
# Ενεργοποίηση CORS για επικοινωνία με το React frontend
CORS(app) 

# --- Ρυθμίσεις Gemini ---
client = None
try:
    # Ο client θα πάρει αυτόματα το κλειδί από την μεταβλητή περιβάλλοντος GEMINI_API_KEY
    client = genai.Client()
    print("SUCCESS: Gemini Client initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini Client. Details: {e}")

@app.route("/test_chat", methods=["POST"])
def ask():
    full_reply = ""
    data = request.json
    prompt = data.get("prompt","hello")
    model = "gemini-robotics-er-1.5-preview"
    contents = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_text(text=prompt),
        ],
    ),
]
    tools = [
    types.Tool(googleSearch=types.GoogleSearch(
    )),
]
    generate_content_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
    ),
    tools=tools,
)

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
):
        if(chunk.text):
            full_reply +=chunk.text

    return jsonify({"answer": full_reply})
        


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask backend running! Test endpoint: /test_chat (GET)"})

if __name__ == "__main__":
    # Τρέχουμε τον server στην διεύθυνση http://127.0.0.1:5000/
    # Το debug=False είναι σωστό για να μην έχουμε προβλήματα με το κλειδί
    app.run(debug=False)