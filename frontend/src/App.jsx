import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Leads from './pages/Leads.jsx'
import Conversations from './pages/Conversations.jsx'
import ConversationDetail from './pages/ConversationDetail.jsx'
import Documents from './pages/Documents.jsx'
import SettingsPage from './pages/Settings.jsx'
import Login from './pages/Login.jsx'
import { api } from './lib/api.js'

export default function App() {
  const [authState, setAuthState] = useState('loading') // loading | in | out
  const [user, setUser] = useState(null)

  useEffect(() => {
    api
      .authMe()
      .then((u) => {
        setUser(u)
        setAuthState('in')
      })
      .catch(() => setAuthState('out'))
  }, [])

  const handleLogout = async () => {
    try {
      await api.authLogout()
    } catch {
      // игнорируем — всё равно выходим
    }
    setUser(null)
    setAuthState('out')
  }

  if (authState === 'loading') {
    return (
      <div className="flex h-full items-center justify-center bg-fitsiz-black text-fitsiz-muted">
        загрузка…
      </div>
    )
  }

  if (authState === 'out') {
    return (
      <Login
        onLoggedIn={(u) => {
          setUser(u)
          setAuthState('in')
        }}
      />
    )
  }

  return (
    <Routes>
      <Route element={<Layout user={user} onLogout={handleLogout} />}>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="conversations" element={<Conversations />} />
        <Route path="conversations/:leadId" element={<ConversationDetail />} />
        <Route path="documents" element={<Documents />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
