import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";

// Radio group helper for equity questions
function EquityRadio({ name, value, onChange, options }) {
  return (
    <div className="equity-options">
      {options.map((opt) => (
        <label key={opt} className={`equity-option ${value === opt ? "selected" : ""}`}>
          <input
            type="radio"
            name={name}
            value={opt}
            checked={value === opt}
            onChange={(e) => onChange(e.target.value)}
          />
          <span>{opt}</span>
        </label>
      ))}
    </div>
  );
}

export default function Login({ condition, onLogin }) {
  const [consented, setConsented] = useState(null); // null = not chosen, true/false
  const [firstInFamily, setFirstInFamily] = useState("");
  const [lowSes, setLowSes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pisOpen, setPisOpen] = useState(false);

  async function handleProceed(e) {
    e.preventDefault();
    if (consented === null) return;

    setLoading(true);
    setError("");

    try {
      const token = new URLSearchParams(window.location.search).get("token");
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          condition: condition,
          consented: consented,
          token: token,
          first_in_family: consented ? (firstInFamily || "Prefer not to say") : null,
          low_ses: consented ? (lowSes || "Prefer not to say") : null,
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

  return (
    <div className="login-container">
      <form className="login-card consent-card" onSubmit={handleProceed}>
        <img src="/logo-curtin.png" alt="Curtin University" className="curtin-logo" />
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
              <strong>HREC approval number:</strong> 83897
            </p>
            <p>
              <strong>Investigators:</strong> Michael Borck (Principal Investigator);
              Marcela Moraes (Co-Investigator); Torsten Reiners (Co-Investigator);
              Renee Ralph (Co-Investigator)
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
              No personal identifying information (such as your name or student
              number) is collected at any stage. All data is tagged with a random
              session code only. The research team analyses only anonymous data.
              The following people will have access to the data: the research team
              and, in the event of an audit or investigation, staff from the
              Research Office at Curtin. Data will be stored securely on Curtin
              University systems for 7 years after the research is published or
              completed, and then destroyed.
            </p>

            <h4>Data sharing</h4>
            <p>
              Aggregate findings and anonymous excerpts from this study may be
              shared with other researchers and published in peer-reviewed outlets
              and open-access resources. No individual-level data or raw
              transcripts will be shared. Results will be published in a
              peer-reviewed journal and shared as an open-access resource pack
              available to any teaching team.
            </p>

            <h4>Voluntary participation and withdrawal</h4>
            <p>
              Participation is voluntary and will not affect your studies or your
              relationship with the University, staff, or colleagues. You may stop
              participating at any time during the session. Because no identifying
              information is collected, withdrawal after the session is not
              possible as individual records cannot be identified.
            </p>

            <h4>Contact and complaints</h4>
            <p>
              For questions about the study: michael.borck@curtin.edu.au
            </p>
            <p>
              Curtin University Human Research Ethics Committee (HREC) has
              approved this study (HREC number 83897). Should you wish
              to discuss the study with someone not directly involved, or wish to
              make a confidential complaint, contact the Ethics Office on (08) 9266
              9223 or HREC@curtin.edu.au, or the Manager, Research Integrity on
              (08) 9266 7093.
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
              You understand that no personal identifying information (such as
              your name or student number) is collected. All data is tagged with
              a random session code only.
            </li>
            <li>
              You consent to logging of your AI conversation and to completing a
              brief exit survey within the app.
            </li>
            <li>
              You consent to the use of anonymous data in publications and
              teaching resources.
            </li>
            <li>
              You consent to aggregate findings and anonymous excerpts from this
              study being shared with other researchers and published in
              peer-reviewed outlets and open-access resources.
            </li>
            <li>
              You understand you may stop participating at any time during the
              session. Because no identifying information is collected, withdrawal
              after the session is not possible as individual records cannot be
              identified.
            </li>
            <li>
              I understand that this project has been approved by Curtin
              University Human Research Ethics Committee and will be carried out
              in line with the National Statement on Ethical Conduct in Human
              Research (2025).
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

        {consented === true && (
          <div className="equity-section">
            <p className="equity-intro">
              The following questions help us understand whether this
              intervention benefits all students equally. Your answers are stored
              with your anonymous session code only and cannot be linked to your
              identity. You may select "Prefer not to say" for either question.
            </p>

            <div className="equity-question">
              <label>
                Are you the first person in your immediate family to attend
                university?
              </label>
              <EquityRadio
                name="first_in_family"
                value={firstInFamily}
                onChange={setFirstInFamily}
                options={["Yes", "No", "Prefer not to say"]}
              />
            </div>

            <div className="equity-question">
              <label>
                Do you identify as being from a low socioeconomic background?
              </label>
              <EquityRadio
                name="low_ses"
                value={lowSes}
                onChange={setLowSes}
                options={["Yes", "No", "Prefer not to say"]}
              />
            </div>
          </div>
        )}

        {error && <div className="login-error">{error}</div>}

        <button type="submit" disabled={loading || consented === null}>
          {loading ? "Starting session..." : "Proceed"}
        </button>
      </form>
    </div>
  );
}
