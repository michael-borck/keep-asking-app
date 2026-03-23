import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login({ condition, onLogin }) {
  const [studentNumber, setStudentNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!studentNumber.trim()) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_number: studentNumber.trim(),
          condition: condition,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Login failed");
      }

      const data = await res.json();
      onLogin({
        sessionCode: data.session_code,
        condition: data.condition,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>AI Lab Session</h1>
        <p>
          Enter your student number to begin. This is used only to link
          equity indicators to your session and will be permanently deleted
          after the study.
        </p>
        {error && <div className="login-error">{error}</div>}
        <input
          type="text"
          placeholder="Student number"
          value={studentNumber}
          onChange={(e) => setStudentNumber(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading || !studentNumber.trim()}>
          {loading ? "Starting session..." : "Start Session"}
        </button>
      </form>
    </div>
  );
}
