import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import Register from './pages/Register';
import Login from './pages/Login';
import VLMRegister from './pages/VLMRegister';
import VLMLogin from './pages/VLMLogin';

/* Shield icon SVG */
const ShieldIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

export default function App() {
  return (
    <Router>
      <div className="app-container">
        {/* ─── Navigation ──────────────────────────────────── */}
        <nav className="nav">
          <NavLink to="/" className="nav-brand">
            <ShieldIcon />
            FaceAuth
          </NavLink>
          <div className="nav-links">
            <NavLink
              to="/register"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              Register
            </NavLink>
            <NavLink
              to="/login"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              Login
            </NavLink>
            <span className="nav-divider">|</span>
            <NavLink
              to="/vlm-register"
              className={({ isActive }) => `nav-link vlm-nav-link ${isActive ? 'active' : ''}`}
            >
              🧠 VLM Register
            </NavLink>
            <NavLink
              to="/vlm-login"
              className={({ isActive }) => `nav-link vlm-nav-link ${isActive ? 'active' : ''}`}
            >
              🧠 VLM Login
            </NavLink>
          </div>
        </nav>

        {/* ─── Routes ──────────────────────────────────────── */}
        <Routes>
          <Route path="/" element={<Register />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/vlm-register" element={<VLMRegister />} />
          <Route path="/vlm-login" element={<VLMLogin />} />
        </Routes>
      </div>
    </Router>
  );
}

