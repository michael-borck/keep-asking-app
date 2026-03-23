import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";

// Three ways to access the session:
//
// /session        - random assignment (default for students)
// /session/a      - force nudge condition (facilitator override)
// /session/b      - force control condition (facilitator override)
//
// In most lab setups, all students go to /session and the backend
// randomly assigns. The /session/a and /session/b paths exist for
// testing or if the facilitator needs to control assignment manually.

const CONDITION_MAP = {
  a: "nudge",
  b: "control",
};

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/session" element={<App condition={null} />} />
        <Route
          path="/session/a"
          element={<App condition={CONDITION_MAP.a} />}
        />
        <Route
          path="/session/b"
          element={<App condition={CONDITION_MAP.b} />}
        />
        <Route path="/" element={<Landing />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);

function Landing() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "20px",
        textAlign: "center",
        gap: "24px",
      }}
    >
      <h1 style={{ fontSize: "24px", color: "#111827" }}>
        Lab Session Setup
      </h1>
      <p style={{ color: "#6b7280", maxWidth: "420px" }}>
        Facilitator only. Direct all students to <strong>/session</strong> for
        random assignment. Use /session/a or /session/b only if you need to
        force a specific condition.
      </p>
      <div style={{ display: "flex", gap: "12px" }}>
        <a
          href="/session"
          style={{
            padding: "12px 24px",
            background: "#2563eb",
            color: "white",
            borderRadius: "8px",
            textDecoration: "none",
            fontFamily: "monospace",
          }}
        >
          /session (random)
        </a>
        <a
          href="/session/a"
          style={{
            padding: "12px 24px",
            background: "#9ca3af",
            color: "white",
            borderRadius: "8px",
            textDecoration: "none",
            fontFamily: "monospace",
            fontSize: "14px",
          }}
        >
          /session/a
        </a>
        <a
          href="/session/b"
          style={{
            padding: "12px 24px",
            background: "#9ca3af",
            color: "white",
            borderRadius: "8px",
            textDecoration: "none",
            fontFamily: "monospace",
            fontSize: "14px",
          }}
        >
          /session/b
        </a>
      </div>
      <p style={{ color: "#9ca3af", fontSize: "13px" }}>
        A = nudge, B = control. Students should not see this page.
      </p>
    </div>
  );
}
