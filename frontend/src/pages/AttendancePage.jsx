/**
 * VeriAttend — Attendance Page
 *
 * Student-facing attendance interface.
 * Selects an active session and runs the full attendance workflow.
 */

import { useState, useEffect } from 'react';
import AttendanceFlow from '../components/AttendanceFlow';
import { sessionsAPI } from '../api/client';

export default function AttendancePage() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await sessionsAPI.listActive();
      setSessions(res.data);
      if (res.data.length === 1) {
        setSelectedSession(res.data[0].session_id);
      }
    } catch (err) {
      // Sessions endpoint may require auth — for student flow, show all active
      setError('Could not load sessions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <a href="/" className="app-header__brand">
          <img src="https://i.ibb.co/YTYGn5qV/logo.png" alt="" className="app-header__logo" />
          <span className="app-header__title">VeriAttend</span>
        </a>
        <nav className="app-header__nav">
          <a href="/register" className="btn btn--ghost btn--sm">Register</a>
          <a href="/student/account" className="btn btn--ghost btn--sm">My Account</a>
          <a href="/login" className="btn btn--ghost btn--sm">Admin Login</a>
        </nav>
      </header>

      <main className="app-main" style={{ maxWidth: 700, margin: '0 auto' }}>
        <div className="text-center mb-3 animate-in">
          <h1>
            <span style={{ background: 'linear-gradient(135deg, var(--primary-400), var(--accent-400))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AI Attendance
            </span>
          </h1>
          <p className="text-muted mt-1">Fit all students in the camera and follow the live check to mark attendance</p>
        </div>

        {/* Session Selector */}
        {sessions.length > 0 && (
          <div className="input-group mb-3 animate-in" style={{ maxWidth: 400, margin: '0 auto' }}>
            <label className="input-group__label">Select Session</label>
            <select
              className="input"
              value={selectedSession || ''}
              onChange={(e) => setSelectedSession(Number(e.target.value))}
              id="select-session"
            >
              <option value="">Choose a session...</option>
              {sessions.map((s) => (
                <option key={s.session_id} value={s.session_id}>
                  {s.name} — {s.subject_name || ''} ({s.date})
                </option>
              ))}
            </select>
          </div>
        )}

        {loading && (
          <div className="spinner-container">
            <div className="spinner" />
            <span>Loading sessions...</span>
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="card text-center" style={{ padding: '3rem' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📅</div>
            <h3>No Active Sessions</h3>
            <p className="text-muted mt-1">
              There are no active attendance sessions right now.<br />
              Please ask your teacher to start a session.
            </p>
          </div>
        )}

        {error && <div className="alert alert--error mb-2">{error}</div>}

        {selectedSession && (
          <div className="animate-in">
            <AttendanceFlow
              sessionId={selectedSession}
              onComplete={(decision) => {
                console.log('Attendance decision:', decision);
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}
