import { useState } from 'react'
import Button from './components/button';
import TextBox from './components/textBox';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import './App.css'
import InputFIles from './components/InputFiles';


function App() {
  const [prompt, setPrompt] = useState("")
  const [answer, setAnswer] = useState("")
  const sendPrompt = async () => {
    const res = await fetch("http://127.0.0.1:5000/test_chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    })

    const data = await res.json()
    setAnswer(data.answer)
  }
  return (
    <div className="header">
      <nav className="navbar fixed-top bg-body-tertiary">
        <div className="container-fluid">
          <a className="navbar-brand" href="#">
            <img
              src="/favicon.ico"
              alt="Logo"
              width="30"
              height="24"
              className="d-inline-block align-text-top"
            />
            PyJudge
          </a>
        </div>
      </nav>

      <h1>Step 1</h1>
      <h2>Provide a Prompt:</h2>
      <TextBox value={prompt} onchange={setPrompt}/>
      {answer && (
        <div className="alert alert-secondary mt-3">
          {answer}
        </div>
      )}
      <Button/>
    <div className='sectionTwo'>
      <h1>Step 2</h1>
      <h2>Upload Your Exercises And Solutions</h2>
      <InputFIles/><InputFIles/>
    </div>
    <div className='sectionThree'>
      <h1>Step 3</h1>
      <h2>Upload Students Exercise </h2>
      <InputFIles/>
    </div>
    <div>
      
    </div>
    </div>
  )
}

export default App
