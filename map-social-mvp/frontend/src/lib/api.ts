export const API_BASE = '' // proxied by Vite to localhost:8000

export async function api<T>(path: string, opts: RequestInit = {}, token?: string): Promise<T> {
  const headers: any = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(API_BASE + path, { ...opts, headers })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<T>
}

export async function uploadImage(file: File, token: string): Promise<{url: string}> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/upload/image', { method: 'POST', body: fd, headers: { 'Authorization': `Bearer ${token}` }})
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
