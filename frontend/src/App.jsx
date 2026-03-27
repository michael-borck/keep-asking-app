import { useState, useEffect } from "react";
import Login from "./Login";
import Chat from "./Chat";
import Survey from "./Survey";
import ThankYou from "./ThankYou";
import NoSession from "./NoSession";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "";

// App states: checking | no-session | login | chat | survey | thankyou
export default function App({ condition }) {
  const [appState, setAppState] = useState("checking");
  const [session, setSession] = useState(null);

  // On mount: restore session or check lab status
  useEffect(() => {
    const saved = sessionStorage.getItem("keep-asking-session");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSession(parsed);
        // If already finished survey, go to thank-you
        if (parsed.surveyCompleted) {
          setAppState("thankyou");
        } else if (parsed.chatLocked) {
          // Chat was locked but survey not done yet
          setAppState(parsed.consented ? "survey" : "thankyou");
        } else {
          setAppState("chat");
        }
        return;
      } catch {
        sessionStorage.removeItem("keep-asking-session");
      }
    }

    // No saved session — check if a lab session is active
    checkLabSession();
  }, []);

  async function checkLabSession() {
    try {
      const params = new URLSearchParams(window.location.search);
      const query = new URLSearchParams();
      if (params.get("lab")) query.set("lab", params.get("lab"));
      if (params.get("token")) query.set("token", params.get("token"));
      const qs = query.toString();
      const url = `${API_URL}/api/session-status${qs ? `?${qs}` : ""}`;
      const res = await fetch(url);
      const data = await res.json();
      setAppState(data.active ? "login" : "no-session");
    } catch {
      // If session-status fails, allow login anyway (graceful degradation)
      setAppState("login");
    }
  }

  function handleLogin(sessionData) {
    sessionStorage.setItem("keep-asking-session", JSON.stringify(sessionData));
    setSession(sessionData);
    setAppState("chat");
  }

  function handleFinish() {
    const updated = { ...session, chatLocked: true };
    sessionStorage.setItem("keep-asking-session", JSON.stringify(updated));
    setSession(updated);
    if (session.consented) {
      setAppState("survey");
    } else {
      setAppState("thankyou");
    }
  }

  function handleSurveyComplete() {
    const updated = { ...session, surveyCompleted: true };
    sessionStorage.setItem("keep-asking-session", JSON.stringify(updated));
    setSession(updated);
    setAppState("thankyou");
  }

  function handleSessionState({ chatLocked, surveyCompleted }) {
    // Called by Chat when restoring history reveals the session was already locked
    if (surveyCompleted) {
      const updated = { ...session, chatLocked: true, surveyCompleted: true };
      sessionStorage.setItem("keep-asking-session", JSON.stringify(updated));
      setSession(updated);
      setAppState("thankyou");
    } else if (chatLocked) {
      const updated = { ...session, chatLocked: true };
      sessionStorage.setItem("keep-asking-session", JSON.stringify(updated));
      setSession(updated);
      setAppState(session.consented ? "survey" : "thankyou");
    }
  }

  switch (appState) {
    case "checking":
      return (
        <div className="loading-container">
          <p>Loading...</p>
        </div>
      );
    case "no-session":
      return <NoSession />;
    case "login":
      return <Login condition={condition} onLogin={handleLogin} />;
    case "chat":
      return (
        <Chat
          session={session}
          onFinish={handleFinish}
          onSessionState={handleSessionState}
        />
      );
    case "survey":
      return (
        <Survey session={session} onComplete={handleSurveyComplete} />
      );
    case "thankyou":
      return <ThankYou />;
    default:
      return null;
  }
}
