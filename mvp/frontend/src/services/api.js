const API_URL = import.meta.env.VITE_API_URL || ''

async function request(path, options) {
  const response = await fetch(`${API_URL}${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Erro na API (${response.status})`)
  }
  return response.json()
}

export const api = {
  alertas: () => request('/api/alertas'),
  indicadores: () => request('/api/indicadores'),
  estatisticas: () => request('/api/alertas/estatisticas'),
  health: () => request('/api/health'),
  gallery: () => request('/api/gallery'),
  galleryVideoUrl: path => `${API_URL}/api/gallery/videos?${new URLSearchParams({ path })}`,
}
