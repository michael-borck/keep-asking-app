import { useState } from "react";
import Login from "./Login";
import Chat from "./Chat";
import "./App.css";

export default function App({ condition }) {
  const [session, setSession] = useState(null);

  if (!session) {
    return <Login condition={condition} onLogin={setSession} />;
  }

  return <Chat session={session} />;
}
