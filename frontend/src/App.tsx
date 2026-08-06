import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DictaphonePage from './pages/DictaphonePage'
import VideoModePage from './pages/VideoModePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dictaphone" element={<DictaphonePage />} />
        <Route path="/video" element={<VideoModePage />} />
        {/* URL inconnue : on renvoie à l'accueil plutôt que sur une page blanche */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
