import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { getToken } from '../lib/auth'

export function SessionPanel({locationId}:{locationId:number}){
  const [items, setItems] = useState<any[]>([])
  const [title, setTitle] = useState('')
  const [activity, setActivity] = useState('bouldering')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [maxp, setMaxp] = useState<number | ''>('')
  const [notes, setNotes] = useState('')

  async function load(){ setItems(await api<any[]>(`/sessions?location_id=${locationId}`)) }
  useEffect(()=>{ load() }, [locationId])

  async function add(){
    const token = getToken()
    const body: any = { location_id: locationId, title, activity, starts_at: start, ends_at: end, notes }
    if (maxp !== '') body.max_people = Number(maxp)
    const s = await api<any>('/sessions', { method:'POST', body: JSON.stringify(body) }, token)
    setItems([ ...items, s ])
    setTitle(''); setNotes('')
  }

  return (
    <div className="card">
      <div className="label">Create a session</div>
      <input className="input" placeholder="Saturday Jam" value={title} onChange={e=>setTitle(e.target.value)} />
      <div className="flex">
        <input className="input" type="datetime-local" value={start} onChange={e=>setStart(e.target.value)} />
        <input className="input" type="datetime-local" value={end} onChange={e=>setEnd(e.target.value)} />
      </div>
      <div className="flex">
        <input className="input" placeholder="activity" value={activity} onChange={e=>setActivity(e.target.value)} />
        <input className="input" placeholder="max people" value={maxp} onChange={e=>setMaxp(e.target.value as any)} />
      </div>
      <textarea className="input" rows={2} placeholder="notes" value={notes} onChange={e=>setNotes(e.target.value)} />
      <div style={{marginTop:6}}>
        <button className="btn primary" onClick={add}>Create</button>
      </div>

      <div style={{marginTop:10}}>
        <strong>Upcoming sessions</strong>
        {items.map(it => (
          <div className="small" key={it.id} style={{marginTop:6}}>
            📅 {it.title} — {it.activity} — {new Date(it.starts_at).toLocaleString()} → {new Date(it.ends_at).toLocaleString()} {it.max_people?`• max ${it.max_people}`:''}
            <div>{it.notes}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
