import doctest
import zipfile
import shutil
import importlib.util
import os
import sys
from groq import Groq
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from grade import grade_submission, check_restrictions
from flask import jsonify, send_file

# --- Ρυθμίσεις Flask ---
app = Flask(__name__)
CORS(app) 

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.1-8b-instant"


# --- Βοηθητική Συνάρτηση Grader---
def run_doctests(test_text, student_code_text):
    try:
        # 1. Δημιουργία του προσωρινού αρχείου hw2.py
        with open("hw2.py", "w", encoding="utf-8") as f:
            f.write(student_code_text)

        # 2. Καθαρισμός του test_text
        # Αφαιρούμε το 'from hw2 import *' και τυχόν κενές γραμμές που μπερδεύουν το doctest
        lines = test_text.splitlines()
        clean_lines = [l for l in lines if "from hw2 import" not in l and l.strip() != ""]
        test_text = "\n".join(clean_lines)

        # 3. Φόρτωση του Module hw2
        module_name = "hw2"
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, "hw2.py")
        student_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = student_module
        spec.loader.exec_module(student_module)

        # 4. Χρήση Parser για μεγαλύτερη ακρίβεια
        parser = doctest.DocTestParser()
        # Globs: δίνουμε πρόσβαση στις συναρτήσεις του φοιτητή
        test_env = {name: getattr(student_module, name) for name in dir(student_module)}
        
        # Δημιουργία του test αντικειμένου από το κείμενο
        test = parser.get_doctest(test_text, test_env, "manual_test", "hw2.py", 0)
        runner = doctest.DocTestRunner(optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
        
        # Εκτέλεση
        runner.run(test)
        results = runner.summarize()

        return {
            "failed": results.failed,
            "attempted": results.attempted,
            "passed": results.attempted - results.failed
        }
    except Exception as e:
        print(f"GRADER CRITICAL ERROR: {e}")
        return {"error": str(e), "failed": 0, "attempted": 0, "passed": 0}

# --- Routes ---
@app.route("/evaluate", methods=["POST"])
def evaluate():
    if "student" not in request.files:
        return jsonify({"error": "missing student file"}), 400
    
    # Λήψη των αρχείων από το αίτημα
    student_file = request.files.get("student")
    exercise_file = request.files.get("exercise")
    solution_file = request.files.get("solution")
    prompt_extra = request.form.get("prompt", "")

    # Δυναμικός προσδιορισμός ονόματος βάσει του solution file
    test_filename = solution_file.filename
    module_name = test_filename.split('_')[0].replace('.txt', '')
    expected_name = f"{module_name}.py"

    temp_dir = os.path.abspath("temp_eval")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    student_path = os.path.join(temp_dir, expected_name)
    test_path = os.path.join(temp_dir, test_filename)

    # Αποθήκευση των αρχείων
    student_file.save(student_path)
    solution_file.save(test_path)

    # Ανάγνωση κώδικα
    with open(student_path, "r", encoding="utf-8", errors="ignore") as f:
        student_code = f.read()

    auto_fix_applied = False
    
    # --- AUTO-FIX LOGIC ---
    try:
        check_restrictions(student_code)
    except Exception as e:
        # Αν υπάρχει SyntaxError, το Gemini Robotics αναλαμβάνει τη διόρθωση
        repair_prompt = f"Ο κώδικας έχει συντακτικό λάθος: {e}. Διόρθωσε ΜΟΝΟ τη σύνταξη (εσοχές κτλ) για να τρέξει. Επίστρεψε ΜΟΝΟ τον κώδικα.\n\n{student_code}"
        
        try:
            repair_res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.1
            )
            repaired_code = repair_res.choices[0].message.content.replace("```python", "").replace("```", "").strip()
            with open(student_path, "w", encoding="utf-8") as f:
                f.write(repaired_code)
            
            student_code = repaired_code
            auto_fix_applied = True
        except:
            pass # Αν αποτύχει το repair, συνεχίζουμε με τον αρχικό κώδικα

    # --- ΕΚΤΕΛΕΣΗ GRADER ---
    # Καλούμε τον Grader με τα σωστά paths
    test_results = grade_submission(test_path, student_path)

    if test_results.get('status') == 'Success':
        total = test_results['summary']['total_tests']
        passed = test_results['summary']['passed']
        failed = test_results['summary']['failed']
        final_grade = test_results['summary']['grade'] 
        details = test_results.get('details', 'Κανένα σφάλμα.')
    else:
        total = passed = failed = final_grade = 0
        details = f"Σφάλμα Grader: {test_results.get('message', 'Άγνωστο σφάλμα')}"

    # --- ΠΕΝΑΛΤΙ ΠΕΡΙΟΡΙΣΜΩΝ ---
    try:
        func_violations = check_restrictions(student_code)
        if "print_digits" in func_violations and total > 0:
            exercise_10_tests = 5 
            penalty_applied = (exercise_10_tests / total) * 10
            final_grade = round(max(0, final_grade - penalty_applied), 2)
    except:
        pass

    # --- ΤΕΛΙΚΟ PROMPT ---
    fullPrompt = f"""
    Είσαι ένας αυστηρός αλλά δίκαιος βοηθός καθηγητή Python. 
    Η βαθμολόγηση βασίζεται ΑΠΟΚΛΕΙΣΤΙΚΑ στα doctests.

    ΔΕΔΟΜΕΝΑ:
    - Βαθμολογία: {final_grade}/10 ({passed}/{total} επιτυχίες)
    - Αυτόματη διόρθωση σύνταξης: {'Ναι' if auto_fix_applied else 'Όχι'}

    ΚΩΔΙΚΑΣ ΦΟΙΤΗΤΗ:
    {student_code}

    ΛΕΠΤΟΜΕΡΕΙΕΣ ΣΦΑΛΜΑΤΩΝ:
    {details}

    ΟΔΗΓΙΕΣ:
    1. Ξεκίνα με τη βαθμολογία..
    2. Αν έγινε auto-fix, εξήγησε στον φοιτητή ότι ο κώδικάς του είχε συντακτικά λάθη.
    3. Δώσε hints για τις αποτυχίες.
    4. Θελω το φορματ της απαντησης σου να ειναι επαγγελματικο με στοιχιση, διαχωριστικα με παυλες γιατι θα παει κατευθειαν στον φοιτητη.
    """
    
    # --- ΚΛΗΣΗ ΓΙΑ FEEDBACK ---
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": fullPrompt}],
            temperature=0.5
        )
        return jsonify({
            "answer": response.choices[0].message.content, 
            "auto_grade": test_results
        })
    except Exception as e:
        return jsonify({"answer": f"Βαθμός: {final_grade}/10. (AI Feedback Error)", "error": str(e)})

