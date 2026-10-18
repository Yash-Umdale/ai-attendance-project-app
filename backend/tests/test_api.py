"""
VeriAttend — API Integration Tests

Tests the FastAPI endpoints using the test client.
Covers: registration, login, student creation, duplicate handling, invalid requests.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from models.database import Base, get_db


# ── Test Database Setup ──
TEST_DATABASE_URL = "sqlite:///./test_veriattend.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


# ── Test 1: Health Check ──
def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Test: Teacher Registration ──
def test_teacher_registration():
    """Test 1: Successful teacher registration."""
    response = client.post("/api/auth/register", json={
        "username": "testteacher",
        "password": "testpass123",
        "name": "Test Teacher",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testteacher"
    assert data["name"] == "Test Teacher"


# ── Test: Duplicate Teacher Registration ──
def test_duplicate_teacher_registration():
    """Test 2: Reject duplicate username."""
    client.post("/api/auth/register", json={
        "username": "dupteacher", "password": "pass", "name": "Teacher 1",
    })
    response = client.post("/api/auth/register", json={
        "username": "dupteacher", "password": "pass2", "name": "Teacher 2",
    })
    assert response.status_code == 409


# ── Test: Teacher Login ──
def test_teacher_login():
    """Test: Successful login returns JWT token."""
    client.post("/api/auth/register", json={
        "username": "logintest", "password": "mypass", "name": "Login Teacher",
    })
    response = client.post("/api/auth/login", json={
        "username": "logintest", "password": "mypass",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ── Test: Invalid Login ──
def test_invalid_login():
    """Test 15: Invalid credentials rejected."""
    response = client.post("/api/auth/login", json={
        "username": "nonexistent", "password": "wrong",
    })
    assert response.status_code == 401


# ── Test: Student Registration ──
def test_student_registration():
    """Test 1: Student registration."""
    response = client.post("/api/students", json={
        "student_code": "CS001",
        "name": "Test Student",
        "email": "test@example.com",
        "department": "Computer Science",
        "year": "3rd",
        "password": "studentpass",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["student_code"] == "CS001"
    assert data["has_face_embedding"] == False


def test_student_can_deregister_only_their_own_account():
    """Deregistration clears active biometric/enrollment data but retains profile."""
    response = client.post("/api/students", json={
        "student_code": "DEREG001", "name": "Deregister Me", "password": "studentpass",
    })
    student_id = response.json()["student_id"]
    login = client.post("/api/students/login", json={"student_code": "DEREG001", "password": "studentpass"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.request("DELETE", "/api/students/me", headers=headers, json={"password": "wrong", "confirmation": "DEREGISTER"})
    assert denied.status_code == 401
    deleted = client.request("DELETE", "/api/students/me", headers=headers, json={"password": "studentpass", "confirmation": "DEREGISTER"})
    assert deleted.status_code == 200
    profile = client.get(f"/api/students/{student_id}").json()
    assert profile["account_status"] == "Deregistered"
    assert profile["has_face_embedding"] is False
    assert client.get("/api/students/me", headers=headers).status_code == 401


# ── Test: Duplicate Student ID ──
def test_duplicate_student_code():
    """Test 2: Reject duplicate student IDs."""
    client.post("/api/students", json={
        "student_code": "DUP001", "name": "Student 1",
    })
    response = client.post("/api/students", json={
        "student_code": "DUP001", "name": "Student 2",
    })
    assert response.status_code == 409


# ── Test: List Students ──
def test_list_students():
    """Test: List all registered students."""
    client.post("/api/students", json={"student_code": "LIST001", "name": "S1"})
    client.post("/api/students", json={"student_code": "LIST002", "name": "S2"})

    response = client.get("/api/students")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


# ── Test: Get Student ──
def test_get_student():
    """Test: Get student by ID."""
    create_res = client.post("/api/students", json={
        "student_code": "GET001", "name": "Get Student",
    })
    student_id = create_res.json()["student_id"]

    response = client.get(f"/api/students/{student_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Student"


# ── Test: Get Non-existent Student ──
def test_get_nonexistent_student():
    """Test 15: 404 for non-existent student."""
    response = client.get("/api/students/99999")
    assert response.status_code == 404


# ── Test: Invalid Registration (missing required fields) ──
def test_invalid_student_registration():
    """Test 15: Invalid request rejected."""
    response = client.post("/api/students", json={
        "name": "No Code Student",
        # Missing student_code
    })
    assert response.status_code == 422  # Validation error


# Liveness challenge test removed — liveness router was simplified
# and is now called internally by the attendance/mark endpoint.


# ── Test: Public Config ──
def test_public_config():
    """Test: Public config returns non-sensitive values."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "camera_sample_interval_ms" in data
    assert "app_name" in data
    # Should NOT contain sensitive values
    assert "JWT_SECRET" not in str(data)
    assert "DATABASE_URL" not in str(data)


# ── Test: Manual Review (13 & 14 — covered via decision engine) ──
# Review approval/rejection is tested via the decision engine tests
# and would require a full setup with attendance records.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
