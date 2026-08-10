import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import DashboardPage from './pages/DashboardPage'
import MeetingDetailPage from './pages/MeetingDetailPage'
import DictaphonePage from './pages/DictaphonePage'
import VideoModePage from './pages/VideoModePage'

// ConsentPage attend un callback, et useNavigate n'existe que sous le Router :
// d'où ce petit adaptateur plutôt qu'un élément inline dans la Route.
// Le consentement conditionne la création de réunion — on enchaîne donc sur le dictaphone.
function ConsentRoute() {
  const navigate = useNavigate()
  return <ConsentPage onConsent={() => navigate('/dictaphone')} />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/consent" element={<ConsentRoute />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/meetings/:meetingId" element={<MeetingDetailPage />} />
        <Route path="/dictaphone" element={<DictaphonePage />} />
        <Route path="/video" element={<VideoModePage />} />
        {/* URL inconnue : on renvoie à l'accueil plutôt que sur une page blanche */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
