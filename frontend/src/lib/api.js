// Клиент к FastAPI-бэкенду. В dev всё идёт через Vite-proxy на 127.0.0.1:8000.
const BASE = ''

async function request(path, { method = 'GET', body, isFormData = false, query } = {}) {
  let url = `${BASE}${path}`
  if (query) {
    const qs = new URLSearchParams(
      Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString()
    if (qs) url += `?${qs}`
  }
  const headers = {}
  if (!isFormData && body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, {
    method,
    headers,
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const message = data?.detail || `${res.status} ${res.statusText}`
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return data
}

export const api = {
  // --- system / health
  health: () => request('/api/health'),

  // --- leads
  leadsList: (params) => request('/api/leads', { query: params }),
  leadCreate: (payload) => request('/api/leads', { method: 'POST', body: payload }),
  leadGet: (id) => request(`/api/leads/${id}`),
  leadUpdate: (id, payload) => request(`/api/leads/${id}`, { method: 'PATCH', body: payload }),
  leadDelete: (id) => request(`/api/leads/${id}`, { method: 'DELETE' }),
  leadTransfer: (id, manager = 'manager') =>
    request(`/api/leads/${id}/transfer`, { method: 'POST', query: { manager } }),
  leadsImport: (file, campaignId) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/api/leads/import', {
      method: 'POST',
      body: fd,
      isFormData: true,
      query: campaignId ? { campaign_id: campaignId } : undefined,
    })
  },

  // --- conversations
  conversationsList: (params) => request('/api/conversations', { query: params }),
  conversationGet: (leadId) => request(`/api/conversations/${leadId}`),
  draftCold: (leadId) =>
    request(`/api/conversations/${leadId}/draft-cold`, { method: 'POST' }),
  draftReply: (leadId, incomingMessageId) =>
    request(`/api/conversations/${leadId}/draft-reply`, {
      method: 'POST',
      query: incomingMessageId ? { incoming_message_id: incomingMessageId } : undefined,
    }),
  draftFollowUp: (leadId, stage = 'follow_up_1') =>
    request(`/api/conversations/${leadId}/draft-followup`, {
      method: 'POST',
      query: { stage },
    }),
  qualify: (leadId) =>
    request(`/api/conversations/${leadId}/qualify`, { method: 'POST' }),
  messageEdit: (id, payload) =>
    request(`/api/conversations/messages/${id}`, { method: 'PATCH', body: payload }),
  messageDelete: (id) =>
    request(`/api/conversations/messages/${id}`, { method: 'DELETE' }),
  messageApprove: (id) =>
    request(`/api/conversations/messages/${id}/approve`, { method: 'POST' }),
  messageSend: (id) =>
    request(`/api/conversations/messages/${id}/send`, { method: 'POST' }),
  conversationTransfer: (leadId, manager = 'manager') =>
    request(`/api/conversations/${leadId}/transfer`, {
      method: 'POST',
      body: { manager },
    }),

  // --- email
  emailQuota: () => request('/api/email/quota'),
  emailCheckInbox: () => request('/api/email/check-inbox', { method: 'POST' }),
  emailSendTest: (payload) =>
    request('/api/email/send-test', { method: 'POST', body: payload }),
  emailTestManager: () =>
    request('/api/email/test-manager-email', { method: 'POST' }),
  emailSetLimit: (dailyLimit) =>
    request('/api/email/limits', {
      method: 'PATCH',
      body: { daily_limit: dailyLimit },
    }),
  emailResetLimit: () =>
    request('/api/email/limits/reset', { method: 'POST' }),
}
