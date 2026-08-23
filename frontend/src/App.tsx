import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import DashboardPage from './pages/DashboardPage'
import MeetingDetailPage from './pages/MeetingDetailPage'
import DictaphonePage from './pages/DictaphonePage'
import VideoModePage from './pages/VideoModePage'
import AdminStatusPage from './pages/AdminStatusPage'
import OfflineBanner from './components/ui/OfflineBanner'

const KEYCLOAK_URL       = import.meta.env.VITE_KEYCLOAK_URL    || "http://localhost:8080";
const KEYCLOAK_REALM     = import.meta.env.VITE_KEYCLOAK_REALM  || "auris";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "auris-frontend";

function ConsentRoute() {
  const navigate = useNavigate()
  return <ConsentPage onConsent={() => navigate('/dictaphone')} />
}

function AppRoutes() {
  const [token, setToken]     = useState<string | null>(localStorage.getItem("access_token"));
  const [loading, setLoading] = useState(false);
  const navigate              = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code   = params.get("code");

    if (!code) return;

    // Nettoie l'URL
    window.history.replaceState({}, document.title, "/");

    setLoading(true);

    fetch(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type:    "authorization_code",
        client_id:     KEYCLOAK_CLIENT_ID,
        redirect_uri:  window.location.origin,
        code,
      }),
    })
      .then(res => res.json())
      .then(data => {
          if (data.access_token) {
            localStorage.setItem("access_token", data.access_token);
            setToken(data.access_token);

            // Crée l'utilisateur en base si première connexion
            fetch("/api/v1/auth/register", {
              method: "POST",
              headers: { "Authorization": `Bearer ${data.access_token}` }
            }).then(() => navigate("/dashboard"));
          }
        })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!token) return;
    fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` }
    }).catch(console.error);
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-500">
        Connexion en cours...
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/"                    element={token ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/consent"             element={token ? <ConsentRoute /> : <Navigate to="/" replace />} />
      <Route path="/dashboard"           element={token ? <DashboardPage /> : <Navigate to="/" replace />} />
      <Route path="/meetings/:meetingId" element={token ? <MeetingDetailPage /> : <Navigate to="/" replace />} />
      <Route path="/dictaphone"          element={token ? <DictaphonePage /> : <Navigate to="/" replace />} />
      <Route path="/video"               element={token ? <VideoModePage /> : <Navigate to="/" replace />} />
      <Route path="/admin/status"        element={token ? <AdminStatusPage /> : <Navigate to="/" replace />} />
      <Route path="*"                    element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <>
      <OfflineBanner />
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </>
  )
}

export default App