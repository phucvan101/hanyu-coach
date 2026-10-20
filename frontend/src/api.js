async function req(method, url, body, isForm = false) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    if (isForm) opts.body = body
    else {
      opts.headers['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    }
  }
  const r = await fetch(url, opts)
  let data = null
  const ct = r.headers.get('content-type') || ''
  if (ct.includes('application/json')) data = await r.json()
  if (!r.ok) {
    const msg = (data && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) || `Lỗi ${r.status}`
    throw new Error(msg)
  }
  return data
}

export const api = {
  get: (u) => req('GET', u),
  post: (u, b = {}) => req('POST', u, b),
  put: (u, b) => req('PUT', u, b),
  patch: (u, b) => req('PATCH', u, b),
  del: (u) => req('DELETE', u),
  upload: (u, form) => req('POST', u, form, true),
}

export function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function fmtDay(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}
