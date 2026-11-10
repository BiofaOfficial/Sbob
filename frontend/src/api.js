async function richiesta(metodo, url, corpo) {
  const opz = { method: metodo, headers: {} }
  if (corpo instanceof FormData) opz.body = corpo
  else if (corpo !== undefined) { opz.body = JSON.stringify(corpo); opz.headers['Content-Type'] = 'application/json' }
  const r = await fetch(url, opz)
  if (!r.ok) {
    let msg = r.statusText
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch (e) { /* testo */ }
    throw new Error(msg)
  }
  return r.json()
}
export const api = {
  get: (u) => richiesta('GET', u),
  post: (u, c) => richiesta('POST', u, c),
  put: (u, c) => richiesta('PUT', u, c),
  patch: (u, c) => richiesta('PATCH', u, c),
  del: (u) => richiesta('DELETE', u),
}

export function mmss(ms) {
  const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, x = s % 60
  const p = (n) => String(n).padStart(2, '0')
  return h ? `${h}:${p(m)}:${p(x)}` : `${p(m)}:${p(x)}`
}

export function secondiDa(ts) {
  const parti = ts.split(':').map(Number)
  return parti.reduce((acc, n) => acc * 60 + n, 0)
}

export function durataFase(f) {
  if (!f.inizio || !f.fine) return ''
  const s = Math.max(0, Math.round((new Date(f.fine) - new Date(f.inizio)) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
