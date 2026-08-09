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
    <div className="flex flex-col items-center justify-center min-h-screen font-sans px-6">
      <h1 className="text-4xl mb-2">Auris</h1>
      <p className="text-gray-500 mb-10 text-center">
        Assistant de réunion intelligent
      </p>
      <button
        onClick={handleLogin}
        disabled={loading}
        className="bg-[#2C5F8A] text-white border-none px-8 py-3 rounded-lg text-base min-h-[44px] w-full sm:w-auto cursor-pointer disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? "Redirection..." : "Se connecter"}
      </button>
      <p className="mt-6 text-sm text-gray-500 text-center">
        Authentification sécurisée via Keycloak
      </p>
    </div>
  );
}