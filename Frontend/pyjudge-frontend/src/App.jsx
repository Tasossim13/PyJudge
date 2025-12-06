import { useState } from 'react'
import './App.css'
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

      <h1>Hello from React</h1>
    </div>
  )
}

export default App
