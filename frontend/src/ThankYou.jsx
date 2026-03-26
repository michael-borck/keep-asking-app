import { useEffect } from "react";

export default function ThankYou() {
  useEffect(() => {
    sessionStorage.removeItem("keep-asking-session");
  }, []);

  return (
    <div className="thankyou-container">
      <div className="thankyou-card">
        <h1>Thank You</h1>
        <p>Your responses have been recorded.</p>
        <p>You may now close this window.</p>
      </div>
    </div>
  );
}
