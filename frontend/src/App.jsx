/**
 * AI Attendance System — App Root
 *
 * Routes:
 *   /                — Redirect to attendance
 *   /login           — Teacher login/register
 *   /register        — Student registration + face enrollment
 *   /attendance      — Live webcam attendance flow
 *   /dashboard       — Teacher dashboard (subjects, sessions, records)
 *   /student/account — Student account management
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import StudentRegister from './pages/StudentRegister';
import AttendancePage from './pages/AttendancePage';
import AdminDashboard from './pages/AdminDashboard';
import StudentAccount from './pages/StudentAccount';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/attendance" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<StudentRegister />} />
      <Route path="/attendance" element={<AttendancePage />} />
      <Route path="/student/account" element={<StudentAccount />} />
      <Route path="/student/dashboard" element={<StudentAccount />} />
      <Route path="/dashboard" element={<AdminDashboard />} />
    </Routes>
  );
}
