export function saveToken(t: string){ localStorage.setItem('token', t) }
export function getToken(){ return localStorage.getItem('token') || '' }
export function saveUser(u: any){ localStorage.setItem('user', JSON.stringify(u)) }
export function getUser(){ try { return JSON.parse(localStorage.getItem('user')||'null') } catch { return null } }
export function signOut(){ localStorage.removeItem('token'); localStorage.removeItem('user'); location.reload() }
