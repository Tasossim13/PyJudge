import zipfile
import os
import re

def extract_grade(text, provider=""):
    """
    Αναβαθμισμένη αναζήτηση βαθμού. 
    Δίνει προτεραιότητα στη λέξη 'Βαθμός' για να μην μπερδεύεται με τα Tracebacks.
    """
    # 1. Πρώτη προτεραιότητα: Η λέξη 'Βαθμός' (όπως στο παράδειγμα του καθηγητή)
    match = re.search(r'Βαθμός:\s*(\d+[\.,]?\d*)', text)
    if match:
        return float(match.group(1).replace(',', '.'))
    
    # 2. Δεύτερη προτεραιότητα: Το κλασικό X/10 (για τα AI)
    match = re.search(r'(\d+[\.,]?\d*)\s*/\s*10', text)
    if match:
        return float(match.group(1).replace(',', '.'))
    
    # 3. Τρίτη προτεραιότητα: Score ή Grade
    match = re.search(r'(?:Score|Grade|Βαθμολογία)\s*:?\s*(\d+[\.,]?\d*)', text, re.IGNORECASE)
    if match:
        val = float(match.group(1).replace(',', '.'))
        if val <= 10: return val

    # 4. Fallback για τον καθηγητή: Ο τελευταίος αριθμός 0-10 που εμφανίζεται στο τέλος του κειμένου
    if provider == "PROFESSOR_TEST":
        numbers = re.findall(r'\b\d+[\.,]?\d*\b', text)
        if numbers:
            last_num = float(numbers[-1].replace(',', '.'))
            if 0 <= last_num <= 10: return last_num
                
    return None

def generate_visual_report():
    zips = [f for f in os.listdir('.') if f.endswith('.zip')]
    all_data = {}
    providers = set()

    for z_path in zips:
        p_name = z_path.replace('results_', '').replace('.zip', '').upper()
        providers.add(p_name)
        
        try:
            with zipfile.ZipFile(z_path, 'r') as z:
                for m in z.namelist():
                    if m.endswith('.txt') and 'MACOSX' not in m:
                        parts = m.split('/')
                        s_id = parts[-2] if len(parts) >= 2 else parts[0].replace('.txt', '')
                        s_id = s_id.replace('feedback_', '').replace('_hw1_bare', '').replace('_hw1', '')
                        
                        if s_id not in all_data: all_data[s_id] = {}
                        
                        content = z.read(m).decode('utf-8', errors='ignore')
                        all_data[s_id][p_name] = content.replace('\n', '<br>')
            print(f"Ανάλυση: {z_path}")
        except Exception as e:
            print(f"Σφάλμα: {e}")

    # Στατιστικά για το γράφημα
    chart_labels = []
    chart_values = []
    sorted_providers = sorted(list(providers))
    if 'PROFESSOR_TEST' in sorted_providers:
        sorted_providers.insert(0, sorted_providers.pop(sorted_providers.index('PROFESSOR_TEST')))

    for p in sorted_providers:
        grades = []
        for s_id in all_data:
            if p in all_data[s_id]:
                g = extract_grade(all_data[s_id][p], p)
                if g is not None: grades.append(g)
        
        avg = round(sum(grades) / len(grades), 2) if grades else 0
        chart_labels.append(p)
        chart_values.append(avg)

    # --- HTML & CHART.JS ---
    html_header = """<!DOCTYPE html><html lang="el"><head><meta charset="UTF-8">
    <title>AI vs Professor Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: #0b0e11; color: #ced4da; padding: 40px; font-family: 'Inter', sans-serif; }
        .chart-box { background: #15191d; border: 1px solid #2d3238; border-radius: 15px; padding: 30px; margin-bottom: 50px; }
        .student-card { background: #15191d; border-radius: 12px; padding: 25px; margin-bottom: 35px; border: 1px solid #2d3238; }
        .student-title { color: #4dabf7; font-size: 1.2rem; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid #2d3238; padding-bottom: 10px; }
        .provider-label { font-size: 0.7rem; font-weight: 800; color: #6c757d; text-transform: uppercase; margin-bottom: 8px; display: block; }
        .feedback-box { background: #0b0e11; border: 1px solid #2d3238; padding: 15px; border-radius: 8px; font-size: 0.8rem; line-height: 1.5; min-height: 150px; font-family: 'Consolas', monospace; }
        .col-professor_test { background: rgba(64, 192, 87, 0.05); border: 1px solid rgba(64, 192, 87, 0.3); border-radius: 10px; }
        .col-professor_test .provider-label { color: #40c057 !important; }
    </style></head><body><div class="container-fluid">
        <h1 class="text-center mb-5">🚀 PyJudge Comparison Dashboard</h1>
        
        <div class="row"><div class="col-md-8 offset-md-2 chart-box">
            <h5 class="text-center mb-4">Μέσος Όρος Βαθμολογίας (AI vs Professor)</h5>
            <canvas id="gradeChart"></canvas>
        </div></div>

        <script>
            new Chart(document.getElementById('gradeChart'), {
                type: 'bar',
                data: {
                    labels: """ + str(chart_labels) + """,
                    datasets: [{
                        label: 'Μέσος Όρος (0-10)',
                        data: """ + str(chart_values) + """,
                        backgroundColor: ['#40c057', '#4dabf7', '#fab005', '#fa5252'],
                        borderRadius: 6
                    }]
                },
                options: { scales: { y: { beginAtZero: true, max: 10 } } }
            });
        </script>
    """

    body = ""
    for s_id, feedbacks in sorted(all_data.items()):
        body += f'<div class="student-card"><div class="student-title">👤 {s_id}</div><div class="row g-3">'
        col_size = 12 // len(sorted_providers) if len(sorted_providers) <= 4 else 3
        for p in sorted_providers:
            content = feedbacks.get(p, '<span style="color:#444">N/A</span>')
            is_prof = "col-professor_test" if p == "PROFESSOR_TEST" else ""
            body += f'<div class="col-md-{col_size} {is_prof}"><span class="provider-label">{p}</span><div class="feedback-box">{content}</div></div>'
        body += "</div></div>"

    with open("comparison_with_charts.html", "w", encoding="utf-8") as f:
        f.write(html_header + body + "</div></body></html>")
    
    print(f"\n✅ ΕΤΟΙΜΟ! Βρέθηκαν {len(all_data)} φοιτητές.")
    print("Άνοιξε το 'comparison_with_charts.html' για να δεις τα γραφήματα!")

if __name__ == "__main__":
    generate_visual_report()