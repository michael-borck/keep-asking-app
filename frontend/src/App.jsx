import { useState, useEffect } from "react";
import Login from "./Login";
import Chat from "./Chat";
import "./App.css";

export default function App({ condition }) {
  const [session, setSession] = useState(null);

  // Restore session from sessionStorage after page reload
  useEffect(() => {
    const saved = sessionStorage.getItem("keep-asking-session");
    if (saved) {
      try {
        setSession(JSON.parse(saved));
      } catch {
        sessionStorage.removeItem("keep-asking-session");
      }
    }
  }, []);

  function handleLogin(sessionData) {
    sessionStorage.setItem("keep-asking-session", JSON.stringify(sessionData));
    setSession(sessionData);
  }

  if (!session) {
    return <Login condition={condition} onLogin={handleLogin} />;
  }

  return <Chat session={session} />;
}
