/**
 * VeriAttend — Student Registration Page
 *
 * Registration flow:
 * 1. Enter student details
 * 2. Open webcam
 * 3. Capture face
 * 4. Backend validates (single face, quality)
 * 5. Generates embedding
 * 6. Registration complete
 */

import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Camera from '../components/Camera';
import { studentsAPI } from '../api/client';

export default function StudentRegister() {
  const navigate = useNavigate();
  const cameraRef = useRef(null);

  const [step, setStep] = useState(1); // 1: form, 2: camera
  const [form, setForm] = useState({
    student_code: '', name: '', email: '', mobile_number: '', department: '', year: '', password: '', confirmPassword: '',
  });
  const [studentId, setStudentId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.'); setLoading(false); return;
    }

    try {
      const { confirmPassword, ...registration } = form;
      const res = await studentsAPI.register(registration);
      setStudentId(res.data.student_id);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Cannot contact the backend. Start the backend terminal, then refresh this page.');
    } finally {
      setLoading(false);
    }
  };

  const handleCaptureFace = async () => {
    if (!cameraRef.current || !studentId) return;
    const frame = cameraRef.current.captureFrame();
    if (!frame) return;

    setLoading(true);
    setError('');

    try {
      await studentsAPI.enrollFace(studentId, frame);
      setSuccess('Registration complete! Face enrolled successfully.');
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || 'Cannot contact the backend. Start the backend terminal, then refresh this page.');
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
      </header>

      <main className="app-main" style={{ maxWidth: 640, margin: '0 auto' }}>
        <div className="animate-in">
          <h1 className="mb-2">Student Registration</h1>
          <p className="text-muted mb-3">Register your profile and enroll your face for attendance</p>

          {/* Progress */}
          <div className="flex gap-2 mb-3">
            {[1, 2, 3].map((s) => (
              <div key={s} style={{
                flex: 1, height: 4, borderRadius: 2,
                background: s <= step ? 'var(--primary-500)' : 'var(--bg-elevated)',
                transition: 'background 0.3s',
              }} />
            ))}
          </div>

          {error && <div className="alert alert--error mb-2">⚠️ {error}</div>}
          {success && <div className="alert alert--success mb-2">✅ {success}</div>}

          {/* Step 1: Form */}
          {step === 1 && (
            <form onSubmit={handleRegister} className="card">
              <h3 className="mb-2">📋 Student Details</h3>
              <div className="input-group mb-2">
                <label className="input-group__label">Student ID *</label>
                <input className="input" required placeholder="e.g. CS2024001"
                  value={form.student_code} onChange={(e) => setForm({ ...form, student_code: e.target.value })} id="input-student-code" />
              </div>
              <div className="input-group mb-2">
                <label className="input-group__label">Full Name *</label>
                <input className="input" required placeholder="e.g. Yash Umdale"
                  value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} id="input-student-name" />
              </div>
              <div className="input-group mb-2">
                <label className="input-group__label">Email</label>
                <input className="input" type="email" placeholder="yash@example.com"
                  value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} id="input-student-email" />
              </div>
              <div className="input-group mb-2">
                <label className="input-group__label">Mobile Number *</label>
                <input className="input" type="tel" placeholder="9876543210" required
                  value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} id="input-student-mobile" />
              </div>
              <div className="grid-2 mb-2">
                <div className="input-group">
                  <label className="input-group__label">Department</label>
                  <input className="input" placeholder="Computer Science"
                    value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-group__label">Year</label>
                  <input className="input" placeholder="3rd Year"
                    value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
                </div>
              </div>
              <div className="grid-2 mb-2">
                <div className="input-group">
                  <label className="input-group__label">Account Password *</label>
                  <input className="input" type={showPasswords ? 'text' : 'password'} required minLength="4" value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-group__label">Confirm Password *</label>
                  <input className="input" type={showPasswords ? 'text' : 'password'} required minLength="4" value={form.confirmPassword}
                    onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} />
                </div>
              </div>
              <label className="text-sm text-muted flex gap-1" style={{ alignItems: 'center', cursor: 'pointer' }}>
                <input type="checkbox" checked={showPasswords} onChange={(e) => setShowPasswords(e.target.checked)} />
                Show passwords while typing
              </label>
              <button type="submit" className="btn btn--primary btn--full btn--lg mt-2" disabled={loading} id="btn-register-student">
                {loading ? 'Registering...' : 'Continue to Face Enrollment →'}
              </button>
            </form>
          )}

          {/* Step 2: Camera */}
          {step === 2 && (
            <div className="card">
              <h3 className="mb-2">📸 Face Enrollment</h3>
              <p className="text-sm text-muted mb-2">Position your face in the center and capture</p>
              <Camera ref={cameraRef} />
              <button className="btn btn--primary btn--full btn--lg mt-2" onClick={handleCaptureFace} disabled={loading} id="btn-capture-face">
                {loading ? 'Processing...' : '📸 Capture & Enroll Face'}
              </button>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 3 && (
            <div className="card text-center" style={{ padding: '3rem' }}>
              <div style={{ fontSize: '4rem' }}>🎉</div>
              <h2 className="mt-2">Registration Complete!</h2>
              <p className="text-muted mt-1">Your face has been enrolled. You can now use VeriAttend for attendance.</p>
              <div className="flex gap-2 mt-3" style={{ justifyContent: 'center' }}>
                <button className="btn btn--primary" onClick={() => navigate('/attendance')}>
                  Go to Attendance →
                </button>
                <button className="btn btn--secondary" onClick={() => { setStep(1); setForm({ student_code: '', name: '', email: '', mobile_number: '', department: '', year: '', password: '', confirmPassword: '' }); setSuccess(''); }}>
                  Register Another
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
