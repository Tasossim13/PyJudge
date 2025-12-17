import { useState } from 'react'
import './App.css'
import Button from './components/button';
import TextBox from './components/textBox';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';


function App() {
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
      <TextBox/>
      <Button/>

      <h1>Step 2</h1>
      <h2>Upload Exercises And Solutions</h2>

      <h1>Step 3</h1>
      <h2>Upload Students Exercise </h2>
    </div>
  )
}

export default App
