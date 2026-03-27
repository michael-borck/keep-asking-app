import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";

export default function Login({ condition, onLogin }) {
  const [consented, setConsented] = useState(null); // null = not chosen, true/false
  const [studentNumber, setStudentNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pisOpen, setPisOpen] = useState(false);

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
        consented: data.consented,
        labId: data.lab_id,
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
          This session is part of a research study on how students interact with
          AI tools during structured tasks. A Participant Information Sheet was
          provided on your unit's Blackboard page.
        </p>

        <details
          className="pis-details"
          open={pisOpen}
          onToggle={(e) => setPisOpen(e.target.open)}
        >
          <summary>View Participant Information Sheet</summary>
          <div className="pis-content">
            <p>
              <strong>Project:</strong> Scaffolding AI Interaction: A Low-Cost
              Intervention for Equitable Student Engagement
            </p>
            <p>
              <strong>Investigators:</strong> Michael Borck (PI); Marcela Moraes;
              Torsten Reiners; Renee Ralph
            </p>

            <h4>What is this study about?</h4>
            <p>
              We are studying how students interact with AI during structured
              tasks and whether different configurations of the AI interface
              affect interaction quality and task outcomes.
            </p>

            <h4>What will I be asked to do?</h4>
            <ul>
              <li>
                Complete a short, course-relevant task using a
                university-provided AI tool (30-45 minutes).
              </li>
              <li>
                Complete a brief exit survey within the app (approximately 8-10
                minutes).
              </li>
            </ul>

            <h4>Are there any risks?</h4>
            <p>
              Risks are minimal (e.g., mild performance awareness). You may stop
              at any time. Participation does not affect your grades.
            </p>

            <h4>Privacy and confidentiality</h4>
            <p>
              Your student number is used only to link equity indicators to your
              session data and is then permanently deleted. Your conversation and
              survey responses are tagged with a random session code only — your
              name and student number do not appear in the research data.
            </p>

            <h4>Withdrawal</h4>
            <p>
              You may withdraw at any time before data de-identification by
              contacting the research team and quoting your session code. Once
              de-identification is complete, withdrawal is no longer possible as
              individual records cannot be identified.
            </p>

            <p className="pis-contact">
              Questions: michael.borck@curtin.edu.au | Ethics concerns:
              hrec@curtin.edu.au
            </p>
          </div>
        </details>

        <div className="consent-items">
          <p className="consent-items-heading">
            By consenting, you confirm that:
          </p>
          <ul>
            <li>You have read and understood the Participant Information Sheet.</li>
            <li>
              You understand participation is voluntary and will not affect your
              grades.
            </li>
            <li>
              You understand your student number is collected to link equity
              indicators and will be permanently deleted after linkage.
            </li>
            <li>
              You consent to logging of your AI conversation and completing the
              exit survey.
            </li>
            <li>
              You consent to the use of de-identified data in publications and
              teaching resources.
            </li>
            <li>
              You understand you may withdraw before de-identification by quoting
              your session code.
            </li>
          </ul>
        </div>

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
              <span className="consent-label">
                I have read the information above and consent to participate
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
                You will still complete the same task as a learning activity. No
                data will be logged.
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
