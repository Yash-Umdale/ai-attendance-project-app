/**
 * VeriAttend — Student Dashboard
 *
 * Full student portal with:
 * - Login
 * - Attendance overview (overall percentage, present/absent counts)
 * - Subject-wise attendance breakdown with progress bars
 * - Attendance history table
 * - Account management (deregister)
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentsAPI } from '../api/client';

const TOKEN_KEY = 'veriattend_student_token';

export default function StudentAccount() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [login, setLogin] = useState({ student_code: '', password: '' });
  const [confirm, setConfirm] = useState({ password: '', confirmation: '' });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [showDeregister, setShowDeregister] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) loadProfile();
  }, []);

  const studentConfig = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` } });

  const loadProfile = async () => {
    try {
      const [profileRes, summaryRes] = await Promise.all([
        studentsAPI.me(studentConfig()),
        studentsAPI.attendanceSummary(studentConfig()),
      ]);
      setProfile(profileRes.data);
      setSummary(summaryRes.data);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setProfile(null);
      setSummary(null);
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await studentsAPI.login(login);
      localStorage.setItem(TOKEN_KEY, res.data.access_token);
      await loadProfile();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not sign in.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setProfile(null);
    setSummary(null);
  };

  const handleDeregister = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await studentsAPI.deregister(confirm, studentConfig());
      localStorage.removeItem(TOKEN_KEY);
      setProfile(null);
      setSummary(null);
      setMessage(res.data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Deregistration failed.');
    } finally {
      setLoading(false);
    }
  };

  const getPercentageColor = (pct) => {
    if (pct >= 75) return 'var(--success-500)';
    if (pct >= 50) return 'var(--warning-500)';
    return 'var(--error-500)';
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <a href="/" className="app-header__brand">
          <img src="https://i.ibb.co/YTYGn5qV/logo.png" alt="" className="app-header__logo" />
          <span className="app-header__title">VeriAttend</span>
        </a>
        <nav className="app-header__nav">
          <a href="/attendance" className="btn btn--ghost btn--sm">Attendance</a>
          <a href="/register" className="btn btn--ghost btn--sm">Register</a>
          {profile && (
            <button className="btn btn--ghost btn--sm" onClick={handleLogout}>Logout</button>
          )}
        </nav>
      </header>

      <main className="app-main" style={{ maxWidth: 900, margin: '0 auto' }}>
        <div className="animate-in">
          {error && <div className="alert alert--error mb-2">⚠️ {error}</div>}
          {message && <div className="alert alert--success mb-2">✅ {message}</div>}

          {/* ── Login Form ── */}
          {!profile && (
            <div style={{ maxWidth: 440, margin: '2rem auto' }}>
              <div className="card" style={{ padding: '2.5rem' }}>
                <div className="text-center mb-3">
                  <h1 style={{ fontSize: '1.75rem' }}>
                    <span style={{ background: 'linear-gradient(135deg, var(--primary-400), var(--accent-400))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      Student Portal
                    </span>
                  </h1>
                  <p className="text-muted text-sm mt-1">Sign in to view your attendance</p>
                </div>
                <form onSubmit={handleLogin}>
                  <div className="input-group mb-2">
                    <label className="input-group__label">Roll Number / Student ID</label>
                    <input className="input" required placeholder="e.g. CS2024001"
                      value={login.student_code} onChange={e => setLogin({ ...login, student_code: e.target.value })} />
                  </div>
                  <div className="input-group mb-3">
                    <label className="input-group__label">Password</label>
                    <input className="input" type="password" required
                      value={login.password} onChange={e => setLogin({ ...login, password: e.target.value })} />
                  </div>
                  <button className="btn btn--primary btn--full btn--lg" disabled={loading}>
                    {loading ? 'Signing in...' : 'Sign In'}
                  </button>
                </form>
                <div className="text-center mt-2">
                  <a href="/register" className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    New student? Register here →
                  </a>
                  <p className="text-sm text-muted mt-1">Forgot your password? Ask an administrator to reset it.</p>
                </div>
              </div>
            </div>
          )}

          {/* ── Dashboard ── */}
          {profile && summary && (
            <>
              {/* Welcome Header */}
              <div className="card mb-3" style={{ padding: '1.5rem 2rem' }}>
                <div className="flex gap-2" style={{ alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                  <div>
                    <h2 style={{ margin: 0 }}>👋 Welcome, {profile.name}</h2>
                    <p className="text-muted text-sm mt-1">
                      {profile.student_code} · {profile.department || 'N/A'} · {profile.year || 'N/A'}
                    </p>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{
                      fontSize: '2.5rem', fontWeight: 800, lineHeight: 1,
                      color: getPercentageColor(summary.overall_percentage),
                    }}>
                      {summary.overall_percentage}%
                    </div>
                    <div className="text-sm text-muted">Overall Attendance</div>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="tabs" style={{ maxWidth: 500 }}>
                {['overview', 'subjects', 'history', 'account'].map((tab) => (
                  <button key={tab} className={`tab ${activeTab === tab ? 'tab--active' : ''}`}
                    onClick={() => setActiveTab(tab)}>
                    {tab === 'overview' ? '📊 Overview' : tab === 'subjects' ? '📚 Subjects' :
                      tab === 'history' ? '📋 History' : '⚙️ Account'}
                  </button>
                ))}
              </div>

              {/* ── Overview Tab ── */}
              {activeTab === 'overview' && (
                <div className="animate-in">
                  <div className="grid-4 mb-3">
                    <div className="stat-card">
                      <div className="stat-card__icon stat-card__icon--primary">📊</div>
                      <div><div className="stat-card__value">{summary.overall_percentage}%</div><div className="stat-card__label">Attendance</div></div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-card__icon stat-card__icon--success">✅</div>
                      <div><div className="stat-card__value">{summary.total_present}</div><div className="stat-card__label">Present</div></div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-card__icon stat-card__icon--error">❌</div>
                      <div><div className="stat-card__value">{summary.total_absent}</div><div className="stat-card__label">Absent</div></div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-card__icon stat-card__icon--warning">📅</div>
                      <div><div className="stat-card__value">{summary.total_sessions}</div><div className="stat-card__label">Sessions</div></div>
                    </div>
                  </div>

                  {/* Quick subject bars */}
                  {summary.subjects.length > 0 && (
                    <div className="card">
                      <h3 className="mb-2">Subject-wise Attendance</h3>
                      {summary.subjects.map((s) => (
                        <div key={s.subject_id} className="mb-2">
                          <div className="flex gap-1" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                            <span className="text-sm"><strong>{s.subject_name}</strong> ({s.subject_code})</span>
                            <span className="text-sm" style={{ color: getPercentageColor(s.percentage), fontWeight: 700 }}>
                              {s.percentage}%
                            </span>
                          </div>
                          <div style={{
                            width: '100%', height: 8, borderRadius: 4,
                            background: 'var(--bg-elevated)', marginTop: 4,
                            overflow: 'hidden',
                          }}>
                            <div style={{
                              width: `${s.percentage}%`, height: '100%', borderRadius: 4,
                              background: getPercentageColor(s.percentage),
                              transition: 'width 0.6s ease',
                            }} />
                          </div>
                          <p className="text-sm text-muted" style={{ marginTop: 2 }}>
                            {s.present_count} / {s.total_sessions} sessions · Section {s.section}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                  {summary.subjects.length === 0 && (
                    <div className="empty-state">
                      <div className="empty-state__icon">📚</div>
                      <div className="empty-state__title">Not enrolled in any subjects yet</div>
                      <div className="empty-state__text">Ask your teacher to enroll you in a subject.</div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Subjects Tab ── */}
              {activeTab === 'subjects' && (
                <div className="animate-in">
                  {summary.subjects.length > 0 ? (
                    <div className="grid-2">
                      {summary.subjects.map((s) => (
                        <div className="card" key={s.subject_id}>
                          <h4>{s.subject_name}</h4>
                          <p className="text-sm text-muted mt-1">
                            Code: <span className="badge badge--primary">{s.subject_code}</span> · Section {s.section}
                          </p>
                          <div className="flex gap-2 mt-2" style={{ alignItems: 'center' }}>
                            <div style={{
                              fontSize: '2rem', fontWeight: 800,
                              color: getPercentageColor(s.percentage),
                            }}>
                              {s.percentage}%
                            </div>
                            <div className="text-sm text-muted">
                              <div>✅ Present: {s.present_count}</div>
                              <div>❌ Absent: {s.absent_count}</div>
                              <div>📅 Total: {s.total_sessions}</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <div className="empty-state__icon">📚</div>
                      <div className="empty-state__title">No subjects</div>
                    </div>
                  )}
                </div>
              )}

              {/* ── History Tab ── */}
              {activeTab === 'history' && (
                <div className="animate-in">
                  <h3 className="mb-2">Attendance History</h3>
                  {summary.history.length > 0 ? (
                    <div className="table-container">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Date</th><th>Subject</th><th>Status</th><th>Confidence</th><th>Time</th>
                          </tr>
                        </thead>
                        <tbody>
                          {summary.history.map((h, i) => (
                            <tr key={i}>
                              <td>{h.date}</td>
                              <td>{h.subject_name}</td>
                              <td>
                                <span className={`badge ${h.status === 'PRESENT' ? 'badge--success' : h.status === 'ABSENT' ? 'badge--error' : 'badge--warning'}`}>
                                  {h.status}
                                </span>
                              </td>
                              <td>{h.confidence ? `${(h.confidence * 100).toFixed(0)}%` : '—'}</td>
                              <td>{h.timestamp ? new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <div className="empty-state__icon">📋</div>
                      <div className="empty-state__title">No attendance records yet</div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Account Tab ── */}
              {activeTab === 'account' && (
                <div className="animate-in">
                  <div className="card mb-3">
                    <h3>Profile Information</h3>
                    <div className="grid-2 mt-2">
                      <div><span className="text-sm text-muted">Name</span><p><strong>{profile.name}</strong></p></div>
                      <div><span className="text-sm text-muted">Roll Number</span><p><strong>{profile.student_code}</strong></p></div>
                      <div><span className="text-sm text-muted">Email</span><p>{profile.email || '—'}</p></div>
                      <div><span className="text-sm text-muted">Mobile</span><p>{profile.mobile_number || '—'}</p></div>
                      <div><span className="text-sm text-muted">Department</span><p>{profile.department || '—'}</p></div>
                      <div><span className="text-sm text-muted">Year</span><p>{profile.year || '—'}</p></div>
                      <div><span className="text-sm text-muted">Face Enrolled</span><p>{profile.has_face_embedding ? '✅ Yes' : '❌ No'}</p></div>
                      <div><span className="text-sm text-muted">Account Status</span><p><span className={`badge ${profile.is_active ? 'badge--success' : 'badge--error'}`}>{profile.account_status}</span></p></div>
                    </div>
                  </div>

                  {!showDeregister ? (
                    <button className="btn btn--danger btn--sm" onClick={() => setShowDeregister(true)}>
                      ⚠️ Deregister Account
                    </button>
                  ) : (
                    <form className="card" onSubmit={handleDeregister}>
                      <h3>⚠️ Deregister / Delete Account</h3>
                      <p className="text-muted text-sm mt-1">
                        This permanently deactivates your account, removes face biometric data, and removes active subject enrollments.
                        Historical attendance is retained for institutional reports.
                      </p>
                      <div className="input-group mt-2">
                        <label className="input-group__label">Current password</label>
                        <input className="input" type="password" required value={confirm.password}
                          onChange={e => setConfirm({ ...confirm, password: e.target.value })} />
                      </div>
                      <div className="input-group mt-2">
                        <label className="input-group__label">Type DEREGISTER to confirm</label>
                        <input className="input" required value={confirm.confirmation}
                          onChange={e => setConfirm({ ...confirm, confirmation: e.target.value })} />
                      </div>
                      <div className="flex gap-2 mt-2">
                        <button className="btn btn--danger" disabled={loading}>
                          {loading ? 'Deregistering...' : 'Deregister Account'}
                        </button>
                        <button type="button" className="btn btn--secondary" onClick={() => setShowDeregister(false)}>
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
