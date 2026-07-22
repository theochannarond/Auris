import { useState } from "react";

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080";
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "auris";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "auris-frontend";
const REDIRECT_URI = window.location.origin;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);

  const handleLogin = () => {
    setLoading(true);
    const authUrl =
      `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth` +
      `?client_id=${KEYCLOAK_CLIENT_ID}` +
      `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
      `&response_type=code` +
      `&scope=openid profile email`;
    window.location.href = authUrl;
  };

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      fontFamily: "Arial, sans-serif"
    }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "8px" }}>Auris</h1>
      <p style={{ color: "#6B7280", marginBottom: "40px" }}>
        Assistant de réunion intelligent
      </p>
      <button
        onClick={handleLogin}
        disabled={loading}
        style={{
          backgroundColor: "#2C5F8A",
          color: "white",
          border: "none",
          padding: "12px 32px",
          borderRadius: "8px",
          fontSize: "1rem",
          cursor: loading ? "not-allowed" : "pointer",
          opacity: loading ? 0.7 : 1
        }}
      >
        {loading ? "Redirection..." : "Se connecter"}
      </button>
      <p style={{ marginTop: "24px", fontSize: "0.8rem", color: "#6B7280" }}>
        Authentification sécurisée via Keycloak
      </p>
    </div>
  );
}