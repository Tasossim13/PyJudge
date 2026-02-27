from contextlib import redirect_stdout
import doctest
import importlib.util
import os
import sys
import io
import ast

def check_restrictions(student_code):
    # Μετατρέπουμε τον κώδικα σε δέντρο (AST) για ακριβεια
    tree = ast.parse(student_code)
    code_violations = {}
    
    for node in ast.walk(tree):
        # Ψάχνουμε για ορισμούς συναρτήσεων
        if isinstance(node, ast.FunctionDef):
            # Μέσα στη συνάρτηση, ψάχνουμε για loops
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.For, ast.While)):
                    code_violations[node.name] = True 
    return code_violations # Επιστρέφει π.χ. {'print_digits': True}

def grade_submission(doctest_txt_path, student_py_path):
    test_file_name = os.path.basename(doctest_txt_path)
    module_name = test_file_name.split('_')[0]
    
    # 1. Καθαρισμός προηγούμενων φορτώσεων
    if module_name in sys.modules:
        del sys.modules[module_name]
        
    f_buffer = io.StringIO()
    try:
        # 2. Φόρτωση του κώδικα του φοιτητή
        spec = importlib.util.spec_from_file_location(module_name, student_py_path)
        student_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = student_module
        spec.loader.exec_module(student_module)
        
        # 3. Ρύθμιση του Parser
        # Χρησιμοποιούμε NORMALIZE_WHITESPACE για να μην κόβει στα κενά των print (π.χ. Άσκηση 6)
        # Χρησιμοποιούμε ELLIPSIS για να είναι πιο ευέλικτο σε μεγάλες εξόδους
        parser = doctest.DocTestParser()
        test_env = {name: getattr(student_module, name) for name in dir(student_module)}
        
        # Διαβάζουμε το αρχείο των tests
        with open(doctest_txt_path, 'r', encoding='utf-8') as t_file:
            test_content = t_file.read()

        # Δημιουργία και εκτέλεση του test
        test = parser.get_doctest(test_content, test_env, "student_test", doctest_txt_path, 0)
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
        )
        
        with redirect_stdout(f_buffer):
            runner.run(test)
        
        results = runner.summarize()
        output_details = f_buffer.getvalue()
        
        passed = results.attempted - results.failed
        grade = (passed / results.attempted * 10) if results.attempted > 0 else 0

        return {
            "summary": {
                "total_tests": results.attempted,
                "passed": passed,
                "failed": results.failed,
                "grade": round(grade, 2)
            },
            "details": output_details,
            "status": "Success"
        }
    except Exception as e:
        return {"status": "Error", "message": str(e), "details": str(e)}
    
    