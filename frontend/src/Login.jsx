import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";

export default function Login({ condition, onLogin }) {
  const [consented, setConsented] = useState(null); // null = not chosen, true/false
  const [studentNumber, setStudentNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleProceed(e) {
    e.preventDefault();
    if (consented === null) return;
    if (consented && !studentNumber.trim()) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_number: consented ? studentNumber.trim() : "",
          condition: condition,
          consented: consented,
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

  const canProceed =
    consented === false || (consented === true && studentNumber.trim());

  return (
    <div className="login-container">
      <form className="login-card consent-card" onSubmit={handleProceed}>
        <h1>AI Lab Session</h1>

        <p className="study-description">
          This study compares how students interact with an AI tool under
          different interface configurations.
        </p>

        <div className="consent-options">
          <label
            className={`consent-option ${consented === true ? "selected" : ""}`}
          >
            <input
              type="radio"
              name="consent"
              checked={consented === true}
              onChange={() => setConsented(true)}
            />
            <div className="consent-option-body">
              <span className="consent-label">I consent</span>
              <span className="consent-detail">
                My conversation may be recorded and processed as part of this
                exercise.
              </span>
              {consented === true && (
                <input
                  type="text"
                  className="student-id-input"
                  placeholder="Enter your student ID"
                  value={studentNumber}
                  onChange={(e) => setStudentNumber(e.target.value)}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              )}
            </div>
          </label>

          <label
            className={`consent-option ${consented === false ? "selected" : ""}`}
          >
            <input
              type="radio"
              name="consent"
              checked={consented === false}
              onChange={() => setConsented(false)}
            />
            <div className="consent-option-body">
              <span className="consent-label">I do not consent</span>
              <span className="consent-detail">
                No data is logged. Please continue with the exercise.
              </span>
            </div>
          </label>
        </div>

        {error && <div className="login-error">{error}</div>}

        <button type="submit" disabled={loading || !canProceed}>
          {loading ? "Starting session..." : "Proceed"}
        </button>
      </form>
    </div>
  );
}
