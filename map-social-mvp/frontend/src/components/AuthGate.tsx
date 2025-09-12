import React, { useState } from 'react'
import { api } from '../lib/api'
import { saveToken, saveUser, getUser } from '../lib/auth'

export function AuthGate(){
  const existing = getUser()
  const [email, setEmail] = useState('alice@example.com')
  const [password, setPassword] = useState('alicepw')
  const [display_name, setDisplay] = useState('Alice')

  async function register(){
    const user = await api<any>('/auth/register', { method:'POST', body: JSON.stringify({ email, password, display_name }) })
    saveUser(user)
    const tok = await login()
    return tok
  }

  async function login(){
    const body = new URLSearchParams({ username: email, password })
    const res = await fetch('/auth/token', { method:'POST', body })
    const json = await res.json()
    saveToken(json.access_token)
    // Fetch minimal user again (simulated)
    saveUser({ email, display_name })
    location.reload()
  }

  if (existing) return null

  return (
    <div className="card">
      <strong>Sign in</strong>
      <div className="label">Email</div>
      <input className="input" value={email} onChange={e=>setEmail(e.target.value)} />
      <div className="label">Password</div>
      <input type="password" className="input" value={password} onChange={e=>setPassword(e.target.value)} />
      <div className="label">Display Name (for register)</div>
      <input className="input" value={display_name} onChange={e=>setDisplay(e.target.value)} />
      <div className="flex" style={{marginTop:8}}>
        <button className="btn" onClick={login}>Sign in</button>
        <button className="btn" onClick={register}>Register</button>
      </div>
      <div className="small" style={{marginTop:6}}>Tip: seed users also exist (alice@example.com/alicepw, bob@example.com/bobpw).</div>
    </div>
  )
}
