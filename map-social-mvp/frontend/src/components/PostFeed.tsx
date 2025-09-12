import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { getToken } from '../lib/auth'

export function PostFeed({items}:{items:any[]}){
  const [comments, setComments] = useState<Record<number, any[]>>({})
  const [text, setText] = useState<Record<number, string>>({})

  async function loadComments(postId: number){
    const cs = await api<any[]>(`/comments?post_id=${postId}`)
    setComments(prev=>({ ...prev, [postId]: cs }))
  }

  async function addComment(postId: number){
    const token = getToken()
    const c = await api<any>('/comments', { method:'POST', body: JSON.stringify({ post_id: postId, content: text[postId] || '' }) }, token)
    setComments(prev=>({ ...prev, [postId]: [ ...(prev[postId]||[]), c ] }))
    setText(prev=>({ ...prev, [postId]: '' }))
  }

  return (
    <div>
      {items.map(p => (
        <div className="card" key={p.id}>
          <div className="small">{new Date(p.created_at).toLocaleString()}</div>
          <div style={{marginTop:6}}>{p.content}</div>
          {p.tags ? <div style={{marginTop:6}}>{p.tags.split(',').map((t:string)=>(<span className="badge" key={t.trim()}>{t.trim()}</span>))}</div> : null}
          {p.photo_url ? <img className="post-photo" src={p.photo_url} alt="" /> : null}

          <div style={{marginTop:8}}>
            <button className="btn" onClick={()=>loadComments(p.id)}>Load comments</button>
          </div>
          {(comments[p.id]||[]).map(c => (
            <div key={c.id} style={{marginTop:6}} className="small">💬 {c.content} — {new Date(c.created_at).toLocaleString()}</div>
          ))}
          <div className="flex" style={{marginTop:8}}>
            <input className="input" placeholder="Write a comment" value={text[p.id]||''} onChange={e=>setText(prev=>({...prev, [p.id]: e.target.value}))} />
            <button className="btn" onClick={()=>addComment(p.id)}>Send</button>
          </div>
        </div>
      ))}
    </div>
  )
}
