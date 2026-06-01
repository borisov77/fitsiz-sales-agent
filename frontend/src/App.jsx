import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Leads from './pages/Leads.jsx'
import Conversations from './pages/Conversations.jsx'
import ConversationDetail from './pages/ConversationDetail.jsx'
import Documents from './pages/Documents.jsx'
import SettingsPage from './pages/Settings.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
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
