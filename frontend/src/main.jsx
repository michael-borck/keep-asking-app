import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";

// /session        - random assignment (default for students)
// /session/a      - force nudge condition (facilitator override)
// /session/b      - force control condition (facilitator override)

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
        <Route path="/" element={<Navigate to="/session" replace />} />
        <Route path="*" element={<Navigate to="/session" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
