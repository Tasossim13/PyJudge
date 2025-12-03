import os
from flask import Flask, jsonify
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

@app.route("/test_chat", methods=["GET"])
def test_chat():
    """
    Στέλνει ένα απλό prompt στο Gemini χωρίς περιορισμούς και επιστρέφει την απάντηση.
    """
    if not client:
        return jsonify({"error": "Gemini API Client failed to initialize. Check GEMINI_API_KEY environment variable."}), 500
    
    try:
        # Απλό, χαλαρό prompt για να εξασφαλίσουμε απάντηση
        prompt = "Απάντησε με μια τυπική φράση χαιρετισμού, όπως 'Καλησπέρα'."
        
        # Κλήση του Gemini API χωρίς το config για να μην μπλοκάρει η απάντηση
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )
        
        # Ελέγχουμε αν υπάρχει κείμενο στην απάντηση
        if response.text:
            answer = response.text.strip()
        else:
            # Χειρισμός σφάλματος αν το μοντέλο μπλοκάρει
            if response.candidates and response.candidates[0].finish_reason.name == 'SAFETY':
                block_reason = response.candidates[0].finish_reason.name
                answer = f"Αποτυχία απάντησης λόγω κανόνων ασφαλείας. Δοκιμάστε διαφορετικό prompt."
            else:
                 # Γενικό σφάλμα αν δεν υπάρχει κείμενο
                 answer = "Αποτυχία απάντησης: Το μοντέλο δεν επέστρεψε κείμενο."
        
        return jsonify({"result": answer})
        
    except APIError as e:
        # Χειρισμός σφαλμάτων API
        print(f"Gemini API Error: {e}")
        return jsonify({"error": f"Gemini API Error: {str(e)}"}), 500
    except Exception as e:
        # Χειρισμός άλλων σφαλμάτων
        print(f"General Error: {e}")
        return jsonify({"error": f"General Server Error: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask backend running! Test endpoint: /test_chat (GET)"})

if __name__ == "__main__":
    # Τρέχουμε τον server στην διεύθυνση http://127.0.0.1:5000/
    # Το debug=False είναι σωστό για να μην έχουμε προβλήματα με το κλειδί
    app.run(debug=False)