@app.route("/evaluate_bulk", methods=["POST"])
def evaluate_bulk():
    zip_file = request.files.get("students_zip")
    solution_file = request.files.get("solution")
    
    if not zip_file or not solution_file:
        return jsonify({"error": "Missing ZIP or Solution file"}), 400

    test_filename = solution_file.filename
    module_to_check = test_filename.split('_')[0].replace('.txt', '')
    expected_py_name = module_to_check + ".py"

    base_dir = os.path.abspath("bulk_work")
    extract_path = os.path.join(base_dir, "extracted")
    
    if os.path.exists(base_dir): shutil.rmtree(base_dir)
    os.makedirs(extract_path)

    zip_path = os.path.join(base_dir, "upload.zip")
    test_path = os.path.join(base_dir, test_filename)
    zip_file.save(zip_path)
    solution_file.save(test_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_path)
    except:
        return jsonify({"error": "Invalid ZIP"}), 400

    # --- LOOP ΑΞΙΟΛΟΓΗΣΗΣ ---
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                student_py_path = os.path.join(root, file)
                target_path = os.path.join(root, expected_py_name)

                if student_py_path != target_path:
                    if os.path.exists(target_path): os.remove(target_path)
                    os.rename(student_py_path, target_path)
                    student_py_path = target_path

                with open(student_py_path, "r", encoding="utf-8", errors="ignore") as f:
                    student_code = f.read()

                func_violations = {}
                syntax_error_msg = ""
                auto_fix_applied = False

                # --- 1. AUTO-FIX ΜΕ GROQ ---
                try:
                    func_violations = check_restrictions(student_code)
                except Exception as syntax_err:
                    repair_prompt = f"""
                    Ο παρακάτω κώδικας Python έχει συντακτικό σφάλμα: {syntax_err}. 
                    Διόρθωσε ΜΟΝΟ τα συντακτικά λάθη (εσοχές, παρενθέσεις) ώστε να εκτελεστεί.
                    Επίστρεψε ΜΟΝΟ τον διορθωμένο κώδικα χωρίς markdown.
                    ΚΩΔΙΚΑΣ: {student_code}
                    """
                    try:
                        # Χρήση Groq για Auto-Fix
                        repair_res = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[{"role": "user", "content": repair_prompt}],
                            temperature=0.1
                        )
                        repaired_code = repair_res.choices[0].message.content.replace("```python", "").replace("```", "").strip()
                        
                        with open(student_py_path, "w", encoding="utf-8") as f:
                            f.write(repaired_code)
                        
                        student_code = repaired_code
                        auto_fix_applied = True
                        syntax_error_msg = "\n(Σημείωση: Ο κώδικας διορθώθηκε αυτόματα από το AI.)"
                        func_violations = check_restrictions(student_code)
                    except Exception as ai_err:
                        syntax_error_msg = f"\nΠΡΟΣΟΧΗ: Συντακτικό λάθος. Η διόρθωση απέτυχε: {ai_err}"

                # --- 2. ΕΚΤΕΛΕΣΗ GRADER ---
                test_results = grade_submission(test_path, student_py_path)

                if test_results.get('status') == 'Success':
                    total = test_results['summary']['total_tests']
                    passed = test_results['summary']['passed']
                    final_grade = test_results['summary']['grade']
                    details = test_results.get('details', 'No errors.')
                else:
                    total = passed = final_grade = 0
                    details = f"Grader Error: {test_results.get('message', 'Unknown')}"

                # Πέναλτι
                if "print_digits" in func_violations and total > 0:
                    exercise_10_tests = 5 
                    penalty_applied = (exercise_10_tests / total) * 10
                    final_grade = round(max(0, final_grade - penalty_applied), 2)

                # --- 3. FEEDBACK ΜΕ GROQ ---
                fullPrompt = f"""
                Είσαι βοηθός καθηγητή Python. 
                Βαθμολογία: {final_grade}/10 ({passed}/{total} επιτυχίες)
                Auto-fix: {'ΝΑΙ' if auto_fix_applied else 'ΟΧΙ'}
                {syntax_error_msg}
                Κώδικας: {student_code}
                Σφάλματα: {details}
                
                ΟΔΗΓΙΕΣ: 
                Ξεκίνα με τη βαθμολογία. Δώσε hints στα Ελληνικά. 
                Αν έγινε Auto-Fix, ενημέρωσε τον φοιτητή οτι εγινε Auto-Fix ωστε να μπορεσουν να τρεξουν οι ασκησεις.
                """

                try:
                    # Χρήση Groq για Feedback
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": fullPrompt}],
                        temperature=0.5
                    )
                    ai_answer = response.choices[0].message.content
                except:
                    ai_answer = f"Τελικός Βαθμός: {final_grade}/10. (AI feedback unavailable)"

                feedback_filename = f"feedback_{file.replace('.py', '.txt')}"
                with open(os.path.join(root, feedback_filename), "w", encoding="utf-8") as f_out:
                    f_out.write(ai_answer)

    # --- 4. ZIP RESULTS ---
    output_zip_name = "graded_results"
    output_zip_path = os.path.join(base_dir, output_zip_name)
    shutil.make_archive(output_zip_path, 'zip', extract_path)

    return send_file(f"{output_zip_path}.zip", as_attachment=True)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask backend running! Test endpoint: /test_chat (GET)"})

# --- Main Entry Point ---
if __name__ == "__main__":
    # Τρέχουμε τον server. Η run_doctests είναι ήδη ορισμένη παραπάνω.
    app.run(debug=False)