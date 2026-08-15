import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import DashboardPage from './pages/DashboardPage'
import MeetingDetailPage from './pages/MeetingDetailPage'
import DictaphonePage from './pages/DictaphonePage'
import VideoModePage from './pages/VideoModePage'
import OfflineBanner from './components/ui/OfflineBanner'

function ConsentRoute() {
  const navigate = useNavigate()
  return <ConsentPage onConsent={() => navigate('/dictaphone')} />
}

function App() {
  return (
    <>
      <OfflineBanner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/consent" element={<ConsentRoute />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/meetings/:meetingId" element={<MeetingDetailPage />} />
          <Route path="/dictaphone" element={<DictaphonePage />} />
          <Route path="/video" element={<VideoModePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </>
  )
}

export default App