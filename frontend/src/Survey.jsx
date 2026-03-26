import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";

// Likert scale helper
function LikertGroup({ name, value, onChange, labels }) {
  return (
    <div className="likert-group">
      {labels.map((label, i) => (
        <label key={i} className={`likert-option ${value === String(i + 1) ? "selected" : ""}`}>
          <input
            type="radio"
            name={name}
            value={String(i + 1)}
            checked={value === String(i + 1)}
            onChange={(e) => onChange(e.target.value)}
          />
          <span className="likert-number">{i + 1}</span>
          <span className="likert-label">{label}</span>
        </label>
      ))}
    </div>
  );
}

// Radio group for non-likert questions
function RadioGroup({ name, value, onChange, options }) {
  return (
    <div className="radio-group">
      {options.map((opt, i) => (
        <label key={i} className={`radio-option ${value === opt ? "selected" : ""}`}>
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

const DISCIPLINE_OPTIONS = [
  "Business Information Systems",
  "Innovation, Entrepreneurship, Strategy and International Business",
  "People, Culture and Organisations",
  "Marketing",
  "Logistics and Supply Chain Management",
  "Tourism, Hospitality and Events",
  "Other",
];

export default function Survey({ session, onComplete }) {
  const [answers, setAnswers] = useState({});
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  function set(key, value) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => prev.filter((e) => e !== key));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    // Validate required fields
    const required = [
      "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q8a",
      "q9", "q10", "q11", "q12", "q13",
    ];
    const missing = required.filter((f) => !answers[f]);
    if (missing.length > 0) {
      setErrors(missing);
      // Scroll to first error
      const firstError = document.querySelector(".survey-error");
      if (firstError) firstError.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setSubmitting(true);
    setSubmitError("");

    try {
      const res = await fetch(`${API_URL}/api/survey`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_code: session.sessionCode,
          responses: answers,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Survey submission failed");
      }
      onComplete();
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function hasError(field) {
    return errors.includes(field);
  }

  return (
    <div className="survey-container">
      <div className="survey-card">
        <h1>Exit Survey</h1>
        <p className="survey-intro">
          Please take a few minutes to answer the following questions about your
          session today.
        </p>

        <form onSubmit={handleSubmit}>
          {/* Section 1: Session Code */}
          <div className="survey-section">
            <h2>Your Session Code</h2>
            <div className="session-code-display">
              Your session code is: <strong>{session.sessionCode}</strong>
            </div>
          </div>

          {/* Section 2: Your Task */}
          <div className="survey-section">
            <h2>Your Task</h2>

            <div className={`survey-question ${hasError("q2") ? "survey-error" : ""}`}>
              <label>
                How confident are you that your final task output today was
                accurate and well-reasoned?
              </label>
              <LikertGroup
                name="q2"
                value={answers.q2}
                onChange={(v) => set("q2", v)}
                labels={[
                  "Not confident at all",
                  "Slightly confident",
                  "Moderately confident",
                  "Quite confident",
                  "Very confident",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q3") ? "survey-error" : ""}`}>
              <label>
                How satisfied are you with the quality of your final task output?
              </label>
              <LikertGroup
                name="q3"
                value={answers.q3}
                onChange={(v) => set("q3", v)}
                labels={[
                  "Very unsatisfied",
                  "Unsatisfied",
                  "Neutral",
                  "Satisfied",
                  "Very satisfied",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q4") ? "survey-error" : ""}`}>
              <label>
                At any point during the session, did something the AI said seem
                wrong, incomplete, or surprising to you?
              </label>
              <RadioGroup
                name="q4"
                value={answers.q4}
                onChange={(v) => set("q4", v)}
                options={["Yes", "No", "Not sure"]}
              />
            </div>

            {answers.q4 === "Yes" && (
              <div className="survey-question conditional">
                <label>
                  Briefly describe what seemed wrong or surprising.
                </label>
                <textarea
                  value={answers.q4a || ""}
                  onChange={(e) => set("q4a", e.target.value)}
                  rows={3}
                  placeholder="Optional"
                />
              </div>
            )}
          </div>

          {/* Section 3: How You Worked with the AI */}
          <div className="survey-section">
            <h2>How You Worked with the AI</h2>

            <div className={`survey-question ${hasError("q5") ? "survey-error" : ""}`}>
              <label>
                Which of the following best describes how you worked with the AI
                tool today?
              </label>
              <RadioGroup
                name="q5"
                value={answers.q5}
                onChange={(v) => set("q5", v)}
                options={[
                  "I mostly accepted what the AI said and used it to build my response",
                  "I sometimes pushed back or asked follow-up questions, but mostly accepted the responses",
                  "I regularly pushed back, questioned, or extended the AI responses",
                  "I treated the AI as a thinking partner throughout - challenging it and building on its responses",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q6") ? "survey-error" : ""}`}>
              <label>
                How much did you feel like you were directing the conversation
                with the AI, versus following where it led?
              </label>
              <LikertGroup
                name="q6"
                value={answers.q6}
                onChange={(v) => set("q6", v)}
                labels={[
                  "The AI mostly led, I followed",
                  "The AI led more than I did",
                  "About equal",
                  "I led more than the AI",
                  "I directed the conversation throughout",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q7") ? "survey-error" : ""}`}>
              <label>
                Did you feel the AI tool was helpful for completing the task
                today?
              </label>
              <LikertGroup
                name="q7"
                value={answers.q7}
                onChange={(v) => set("q7", v)}
                labels={[
                  "Not helpful at all",
                  "Slightly helpful",
                  "Moderately helpful",
                  "Quite helpful",
                  "Extremely helpful",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q8") ? "survey-error" : ""}`}>
              <label>
                Did anything about the AI tool's responses make you want to ask a
                follow-up question or push back?
              </label>
              <RadioGroup
                name="q8"
                value={answers.q8}
                onChange={(v) => set("q8", v)}
                options={[
                  "Yes, frequently",
                  "Yes, occasionally",
                  "No, the responses seemed complete and I accepted them",
                  "No, I was unsure how to push back even if I wanted to",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q8a") ? "survey-error" : ""}`}>
              <label>
                Did you notice anything unusual or different about the way the AI
                responded today (for example, any extra text or prompts in the
                responses)?
              </label>
              <RadioGroup
                name="q8a"
                value={answers.q8a}
                onChange={(v) => set("q8a", v)}
                options={["Yes", "No", "Not sure"]}
              />
            </div>

            {answers.q8a === "Yes" && (
              <div className="survey-question conditional">
                <label>Briefly describe what you noticed.</label>
                <textarea
                  value={answers.q8b || ""}
                  onChange={(e) => set("q8b", e.target.value)}
                  rows={3}
                  placeholder="Optional"
                />
              </div>
            )}
          </div>

          {/* Section 4: Your Prior AI Experience */}
          <div className="survey-section">
            <h2>Your Prior AI Experience</h2>
            <p className="section-note">
              These questions help us understand the range of prior experience in
              the study. There are no right or wrong answers.
            </p>

            <div className={`survey-question ${hasError("q9") ? "survey-error" : ""}`}>
              <label>
                How often do you use AI tools (such as ChatGPT, Claude, Gemini,
                or similar) for study or work?
              </label>
              <RadioGroup
                name="q9"
                value={answers.q9}
                onChange={(v) => set("q9", v)}
                options={[
                  "Never",
                  "Occasionally (a few times a month)",
                  "Regularly (a few times a week)",
                  "Daily",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q10") ? "survey-error" : ""}`}>
              <label>
                Before today, how would you describe your typical approach when
                using an AI tool for a task?
              </label>
              <RadioGroup
                name="q10"
                value={answers.q10}
                onChange={(v) => set("q10", v)}
                options={[
                  "I usually accept the first response and use it directly",
                  "I sometimes ask follow-up questions but mostly accept responses",
                  "I regularly ask follow-up questions and push back on responses",
                  "I treat AI as a thinking partner - I always challenge and refine its responses",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q11") ? "survey-error" : ""}`}>
              <label>
                Have you received any formal instruction on how to use AI tools
                effectively (for example, in a class, workshop, or training
                session)?
              </label>
              <RadioGroup
                name="q11"
                value={answers.q11}
                onChange={(v) => set("q11", v)}
                options={["Yes", "No", "Not sure"]}
              />
            </div>
          </div>

          {/* Section 5: About You */}
          <div className="survey-section">
            <h2>About You</h2>
            <p className="section-note">
              These questions are used only for statistical purposes to describe
              the study sample. Responses cannot be linked to your identity.
            </p>

            <div className={`survey-question ${hasError("q12") ? "survey-error" : ""}`}>
              <label>What is your current year of study?</label>
              <RadioGroup
                name="q12"
                value={answers.q12}
                onChange={(v) => set("q12", v)}
                options={[
                  "First year",
                  "Second year",
                  "Third year",
                  "Fourth year or above",
                  "Postgraduate coursework",
                  "Postgraduate research",
                ]}
              />
            </div>

            <div className={`survey-question ${hasError("q13") ? "survey-error" : ""}`}>
              <label>
                What is your primary discipline or field of study?
              </label>
              <select
                value={answers.q13 || ""}
                onChange={(e) => set("q13", e.target.value)}
                className="survey-select"
              >
                <option value="">Select your discipline...</option>
                {DISCIPLINE_OPTIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div className="survey-question">
              <label>
                Is there anything else you would like to tell us about your
                experience today?
              </label>
              <textarea
                value={answers.q14 || ""}
                onChange={(e) => set("q14", e.target.value)}
                rows={4}
                placeholder="Optional"
              />
            </div>
          </div>

          {errors.length > 0 && (
            <div className="survey-validation-message">
              Please answer all required questions before submitting.
            </div>
          )}

          {submitError && (
            <div className="survey-submit-error">{submitError}</div>
          )}

          <button
            type="submit"
            className="survey-submit"
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "Submit Survey"}
          </button>
        </form>
      </div>
    </div>
  );
}
