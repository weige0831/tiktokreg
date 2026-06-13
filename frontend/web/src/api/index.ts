import { ofetch, type FetchOptions } from 'ofetch'

// 从 localStorage 读取 Basic Auth 凭据（首次访问时由用户输入）
function getAuthHeader(): string {
  const stored = localStorage.getItem('basic_auth')
  if (stored) {
    return `Basic ${stored}`
  }
  // 提示用户输入
  const user = prompt('请输入管理员用户名（默认 admin）') || 'admin'
  const pass = prompt('请输入管理员密码') || ''
  const encoded = btoa(`${user}:${pass}`)
  localStorage.setItem('basic_auth', encoded)
  return `Basic ${encoded}`
}

export const apiFetch = ofetch.create({
  baseURL: '/api',
  onRequest({ options }) {
    ;(options.headers as Record<string, string>) = {
      ...(options.headers as Record<string, string>),
      Authorization: getAuthHeader(),
    }
  },
  onResponseError({ response }) {
    if (response.status === 401) {
      // 凭据失效，清除重新输入
      localStorage.removeItem('basic_auth')
      window.location.reload()
    }
  },
})

export interface Account {
  id: number
  email: string
  username: string | null
  birth_date: string | null
  session_id: string | null
  tt_target_idc: string | null
  ms_token: string | null
  user_agent: string | null
  proxy_used: string | null
  fingerprint_hash: string | null
  timezone: string | null
  locale: string | null
  status: string
  error_msg: string | null
  batch_id: string | null
  registered_at: string | null
  created_at: string | null
  last_checked_at: string | null
}

export interface AccountDetail extends Account {
  cookies_json: string | null
  important_cookies: Record<string, string> | null
  password: string
  viewport: { width: number; height: number } | null
}

export interface PaginatedAccounts {
  total: number
  page: number
  per_page: number
  items: Account[]
}

export interface Stats {
  total: number
  success: number
  failed: number
  success_rate: number
  last_24h_total: number
  last_24h_success: number
  failure_reasons: { reason: string; count: number }[]
  daily_trend: { date: string; success: number; failed: number }[]
}

export const api = {
  async getAccounts(params: {
    page?: number
    per_page?: number
    status?: string
    search?: string
  }): Promise<PaginatedAccounts> {
    return apiFetch<PaginatedAccounts>('/accounts', { query: params })
  },

  async getAccount(id: number): Promise<AccountDetail> {
    return apiFetch<AccountDetail>(`/accounts/${id}`)
  },

  async deleteAccount(id: number): Promise<void> {
    await apiFetch(`/accounts/${id}`, { method: 'DELETE' })
  },

  async markChecked(id: number): Promise<void> {
    await apiFetch(`/accounts/${id}/check`, { method: 'POST' })
  },

  async getStats(): Promise<Stats> {
    return apiFetch<Stats>('/stats')
  },

  // 导出 URL（浏览器直接下载）
  exportUrls: {
    json: (status?: string) =>
      `/api/export/accounts.json${status ? `?status=${status}` : ''}`,
    csv: (status?: string) =>
      `/api/export/accounts.csv${status ? `?status=${status}` : ''}`,
    accountCookies: (id: number) => `/api/export/accounts/${id}/cookies.txt`,
    accountInfo: (id: number) => `/api/export/accounts/${id}/info.json`,
  },

  async downloadExport(url: string, filename: string): Promise<void> {
    const r = await fetch(url, {
      headers: { Authorization: getAuthHeader() },
    })
    if (!r.ok) throw new Error(`导出失败: ${r.status}`)
    const blob = await r.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  },
}
