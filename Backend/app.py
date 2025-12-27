import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai.errors import APIError

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
    data= request.json
    prompt = data.get("prompt","")
    print("Prompt: ", prompt)
    reply = f"Prompt Received.../{prompt}"

    return jsonify({"answer": reply})


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask backend running! Test endpoint: /test_chat (GET)"})

if __name__ == "__main__":
    # Τρέχουμε τον server στην διεύθυνση http://127.0.0.1:5000/
    # Το debug=False είναι σωστό για να μην έχουμε προβλήματα με το κλειδί
    app.run(debug=False)