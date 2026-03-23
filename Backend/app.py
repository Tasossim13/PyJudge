import doctest
import zipfile
import shutil
import importlib.util
import os
import sys
from groq import Groq
import openai
from google import genai
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from grade import grade_submission, check_restrictions
from flask import jsonify, send_file

# --- Ρυθμίσεις Flask ---
app = Flask(__name__)
CORS(app) 


# --- Βοηθητική Συνάρτηση Grader---
def run_doctests(test_text, student_code_text, filename="student_code"):
    try:
        module_name = filename.replace(".py","")
        temp_file = f"{module_name}.py"
        # 1. Δημιουργία του προσωρινού αρχείου 
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(student_code_text)

        # 2. Καθαρισμός του test_text
        # Αφαιρούμε το 'from hw import *' και τυχόν κενές γραμμές που μπερδεύουν το doctest
        lines = test_text.splitlines()
        clean_lines = [l for l in lines if f"from {module_name} import" not in l and l.strip() != ""]
        test_text = "\n".join(clean_lines)


        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, temp_file)
        student_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = student_module
        spec.loader.exec_module(student_module)

        # 4. Χρήση Parser για μεγαλύτερη ακρίβεια
        parser = doctest.DocTestParser()
        # Globs: δίνουμε πρόσβαση στις συναρτήσεις του φοιτητή
        test_env = {name: getattr(student_module, name) for name in dir(student_module)}
        
        # Δημιουργία του test αντικειμένου από το κείμενο
        test = parser.get_doctest(test_text, test_env, "manual_test", temp_file, 0)
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
    # 1. Λήψη δεδομένων και Παρόχου
    provider = request.form.get("provider", "groq") # Default αν δεν σταλεί
    api_key = request.form.get("api_key")
    identities = {
        "openai": "Είσαι το μοντέλο GPT-4o της OpenAI.",
        "gemini": "Είσαι το μοντέλο Gemini 1.5 Flash της Google.",
        "groq": "Είσαι το μοντέλο Llama-3 της Meta, που τρέχει μέσω της Groq."
    }
    current_identity = identities.get(provider, "Είσαι ένας βοηθός καθηγητή.")

    if "student" not in request.files:
        return jsonify({"error": "missing student file"}), 400
    
    student_file = request.files.get("student")
    exercise_file = request.files.get("exercise")
    solution_file = request.files.get("solution")
    
    # Δυναμικός προσδιορισμός ονόματος
    test_filename = solution_file.filename
    module_name = test_filename.split('_')[0].replace('.txt', '')
    expected_name = f"{module_name}.py"

    temp_dir = os.path.abspath("temp_eval")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    student_path = os.path.join(temp_dir, expected_name)
    test_path = os.path.join(temp_dir, test_filename)

    student_file.save(student_path)
    solution_file.save(test_path)

    with open(student_path, "r", encoding="utf-8", errors="ignore") as f:
        student_code = f.read()

    auto_fix_applied = False
    
    # --- AUTO-FIX LOGIC ΜΕ ΕΠΙΛΟΓΗ PROVIDER ---
    try:
        check_restrictions(student_code)
    except Exception as e:
        repair_prompt = f"Ο κώδικας έχει συντακτικό λάθος: {e}. Διόρθωσε ΜΟΝΟ τη σύνταξη (εσοχές κτλ) για να τρέξει. Επίστρεψε ΜΟΝΟ τον κώδικα.\n\n{student_code}"
        
        try:
            repaired_code = None
            if provider == "openai":
                client_ai = openai.OpenAI(api_key=api_key)
                res = client_ai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": repair_prompt}], temperature=0.1)
                repaired_code = res.choices[0].message.content
            elif provider == "gemini":
                genai.configure(api_key=api_key)
                model_ai = genai.GenerativeModel('gemini-1.5-flash')
                res = model_ai.generate_content(repair_prompt)
                repaired_code = res.text
            elif provider == "groq":
                client_ai = Groq(api_key=api_key)
                res = client_ai.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": repair_prompt}], temperature=0.1)
                repaired_code = res.choices[0].message.content

            if repaired_code:
                repaired_code = repaired_code.replace("```python", "").replace("```", "").strip()
                with open(student_path, "w", encoding="utf-8") as f:
                    f.write(repaired_code)
                student_code = repaired_code
                auto_fix_applied = True
        except:
            pass

    # --- ΕΚΤΕΛΕΣΗ GRADER ---
    test_results = grade_submission(test_path, student_path)

    if test_results.get('status') == 'Success':
        total = test_results['summary']['total_tests']
        passed = test_results['summary']['passed']
        final_grade = test_results['summary']['grade'] 
        details = test_results.get('details', 'Κανένα σφάλμα.')
    else:
        total = passed = final_grade = 0
        details = f"Σφάλμα Grader: {test_results.get('message', 'Άγνωστο σφάλμα')}"

    # --- ΠΕΝΑΛΤΙ ΠΕΡΙΟΡΙΣΜΩΝ (CHECK RESTRICTIONS) ---
    try:
        func_violations = check_restrictions(student_code)
        if "print_digits" in func_violations and total > 0:
            penalty_applied = (5 / total) * 10
            final_grade = round(max(0, final_grade - penalty_applied), 2)
    except:
        pass

    # --- ΤΕΛΙΚΟ PROMPT ΓΙΑ FEEDBACK ---
    fullPrompt = f"""
    {current_identity}
    ΟΔΗΓΙΕΣ: 
    1. Ξεκίνα την απάντησή σου γράφοντας ξεκάθαρα: ΜΟΝΤΈΛΟ:{provider.upper()} .
    2. Είσαι αυστηρός βοηθός καθηγητή Python.
    3. Δώσε επαγγελματικό feedback στα Ελληνικά με Hints. Εαν περασε ολα τα τεστ μην γραψεις σχολια, μονο βαθμολογια και ποσα τεστ περασε.
    .
    
    ΔΕΔΟΜΕΝΑ ΑΞΙΟΛΟΓΗΣΗΣ:
    Βαθμολογία: {final_grade}/10
    Επιτυχίες: {passed}/{total}
    Αυτόματη Διόρθωση: {'Ναι' if auto_fix_applied else 'Όχι'}
    
    ΚΩΔΙΚΑΣ ΦΟΙΤΗΤΗ:
    {student_code}

    ΣΦΑΛΜΑΤΑ GRADER:
    {details}
    """
    
    # --- ΚΛΗΣΗ ΓΙΑ ΤΕΛΙΚΟ FEEDBACK ---
    try:
        final_answer = ""
        if provider == "openai":
            client_ai = openai.OpenAI(api_key=api_key)
            res = client_ai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": fullPrompt}], temperature=0.5)
            final_answer = res.choices[0].message.content
        elif provider == "gemini":
            client_gemini = genai.Client(api_key=api_key)
            response = client_gemini.models.generate_content(model="gemini-robotics-er-1.5-preview",contents=fullPrompt)
            final_answer = response.text
        elif provider == "groq":
            client_ai = Groq(api_key=api_key)
            res = client_ai.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": fullPrompt}], temperature=0.5)
            final_answer = res.choices[0].message.content

        return jsonify({"answer": final_answer, "auto_grade": test_results})
    except Exception as e:
        return jsonify({"answer": f"Βαθμός: {final_grade}/10. (AI Error)", "error": str(e)})

