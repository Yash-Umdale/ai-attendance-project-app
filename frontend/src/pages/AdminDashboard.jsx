/**
 * VeriAttend — Admin Dashboard
 *
 * Dashboard with:
 * - Stats cards (total students, present today, absent, pending reviews)
 * - Attendance table with search/filter + manual edit
 * - Session management with Start Attendance webcam
 * - Subject management
 * - Student information
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminAPI, enrollmentAPI, sessionsAPI, studentsAPI, attendanceAPI } from '../api/client';
import Camera from '../components/Camera';
import StatusDisplay from '../components/StatusDisplay';
import { runLivenessChallenge } from '../utils/runLivenessChallenge';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [teacher, setTeacher] = useState(null);
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [students, setStudents] = useState([]);
  const [subjectRosters, setSubjectRosters] = useState({});
  const [studentToEnroll, setStudentToEnroll] = useState({});
  const [studentPasswordReset, setStudentPasswordReset] = useState({ studentId: null, password: '', confirmation: '' });
  const [clearDataOpen, setClearDataOpen] = useState(false);
  const [clearDataForm, setClearDataForm] = useState({ password: '', confirmation: '' });
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);

  // Filters
  const [filters, setFilters] = useState({ subject_id: '', date: '', student_name: '', status_filter: '' });

  // Create session form
  const [sessionForm, setSessionForm] = useState({ name: '', subject_id: '', date: '', start_time: '', end_time: '' });

  // Create subject form
  const [subjectForm, setSubjectForm] = useState({ subject_code: '', name: '', section: '' });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  // Attendance webcam state
  const [attendanceSessionId, setAttendanceSessionId] = useState(null);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [attendanceResult, setAttendanceResult] = useState(null);
  const [attendanceStatus, setAttendanceStatus] = useState('');
  const [recognizedList, setRecognizedList] = useState([]);
  const cameraRef = useRef(null);

  useEffect(() => {
    const stored = localStorage.getItem('veriattend_teacher');
    if (!stored) { navigate('/login'); return; }
    setTeacher(JSON.parse(stored));
    loadData();
  }, [navigate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, recordsRes, subjectsRes, sessionsRes, studentsRes] = await Promise.all([
        adminAPI.dashboard(),
        adminAPI.getAttendance({ limit: 50 }),
        adminAPI.listSubjects(),
        sessionsAPI.list(),
        adminAPI.listStudents(),
      ]);
      setStats(statsRes.data);
      setRecords(recordsRes.data);
      setSubjects(subjectsRes.data);
      setSessions(sessionsRes.data);
      setStudents(studentsRes.data);
      const rosterResponses = await Promise.all(
        subjectsRes.data.map(async (subject) => [subject.subject_id, (await enrollmentAPI.getStudents(subject.subject_id)).data])
      );
      setSubjectRosters(Object.fromEntries(rosterResponses));
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = async () => {
    try {
      const params = {};
      if (filters.subject_id) params.subject_id = filters.subject_id;
      if (filters.date) params.date = filters.date;
      if (filters.student_name) params.student_name = filters.student_name;
      if (filters.status_filter) params.status_filter = filters.status_filter;
      const res = await adminAPI.getAttendance(params);
      setRecords(res.data);
    } catch (err) {
      console.error('Filter error:', err);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    setFormError(''); setFormSuccess('');
    try {
      const payload = {
        ...sessionForm,
        subject_id: Number(sessionForm.subject_id),
        // Keep local wall-clock times. The backend stores session windows as local
        // values so the teacher sees the same time they selected in the dashboard.
        start_time: `${sessionForm.date}T${sessionForm.start_time}`,
        end_time: `${sessionForm.date}T${sessionForm.end_time}`,
      };
      await sessionsAPI.create(payload);
      setFormSuccess('Session created!');
      setSessionForm({ name: '', subject_id: '', date: '', start_time: '', end_time: '' });
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to create session.');
    }
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    setFormError(''); setFormSuccess('');
    try {
      await adminAPI.createSubject(subjectForm);
      setFormSuccess('Subject created!');
      setSubjectForm({ subject_code: '', name: '', section: '' });
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to create subject.');
    }
  };

  const handleToggleSession = async (sessionId, isActive) => {
    try {
      await sessionsAPI.toggle(sessionId, !isActive);
      loadData();
    } catch (err) {
      console.error('Toggle error:', err);
    }
  };

  const handleDeleteSession = async (sessionId, name) => {
    if (!window.confirm(`Delete "${name}" from the sessions list? Attendance records will be retained.`)) return;
    try {
      await sessionsAPI.remove(sessionId);
      setFormSuccess('Session removed. Existing attendance records were kept.');
      loadData();
    } catch (err) { setFormError(err.response?.data?.detail || 'Could not delete session.'); }
  };

  const handleEnrollStudent = async (subject) => {
    const studentId = Number(studentToEnroll[subject.subject_id]);
    if (!studentId) return;
    setFormError(''); setFormSuccess('');
    try {
      await enrollmentAPI.enroll({ student_id: studentId, subject_code: subject.subject_code });
      setStudentToEnroll((current) => ({ ...current, [subject.subject_id]: '' }));
      setFormSuccess('Student enrolled successfully.');
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not enroll student.');
    }
  };

  const handleRemoveFromClass = async (subject, student) => {
    if (!window.confirm(`Remove ${student.name} from ${subject.name}? They will no longer be able to mark attendance for this subject.`)) return;
    setFormError(''); setFormSuccess('');
    try {
      await enrollmentAPI.unenroll(student.student_id, subject.subject_id);
      setFormSuccess(`${student.name} was removed from ${subject.name}.`);
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not remove the student from this subject.');
    }
  };

  const handleEraseFace = async (subject, student) => {
    const confirmed = window.confirm(
      `Permanently erase ${student.name}'s enrolled face data and remove them from ${subject.name}? This cannot be undone; they must register their face again to use attendance.`
    );
    if (!confirmed) return;
    setFormError(''); setFormSuccess('');
    try {
      await studentsAPI.removeFace(student.student_id, subject.subject_id);
      setFormSuccess(`Face data erased and ${student.name} removed from ${subject.name}.`);
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not erase the face data.');
    }
  };

  const handleResetStudentPassword = async (event, student) => {
    event.preventDefault();
    setFormError(''); setFormSuccess('');
    if (studentPasswordReset.password !== studentPasswordReset.confirmation) {
      setFormError('The new password and confirmation do not match.');
      return;
    }
    try {
      await adminAPI.resetStudentPassword(student.student_id, studentPasswordReset.password);
      setStudentPasswordReset({ studentId: null, password: '', confirmation: '' });
      setFormSuccess(`Password updated for ${student.student_code}. Share it with the student securely.`);
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not update the student password.');
    }
  };

  const handleClearAllData = async (event) => {
    event.preventDefault();
    setFormError(''); setFormSuccess('');
    try {
      const response = await adminAPI.clearData(clearDataForm);
      setClearDataOpen(false);
      setClearDataForm({ password: '', confirmation: '' });
      setStudentPasswordReset({ studentId: null, password: '', confirmation: '' });
      setFormSuccess(response.data.message);
      await loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not clear application data.');
    }
  };

  // ── Manual attendance status edit ──
  const handleStatusChange = async (attendanceId, newStatus) => {
    setFormError(''); setFormSuccess('');
    try {
      await adminAPI.updateAttendanceStatus(attendanceId, newStatus);
      setFormSuccess(`Attendance updated to ${newStatus}.`);
      // Refresh records
      handleFilter();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Could not update status.');
    }
  };

  // ── Start Attendance (webcam) ──
  const startAttendanceCamera = (sessionId) => {
    setAttendanceSessionId(sessionId);
    setAttendanceResult(null);
    setAttendanceStatus('');
    setRecognizedList([]);
    setCameraEnabled(true);
  };

  const stopAttendanceCamera = () => {
    cameraRef.current?.stopCamera();
    setCameraEnabled(false);
    setAttendanceSessionId(null);
    setAttendanceResult(null);
    setAttendanceStatus('');
  };

  const captureAndVerify = async () => {
    if (isProcessing || !cameraRef.current || !attendanceSessionId) return;
    if (!cameraRef.current.captureFrame()) return;
    setIsProcessing(true);
    setAttendanceStatus('✨ Preparing a random liveness check...');
    try {
      const { challengeId, frameData } = await runLivenessChallenge(
        cameraRef,
        (instruction) => setAttendanceStatus(`✨ ${instruction}`),
        true,
      );
      setAttendanceStatus('🔍 Liveness verified. Recognizing face...');
      const response = await attendanceAPI.markGroup({
        session_id: attendanceSessionId,
        frame_data: frameData,
        liveness_challenge_id: challengeId,
      });
      const decision = response.data;
      setAttendanceResult(decision);
      if (decision.decision === 'GROUP_PROCESSED') {
        const approved = decision.students.filter((student) => student.decision === 'APPROVED');
        const duplicates = decision.students.filter((student) => student.decision === 'DUPLICATE');
        setAttendanceStatus(`✅ Processed ${decision.face_count} face(s): ${approved.length} marked present, ${duplicates.length} already present.`);
        setRecognizedList((prev) => {
          const added = approved
            .filter((student) => !prev.some((row) => row.student_id === student.student_id))
            .map((student) => ({
              student_id: student.student_id,
              student_name: student.student_name,
              student_code: student.student_code,
              confidence: student.recognition_confidence,
            }));
          return [...prev, ...added];
        });
      } else {
        setAttendanceStatus(`❌ ${decision.reason || 'Group attendance rejected.'}`);
      }
    } catch (err) {
      setAttendanceStatus(err.isLivenessFailure
        ? '❌ Attendance rejected (Image Detected) — Liveness unverified'
        : `⚠️ ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('veriattend_token');
    localStorage.removeItem('veriattend_teacher');
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="app-layout">
        <div className="spinner-container" style={{ minHeight: '100vh' }}>
          <div className="spinner" />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <a href="/dashboard" className="app-header__brand">
          <img src="https://i.ibb.co/YTYGn5qV/logo.png" alt="" className="app-header__logo" />
          <span className="app-header__title">VeriAttend</span>
        </a>
        <nav className="app-header__nav">
          <span className="text-sm text-muted">👋 {teacher?.name}</span>
          <button className="btn btn--ghost btn--sm" onClick={handleLogout}>Logout</button>
        </nav>
      </header>

      <main className="app-main">
        {/* Tabs */}
        <div className="tabs" style={{ maxWidth: 600 }}>
          {['overview', 'attendance', 'sessions', 'subjects', 'students'].map((tab) => (
            <button key={tab} className={`tab ${activeTab === tab ? 'tab--active' : ''}`}
              onClick={() => setActiveTab(tab)}>
              {tab === 'overview' ? '📊 Overview' : tab === 'attendance' ? '📋 Attendance' :
                tab === 'sessions' ? '📅 Sessions' : tab === 'subjects' ? '📚 Subjects' : '👥 Students'}
            </button>
          ))}
        </div>

        {formError && <div className="alert alert--error mb-2">⚠️ {formError}</div>}
        {formSuccess && <div className="alert alert--success mb-2">✅ {formSuccess}</div>}

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="animate-in">
            <div className="grid-4 mb-3">
              <div className="stat-card">
                <div className="stat-card__icon stat-card__icon--primary">👥</div>
                <div><div className="stat-card__value">{stats.total_students}</div><div className="stat-card__label">Total Students</div></div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon stat-card__icon--success">✅</div>
                <div><div className="stat-card__value">{stats.present_today}</div><div className="stat-card__label">Present Today</div></div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon stat-card__icon--error">❌</div>
                <div><div className="stat-card__value">{stats.absent_today}</div><div className="stat-card__label">Absent Today</div></div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon stat-card__icon--warning">📋</div>
                <div><div className="stat-card__value">{stats.pending_reviews}</div><div className="stat-card__label">Pending Reviews</div></div>
              </div>
            </div>

            {/* Recent Attendance */}
            <h3 className="mb-2">Recent Attendance</h3>
            {records.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead><tr>
                    <th>Student</th><th>Subject</th><th>Date</th><th>Time</th>
                    <th>Confidence</th><th>Liveness</th><th>Status</th>
                  </tr></thead>
                  <tbody>
                    {records.slice(0, 10).map((r) => (
                      <tr key={r.attendance_id}>
                        <td><strong>{r.student_name}</strong><br /><span className="text-sm text-muted">{r.student_code}</span></td>
                        <td>{r.subject_name}</td>
                        <td>{r.date}</td>
                        <td>{new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                        <td>
                          <span style={{ fontWeight: 600 }}>{r.recognition_confidence ? `${(r.recognition_confidence * 100).toFixed(0)}%` : '—'}</span>
                        </td>
                        <td><span className={`badge ${r.liveness_status === 'PASS' ? 'badge--success' : 'badge--neutral'}`}>{r.liveness_status}</span></td>
                        <td><span className={`badge ${r.status === 'PRESENT' ? 'badge--success' : r.status === 'MANUAL_REVIEW' ? 'badge--warning' : 'badge--error'}`}>{r.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state"><div className="empty-state__icon">📊</div><div className="empty-state__title">No attendance records yet</div></div>
            )}
          </div>
        )}

        {/* Attendance Tab — with manual edit */}
        {activeTab === 'attendance' && (
          <div className="animate-in">
            <h3 className="mb-2">Attendance Records</h3>
            <div className="filter-bar">
              <div className="input-group">
                <label className="input-group__label">Subject</label>
                <select className="input" value={filters.subject_id} onChange={(e) => setFilters({ ...filters, subject_id: e.target.value })}>
                  <option value="">All Subjects</option>
                  {subjects.map((s) => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
                </select>
              </div>
              <div className="input-group">
                <label className="input-group__label">Date</label>
                <input className="input" type="date" value={filters.date} onChange={(e) => setFilters({ ...filters, date: e.target.value })} />
              </div>
              <div className="input-group">
                <label className="input-group__label">Student</label>
                <input className="input" placeholder="Search name..." value={filters.student_name} onChange={(e) => setFilters({ ...filters, student_name: e.target.value })} />
              </div>
              <div className="input-group">
                <label className="input-group__label">Status</label>
                <select className="input" value={filters.status_filter} onChange={(e) => setFilters({ ...filters, status_filter: e.target.value })}>
                  <option value="">All</option>
                  <option value="PRESENT">Present</option>
                  <option value="ABSENT">Absent</option>
                  <option value="MANUAL_REVIEW">Manual Review</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>
              <button className="btn btn--primary btn--sm" onClick={handleFilter}>🔍 Filter</button>
            </div>

            {records.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead><tr>
                    <th>Student</th><th>Subject</th><th>Date</th><th>Time</th>
                    <th>Confidence</th><th>Liveness</th><th>Status</th><th>Action</th>
                  </tr></thead>
                  <tbody>
                    {records.map((r) => (
                      <tr key={r.attendance_id ?? `absent-${r.session_id}-${r.student_id}`}>
                        <td><strong>{r.student_name}</strong><br /><span className="text-sm text-muted">{r.student_code}</span></td>
                        <td>{r.subject_name}</td>
                        <td>{r.date}</td>
                        <td>{new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                        <td>{r.recognition_confidence ? `${(r.recognition_confidence * 100).toFixed(0)}%` : '—'}</td>
                        <td><span className={`badge ${r.liveness_status === 'PASS' ? 'badge--success' : 'badge--neutral'}`}>{r.liveness_status}</span></td>
                        <td><span className={`badge ${r.status === 'PRESENT' ? 'badge--success' : r.status === 'ABSENT' ? 'badge--error' : r.status === 'MANUAL_REVIEW' ? 'badge--warning' : 'badge--error'}`}>
                          {r.is_derived_absence ? 'ABSENT · No attendance' : r.status}
                        </span></td>
                        <td>
                          {r.is_derived_absence ? <span className="text-sm text-muted">No record</span> : (
                            <div className="flex gap-1">
                              {r.status !== 'PRESENT' && (
                                <button className="btn btn--success btn--sm" onClick={() => handleStatusChange(r.attendance_id, 'PRESENT')}
                                  title="Mark as Present">✅</button>
                              )}
                              {r.status !== 'ABSENT' && (
                                <button className="btn btn--danger btn--sm" onClick={() => handleStatusChange(r.attendance_id, 'ABSENT')}
                                  title="Mark as Absent">❌</button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state"><div className="empty-state__icon">📋</div><div className="empty-state__title">No records found</div></div>
            )}
          </div>
        )}

        {/* Sessions Tab — with Start Attendance */}
        {activeTab === 'sessions' && (
          <div className="animate-in">
            <div className="page-header">
              <h3>📅 Attendance Sessions</h3>
            </div>

            {/* Webcam Attendance Area */}
            {cameraEnabled && attendanceSessionId && (
              <div className="card mb-3" style={{ border: '2px solid var(--primary-500)' }}>
                <div className="flex gap-2 mb-2" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
                  <h4>📸 Live Attendance — Session #{attendanceSessionId}</h4>
                  <button className="btn btn--danger btn--sm" onClick={stopAttendanceCamera}>⏹ Stop Camera</button>
                </div>
                <Camera ref={cameraRef} />
                <div className="flex gap-2 mt-2" style={{ justifyContent: 'center' }}>
                  <button className="btn btn--primary btn--lg" onClick={captureAndVerify} disabled={isProcessing}>
                    {isProcessing ? '⏳ Processing...' : '📸 Capture & Verify'}
                  </button>
                </div>
                {attendanceStatus && (
                  <div className="alert mt-2" style={{
                    background: attendanceStatus.startsWith('✅') ? 'rgba(34,197,94,0.15)' :
                      attendanceStatus.startsWith('📌') ? 'rgba(245,158,11,0.15)' :
                      'rgba(239,68,68,0.15)',
                    border: '1px solid',
                    borderColor: attendanceStatus.startsWith('✅') ? 'var(--success-500)' :
                      attendanceStatus.startsWith('📌') ? 'var(--warning-500)' :
                      'var(--error-500)',
                    padding: '0.75rem 1rem', borderRadius: 8,
                  }}>
                    <strong>{attendanceStatus}</strong>
                  </div>
                )}
                {recognizedList.length > 0 && (
                  <div className="mt-2">
                    <h4 className="mb-1">✅ Recognized Students ({recognizedList.length})</h4>
                    <div className="table-container">
                      <table className="table">
                        <thead><tr><th>#</th><th>Roll Number</th><th>Name</th><th>Confidence</th></tr></thead>
                        <tbody>
                          {recognizedList.map((r, i) => (
                            <tr key={r.student_id}>
                              <td>{i + 1}</td>
                              <td><strong>{r.student_code}</strong></td>
                              <td>{r.student_name}</td>
                              <td>{r.confidence ? `${(r.confidence * 100).toFixed(0)}%` : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Create Session Form */}
            <div className="card mb-3">
              <h4 className="mb-2">Create New Session</h4>
              <form onSubmit={handleCreateSession}>
                <div className="grid-2 mb-2">
                  <div className="input-group">
                    <label className="input-group__label">Session Name *</label>
                    <input className="input" required placeholder="Morning Attendance" value={sessionForm.name}
                      onChange={(e) => setSessionForm({ ...sessionForm, name: e.target.value })} />
                  </div>
                  <div className="input-group">
                    <label className="input-group__label">Subject *</label>
                    <select className="input" required value={sessionForm.subject_id}
                      onChange={(e) => setSessionForm({ ...sessionForm, subject_id: e.target.value })}>
                      <option value="">Select...</option>
                      {subjects.map((s) => <option key={s.subject_id} value={s.subject_id}>{s.name} ({s.subject_code})</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid-3 mb-2">
                  <div className="input-group">
                    <label className="input-group__label">Date *</label>
                    <input className="input" type="date" required value={sessionForm.date}
                      onChange={(e) => setSessionForm({ ...sessionForm, date: e.target.value })} />
                  </div>
                  <div className="input-group">
                    <label className="input-group__label">Start Time *</label>
                    <input className="input" type="time" required value={sessionForm.start_time}
                      onChange={(e) => setSessionForm({ ...sessionForm, start_time: e.target.value })} />
                  </div>
                  <div className="input-group">
                    <label className="input-group__label">End Time *</label>
                    <input className="input" type="time" required value={sessionForm.end_time}
                      onChange={(e) => setSessionForm({ ...sessionForm, end_time: e.target.value })} />
                  </div>
                </div>
                <button type="submit" className="btn btn--primary">➕ Create Session</button>
              </form>
            </div>

            {/* Sessions List */}
            {sessions.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead><tr><th>Name</th><th>Subject</th><th>Date</th><th>Time</th><th>Status</th><th>Action</th></tr></thead>
                  <tbody>
                    {sessions.map((s) => (
                      <tr key={s.session_id}>
                        <td><strong>{s.name}</strong></td>
                        <td>{s.subject_name}</td>
                        <td>{s.date}</td>
                        <td>{new Date(s.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(s.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                        <td><span className={`badge ${s.is_active ? 'badge--success' : 'badge--neutral'}`}>{s.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td><div className="flex gap-1">
                          {s.is_active && (
                            <button className="btn btn--primary btn--sm"
                              onClick={() => startAttendanceCamera(s.session_id)}
                              disabled={cameraEnabled}>
                              📸 Start Attendance
                            </button>
                          )}
                          <button className={`btn btn--sm ${s.is_active ? 'btn--danger' : 'btn--success'}`}
                            onClick={() => handleToggleSession(s.session_id, s.is_active)}>
                            {s.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button className="btn btn--danger btn--sm" onClick={() => handleDeleteSession(s.session_id, s.name)}>Delete</button>
                        </div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state"><div className="empty-state__icon">📅</div><div className="empty-state__title">No sessions yet</div></div>
            )}
          </div>
        )}

        {/* Subjects Tab */}
        {activeTab === 'subjects' && (
          <div className="animate-in">
            <div className="page-header"><h3>📚 Subjects</h3></div>

            <div className="card mb-3">
              <h4 className="mb-2">Create New Subject</h4>
              <form onSubmit={handleCreateSubject} className="grid-3" style={{ alignItems: 'end' }}>
                <div className="input-group">
                  <label className="input-group__label">Code *</label>
                  <input className="input" required placeholder="CS101" value={subjectForm.subject_code}
                    onChange={(e) => setSubjectForm({ ...subjectForm, subject_code: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-group__label">Name *</label>
                  <input className="input" required placeholder="Data Structures" value={subjectForm.name}
                    onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-group__label">Section *</label>
                  <div className="flex gap-1">
                    <input className="input" required placeholder="A" value={subjectForm.section}
                      onChange={(e) => setSubjectForm({ ...subjectForm, section: e.target.value })} style={{ flex: 1 }} />
                    <button type="submit" className="btn btn--primary btn--sm">➕ Create</button>
                  </div>
                </div>
              </form>
            </div>

            {subjects.length > 0 ? (
              <div className="grid-2">
                {subjects.map((s) => (
                  <div className="card" key={s.subject_id}>
                    <h4>{s.name}</h4>
                    <p className="text-sm text-muted mt-1">
                      Code: <span className="badge badge--primary">{s.subject_code}</span> &middot; Section: {s.section}
                    </p>
                    <p className="text-sm mt-1">👥 {s.enrolled_count} enrolled</p>
                    <div className="flex gap-1 mt-2">
                      <select
                        className="input"
                        value={studentToEnroll[s.subject_id] || ''}
                        onChange={(e) => setStudentToEnroll({ ...studentToEnroll, [s.subject_id]: e.target.value })}
                        aria-label={`Student to enroll in ${s.name}`}
                        style={{ flex: 1 }}
                      >
                        <option value="">Enroll a registered student...</option>
                        {students.map((student) => (
                          <option key={student.student_id} value={student.student_id}>
                            {student.student_code} — {student.name}{student.is_active === false ? ' (Deregistered)' : student.has_face_embedding ? '' : ' (face not enrolled)'}
                          </option>
                        ))}
                      </select>
                      <button
                        className="btn btn--primary btn--sm"
                        onClick={() => handleEnrollStudent(s)}
                        disabled={!studentToEnroll[s.subject_id]}
                      >
                        Enroll
                      </button>
                    </div>
                    <div className="mt-2">
                      <p className="text-sm text-muted mb-1">Class roster — administrator controls</p>
                      {(subjectRosters[s.subject_id] || []).length > 0 ? (
                        <div className="flex flex-col gap-1">
                          {subjectRosters[s.subject_id].map((student) => (
                            <div key={student.student_id} className="flex gap-1" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
                              <span className="text-sm">
                                {student.student_code} — {student.name} {!student.has_face_embedding && '(no face enrolled)'}
                              </span>
                              <div className="flex gap-1">
                                <button className="btn btn--secondary btn--sm" onClick={() => handleRemoveFromClass(s, student)}>
                                  Remove from class
                                </button>
                                <button className="btn btn--danger btn--sm" onClick={() => handleEraseFace(s, student)}>
                                  Erase face
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted">No students enrolled in this subject.</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><div className="empty-state__icon">📚</div><div className="empty-state__title">No subjects yet</div></div>
            )}
          </div>
        )}

        {activeTab === 'students' && (
          <div className="animate-in">
            <div className="page-header"><h3>👥 Student Information</h3></div>
            <p className="text-muted mb-2">Passwords are never displayed. An administrator can set a new password when a student cannot sign in.</p>
            {students.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead><tr><th>Student ID</th><th>Name</th><th>Mobile</th><th>Email</th><th>Department / Year</th><th>Face enrollment</th><th>Account</th><th>Password</th></tr></thead>
                  <tbody>
                    {students.map((student) => (
                      <tr key={student.student_id}>
                        <td><strong>{student.student_code}</strong></td>
                        <td>{student.name}</td>
                        <td>{student.mobile_number || '—'}</td>
                        <td>{student.email || '—'}</td>
                        <td>{student.department || '—'}{student.year ? ` / ${student.year}` : ''}</td>
                        <td><span className={`badge ${student.has_face_embedding ? 'badge--success' : 'badge--neutral'}`}>{student.has_face_embedding ? 'Enrolled' : 'Not enrolled'}</span></td>
                        <td><span className={`badge ${student.is_active ? 'badge--success' : 'badge--error'}`}>{student.account_status}</span></td>
                        <td>
                          {student.is_active && studentPasswordReset.studentId === student.student_id ? (
                            <form onSubmit={(event) => handleResetStudentPassword(event, student)} className="flex gap-1" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
                              <input className="input" type="password" required minLength="4" maxLength="100"
                                aria-label={`New password for ${student.student_code}`} placeholder="New password"
                                autoComplete="new-password" value={studentPasswordReset.password}
                                onChange={(event) => setStudentPasswordReset((current) => ({ ...current, password: event.target.value }))} />
                              <input className="input" type="password" required minLength="4" maxLength="100"
                                aria-label={`Confirm new password for ${student.student_code}`} placeholder="Confirm password"
                                autoComplete="new-password" value={studentPasswordReset.confirmation}
                                onChange={(event) => setStudentPasswordReset((current) => ({ ...current, confirmation: event.target.value }))} />
                              <button className="btn btn--primary btn--sm" type="submit">Save</button>
                              <button className="btn btn--ghost btn--sm" type="button"
                                onClick={() => setStudentPasswordReset({ studentId: null, password: '', confirmation: '' })}>Cancel</button>
                            </form>
                          ) : (
                            <button className="btn btn--secondary btn--sm" disabled={!student.is_active}
                              onClick={() => { setFormError(''); setFormSuccess(''); setStudentPasswordReset({ studentId: student.student_id, password: '', confirmation: '' }); }}>
                              Reset password
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state"><div className="empty-state__icon">👥</div><div className="empty-state__title">No students registered yet</div></div>
            )}

            <section className="card mt-3" style={{ border: '1px solid var(--error-500)' }}>
              <h4 style={{ color: 'var(--error-500)' }}>Danger zone: Clear all data</h4>
              <p className="text-sm text-muted mt-1">
                Permanently deletes student profiles and face data, classes, enrollments, sessions, and attendance records.
                Administrator accounts are kept so you can continue using the app.
              </p>
              {!clearDataOpen ? (
                <button className="btn btn--danger mt-2" onClick={() => { setFormError(''); setFormSuccess(''); setClearDataOpen(true); }}>
                  Clear all data
                </button>
              ) : (
                <form onSubmit={handleClearAllData} className="mt-2" style={{ maxWidth: 520 }}>
                  <div className="input-group mb-2">
                    <label className="input-group__label" htmlFor="clear-data-admin-password">Administrator password</label>
                    <input id="clear-data-admin-password" className="input" type="password" autoComplete="current-password"
                      required value={clearDataForm.password}
                      onChange={(event) => setClearDataForm((current) => ({ ...current, password: event.target.value }))} />
                  </div>
                  <div className="input-group mb-2">
                    <label className="input-group__label" htmlFor="clear-data-confirmation">Type DELETE ALL DATA to confirm</label>
                    <input id="clear-data-confirmation" className="input" type="text" required autoComplete="off"
                      value={clearDataForm.confirmation}
                      onChange={(event) => setClearDataForm((current) => ({ ...current, confirmation: event.target.value }))} />
                  </div>
                  <div className="flex gap-1">
                    <button className="btn btn--danger" type="submit">Confirm clear all data</button>
                    <button className="btn btn--secondary" type="button"
                      onClick={() => { setClearDataOpen(false); setClearDataForm({ password: '', confirmation: '' }); }}>Cancel</button>
                  </div>
                </form>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
