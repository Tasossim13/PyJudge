import { useState } from 'react'
import Button from './components/Βutton';
import 'bootstrap/dist/css/bootstrap.min.css';
import Swal from 'sweetalert2'
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import './App.css'

function App() {
  const [apiKey, setApiKey] = useState("");
  const [answer, setAnswer] = useState("");
  const [prompt, setPrompt] = useState("");
  const [studentFile, setStudentFile] = useState(null);
  const [solutionFile, setSolutionFile] = useState(null);
  const [exerciseFile, setExerciseFile] = useState(null);
  const [zipFile, setZipFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState("single");
  const [provider, setProvider] = useState("groq");
  const providerDetails = {
  groq: { label: "Groq API Key", placeholder: "gsk_...", color: "danger" },
  openai: { label: "ChatGpt API Key", placeholder: "sk-...", color: "dark" },
  gemini: { label: "Gemini API Key", placeholder: "AIza...", color: "primary" }
};

const sendToBackend = async () => {
  setAnswer("");
  
  // 1. Βασικός έλεγχος για API Key
  if (!apiKey) {
    Swal.fire({ title: 'Missing API Key', text: 'Please enter your API key first.', icon: 'warning' });
    return;
  }

  // 2. Έλεγχος αρχείων ανάλογα με το mode
  if (mode === "single") {
    if (!studentFile || !exerciseFile || !solutionFile) {
      Swal.fire({ title: 'Files Missing!', text: 'Please Upload All 3 Files (Python, HTML, TXT).', icon: 'error' });
      return;
    }
  } else {
    if (!zipFile || !solutionFile) {
      Swal.fire({ title: 'Files Missing!', text: 'Please Upload ZIP and Doc Tests.', icon: 'error' });
      return;
    }
  }

  setIsLoading(true);
  const formData = new FormData();
  
  // Κοινά δεδομένα για όλα τα modes
  formData.append("api_key", apiKey);
  formData.append("provider", provider);
  formData.append("solution", solutionFile);

  try {
    if (mode === "single") {
      formData.append("exercise", exerciseFile);
      formData.append("student", studentFile);

      const res = await fetch("http://127.0.0.1:5000/evaluate", { method: "POST", body: formData });
      const data = await res.json();
      
      if (data.error) throw new Error(data.error);
      setAnswer(data.answer);
    } 
    else {
      formData.append("students_zip", zipFile);
      
      const res = await fetch("http://127.0.0.1:5000/evaluate_bulk", { method: "POST", body: formData });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Bulk grading failed");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "grading_results.zip";
      a.click();
      setAnswer("Bulk grading finished! Your ZIP has been downloaded.");
    }
  } catch (err) {
    Swal.fire('Error', err.message || 'Server connection failed', 'error');
  } finally {
    setIsLoading(false);
  }
};

  const downloadTxt = () => { //for single grade only
    const blob = new Blob([answer], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "grading_result.txt"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="header">
      <nav className="navbar fixed-top bg-body-tertiary shadow-sm">
        <div className="container-fluid">
          <div className="d-flex align-items-center">
            <img src="/logo.svg" alt="Logo" width="50" height="30" className="d-inline-block align-text-top" />
            <span className="navbar-brand">PyJudge</span>
          </div>
          
          <div className="btn-group">
            <button 
              className={`btn ${mode === 'single' ? 'btn-primary' : 'btn-outline-success'}`} 
              onClick={() => { setMode("single"); setAnswer(""); }}
            >
              Single
            </button>
            <button 
              className={`btn ${mode === 'bulk' ? 'btn-primary' : 'btn-outline-success'}`} 
              onClick={() => { setMode("bulk"); setAnswer(""); }}
            >
              Bulk
            </button>
          </div>
        </div>
      </nav>

      <h1 style={{ minHeight: "40px" }}>
    {mode === "single" ? "Single Grade" : "Bulk Grade"}
    </h1>
      <hr />
      <div className="mb-3 d-flex justify-content-center gap-2">
        <button 
          className={`btn ${provider === 'openai' ? 'btn-success' : 'btn-outline-success'}`}
          onClick={() => setProvider("openai")}
        >
        ChatGPT
        </button>
        <button 
          className={`btn ${provider === 'gemini' ? 'btn-primary' : 'btn-outline-success'}`}
          onClick={() => setProvider("gemini")}
        >
        Gemini
        </button>
        <button 
          className={`btn ${provider === 'groq' ? 'btn-success' : 'btn-outline-success'}`}
          onClick={() => setProvider("groq")}
        >     
        Groq
        </button>
        </div>
        <div className="mb-3 card p-3 shadow-sm ">
            <label className="form-label font-weight-bold">Enter Your {providerDetails[provider].label}:</label>
            <input 
              type="text" 
              className="form-control border-primary" 
              placeholder={providerDetails[provider].placeholder}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <small className="text-muted">Your API key will be deleted shortly for safety reasons.</small>
          </div>
      {mode === "single" ? (
        <>
          
        <div className='sectionTwo'>
          <h2>Upload Doc Tests(.txt)</h2>
        <input type="file" accept=".txt" onChange={e => setSolutionFile(e.target.files[0])} />
        </div>
          <div className='sectionTwo'>
            <h2>Upload Exercises(.html)</h2>
            <input type="file" accept=".html" onChange={e => setExerciseFile(e.target.files[0])} />
          </div>
          <div className='sectionThree'>
            <h2>Upload Student File(.py)</h2>
            <input type="file" accept=".py" onChange={e => setStudentFile(e.target.files[0])} />
          </div>
        </>
      ) : (
        <div>
        <div className='sectionTwo'>
          <h2>Upload Doc Tests(.txt)</h2>
          <input type="file" accept=".txt" onChange={e => setSolutionFile(e.target.files[0])} />
        </div>
        <div className='sectionTwo'>
          <h2>Upload Exercises(.html)</h2>
          <input type="file" accept=".html" onChange={e => setExerciseFile(e.target.files[0])} />
        </div>
        <div className='sectionThree'>
          <h2>Upload Students Filder(.zip)</h2>
          <input type="file" accept=".zip" onChange={e => setZipFile(e.target.files[0])} />
        </div></div>
      )}

      <Button onClick={sendToBackend} disabled={isLoading}/>

      {isLoading && (
        <div className="text-center mt-3">
          <div className="spinner-border text-success" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          
        </div>
      )}

      {answer && (
        <div>
          {mode === "single" && (
            <div className='downloadButton mt-2'>
              <button onClick={downloadTxt}>Download Txt</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App;