/**
 * VeriAttend — API Client
 *
 * Centralized HTTP client for all backend API calls.
 * Uses axios with JWT token management.
 */

import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('veriattend_token');
  // A student account request supplies its own scoped token.
  const isStudentLogin = config.url?.includes('/students/login');
  if (token && !config.headers.Authorization && !isStudentLogin) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses — only clear token if one was sent and rejected
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only clear and redirect if a token was actually sent (meaning it's invalid/expired)
      // Don't redirect if we're on login page or if the request was the login request itself
      const isLoginPage = window.location.pathname.includes('/login');
      const requestUrl = error.config?.url || '';
      const isLoginRequest = requestUrl.includes('/auth/login') || requestUrl.includes('/students/login');
      const isRegisterRequest = error.config?.url?.includes('/auth/register');

      if (!isLoginPage && !isLoginRequest && !isRegisterRequest) {
        // Token was rejected — it's invalid or expired
        const hadToken = localStorage.getItem('veriattend_token');
        if (hadToken) {
          localStorage.removeItem('veriattend_token');
          localStorage.removeItem('veriattend_teacher');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

// ── Students ──
export const studentsAPI = {
  register: (data) => api.post('/students', data),
  list: () => api.get('/students'),
  get: (id) => api.get(`/students/${id}`),
  update: (id, data) => api.put(`/students/${id}`, data),
  enrollFace: (id, frameData) =>
    api.post(`/students/${id}/enroll-face`, { student_id: id, frame_data: frameData }),
  removeFace: (id, subjectId) => api.delete(`/students/${id}/face`, { params: { subject_id: subjectId } }),
  login: (data) => api.post('/students/login', data),
  me: (config = {}) => api.get('/students/me', config),
  monthlyAttendance: (month, config = {}) =>
    api.get('/students/me/attendance', { ...config, params: { month } }),
  attendanceSummary: (config = {}) => api.get('/students/me/attendance-summary', config),
  deregister: (data, config = {}) => api.delete('/students/me', { ...config, data }),
};

// ── Enrollment ──
export const enrollmentAPI = {
  enroll: (data) => api.post('/enrollment/enroll', data),
  unenroll: (studentId, subjectId) =>
    api.delete(`/enrollment/unenroll?student_id=${studentId}&subject_id=${subjectId}`),
  getStudents: (subjectId) => api.get(`/enrollment/${subjectId}/students`),
};

// ── Recognition ──
export const recognitionAPI = {
  detect: (frameData) => api.post('/recognition/detect', { frame_data: frameData }),
  recognize: (frameData) => api.post('/recognition/recognize', { frame_data: frameData }),
};

// ── Liveness ──
export const livenessAPI = {
  createChallenge: (groupMode = false) => api.post('/liveness/challenge', { group_mode: groupMode }),
  verify: (challengeId, frameData) =>
    api.post('/liveness/verify', { challenge_id: challengeId, frame_data: frameData }),
  passiveCheck: (frameData) =>
    api.post('/liveness/passive-check', { frame_data: frameData }),
};

// ── Attendance ──
export const attendanceAPI = {
  mark: (data) => api.post('/attendance/mark', data),
  markGroup: (data) => api.post('/attendance/mark-group', data),
  getRecords: (params) => api.get('/attendance/records', { params }),
  getStudentRecords: (studentId) => api.get(`/attendance/student/${studentId}`),
};

// ── Sessions ──
export const sessionsAPI = {
  create: (data) => api.post('/sessions', data),
  list: (params) => api.get('/sessions', { params }),
  listActive: () => api.get('/sessions/active'),
  get: (id) => api.get(`/sessions/${id}`),
  toggle: (id, isActive) => api.put(`/sessions/${id}/toggle`, { is_active: isActive }),
  remove: (id) => api.delete(`/sessions/${id}`),
};


// ── Admin ──
export const adminAPI = {
  dashboard: () => api.get('/admin/dashboard'),
  createSubject: (data) => api.post('/admin/subjects', data),
  listSubjects: () => api.get('/admin/subjects'),
  listStudents: () => api.get('/admin/students'),
  resetStudentPassword: (studentId, password) =>
    api.put(`/admin/students/${studentId}/password`, { password }),
  clearData: (data) => api.delete('/admin/data', { data }),
  getAttendance: (params) => api.get('/admin/attendance', { params }),
  updateAttendanceStatus: (attendanceId, newStatus) =>
    api.put(`/admin/attendance/${attendanceId}/status`, null, { params: { new_status: newStatus } }),
};

// ── Config ──
export const configAPI = {
  getPublic: () => api.get('/config'),
};

export default api;