@app.route("/evaluate_bulk", methods=["POST"])
def evaluate_bulk():
    # 1. Λήψη API Key και Provider από το Frontend
    api_key = request.form.get("api_key")
    provider = request.form.get("provider", "groq")
    zip_file = request.files.get("students_zip")
    solution_file = request.files.get("solution")
    identities = {
        "openai": "Είσαι το μοντέλο GPT-4o της OpenAI.",
        "gemini": "Είσαι το μοντέλο Gemini 1.5 Flash της Google.",
        "groq": "Είσαι το μοντέλο Llama-3 της Meta, που τρέχει μέσω της Groq."
    }
    current_identity = identities.get(provider, "Είσαι ένας βοηθός καθηγητή.")
    
    if not api_key or not zip_file or not solution_file:
        return jsonify({"error": "Missing API Key, ZIP or Solution file"}), 400

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

                # Rename student file to match test expectations
                if student_py_path != target_path:
                    if os.path.exists(target_path): os.remove(target_path)
                    os.rename(student_py_path, target_path)
                    student_py_path = target_path

                with open(student_py_path, "r", encoding="utf-8", errors="ignore") as f:
                    student_code = f.read()

                func_violations = {}
                syntax_error_msg = ""
                auto_fix_applied = False

                # --- 1. AUTO-FIX LOGIC ---
                try:
                    func_violations = check_restrictions(student_code)
                except Exception as syntax_err:
                    repair_prompt = f"Ο κώδικας Python έχει συντακτικό σφάλμα: {syntax_err}. Διόρθωσε  τη σύνταξη μονο εαν εχει ξεχασει ενα γραμμα η μια παρενθεση,Εαν εχει πολλα συντακτικα και σημαντικα μην πειραξεις κατι, Επίστρεψε ΜΟΝΟ τον κώδικα  οπως ηταν.\n\n{student_code}"
                    
                    try:
                        repaired_code = None
                        if provider == "openai":
                            client_ai = openai.OpenAI(api_key=api_key)
                            res = client_ai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": repair_prompt}], temperature=0.1)
                            repaired_code = res.choices[0].message.content
                        elif provider == "gemini":
                            genai_client = genai.Client(api_key=api_key)
                            res = genai_client.models.generate_content(model="gemini-robotics-er-1.5-preview", contents=repair_prompt)
                            repaired_code = res.text
                        elif provider == "groq":
                            client_ai = Groq(api_key=api_key)
                            res = client_ai.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": repair_prompt}], temperature=0.1)
                            repaired_code = res.choices[0].message.content

                        if repaired_code:
                            repaired_code = repaired_code.replace("```python", "").replace("```", "").strip()
                            with open(student_py_path, "w", encoding="utf-8") as f:
                                f.write(repaired_code)
                            student_code = repaired_code
                            auto_fix_applied = True
                            syntax_error_msg = "\n(Σημείωση: Ο κώδικας διορθώθηκε αυτόματα.)"
                            func_violations = check_restrictions(student_code)
                    except:
                        syntax_error_msg = f"\nΠΡΟΣΟΧΗ: Συντακτικό λάθος. Η διόρθωση απέτυχε."

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

                # Πέναλτι Restrictions
                if "print_digits" in func_violations and total > 0:
                    penalty_applied = (5 / total) * 10
                    final_grade = round(max(0, final_grade - penalty_applied), 2)

                # --- 3. FEEDBACK LOGIC ---
                fullPrompt = f"""
                    {current_identity}
                    ΟΔΗΓΙΕΣ: 
                    1. Ξεκίνα την απάντησή σου γράφοντας ξεκάθαρα: ΜΟΝΤΈΛΟ:{provider.upper()} .
                    2. Είσαι αυστηρος βοηθός καθηγητή Python.
                    3. Δώσε επαγγελματικό feedback στα Ελληνικά με Hints. Εαν περασε ολα τα τεστ μην γραψεις σχολια, μονο βαθμολογια και ποσα τεστ περασε.
                    4. Μην δίνεις επιπλέον βαθμούς για "καλή προσπάθεια". Μείνε πιστός στα test cases.

                    ΔΕΔΟΜΕΝΑ ΑΞΙΟΛΟΓΗΣΗΣ:
                    Βαθμολογία: {final_grade}/10
                    Επιτυχίες: {passed}/{total}
                    Αυτόματη Διόρθωση: {'Ναι' if auto_fix_applied else 'Όχι'}
    
                    ΚΩΔΙΚΑΣ ΦΟΙΤΗΤΗ:
                    {student_code}
                    ΣΦΑΛΜΑΤΑ GRADER:
                    {details}
                    """

                try:
                    ai_answer = ""
                    if provider == "openai":
                        client_ai = openai.OpenAI(api_key=api_key)
                        res = client_ai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": fullPrompt}], temperature=0.5)
                        ai_answer = res.choices[0].message.content
                    elif provider == "gemini":
                        genai_client = genai.Client(api_key=api_key)
                        res = genai_client.models.generate_content(model="gemini-robotics-er-1.5-preview", contents=fullPrompt)
                        ai_answer = res.text
                    elif provider == "groq":
                        client_ai = Groq(api_key=api_key)
                        res = client_ai.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": fullPrompt}], temperature=0.5)
                        ai_answer = res.choices[0].message.content
                except Exception as e:
                    ai_answer = f"Τελικός Βαθμός: {final_grade}/10. (AI feedback unavailable: {str(e)})"

                # Αποθήκευση Feedback σε αρχείο TXT μέσα στο ZIP
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