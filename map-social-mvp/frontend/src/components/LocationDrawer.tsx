import React, { useEffect, useState } from 'react'
import { api, uploadImage } from '../lib/api'
import { getToken, getUser } from '../lib/auth'
import { PostFeed } from './PostFeed'
import { SessionPanel } from './SessionPanel'

type Location = { id:number; title:string; kind:string; lat:number; lon:number; address?:string; description?:string }

export function LocationDrawer({ location, onClose }:{ location: Location, onClose: ()=>void }){
  const [posts, setPosts] = useState<any[]>([])
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')
  const [file, setFile] = useState<File | null>(null)

  useEffect(()=>{
    api<any[]>(`/posts?location_id=${location.id}`).then(setPosts).catch(console.error)
  }, [location.id])

  async function submitPost(){
    const token = getToken()
    let photo_url: string | undefined = undefined
    if (file){
      const up = await uploadImage(file, token)
      photo_url = up.url
    }
    const body = { location_id: location.id, content, photo_url, tags }
    const p = await api<any>('/posts', { method:'POST', body: JSON.stringify(body) }, token)
    setPosts([p, ...posts])
    setContent(''); setFile(null); setTags('')
  }

  return (
    <div>
      <div className="flex" style={{justifyContent:'space-between'}}>
        <div>
          <h3 style={{margin:'8px 0'}}>{location.title}</h3>
          <div className="small">{location.kind} • {location.address || ''}</div>
        </div>
        <button className="btn" onClick={onClose}>Close</button>
      </div>

      <div className="card">
        <div className="label">Write a post</div>
        <textarea rows={3} className="input" placeholder="Looking for partners..." value={content} onChange={e=>setContent(e.target.value)} />
        <div className="label">Tags (comma separated)</div>
        <input className="input" value={tags} onChange={e=>setTags(e.target.value)} placeholder="bouldering, partner" />
        <div className="flex" style={{marginTop:8}}>
          <input type="file" onChange={e=>setFile(e.target.files?.[0] || null)} />
          <button className="btn primary" onClick={submitPost}>Post</button>
        </div>
      </div>

      <SessionPanel locationId={location.id} />

      <PostFeed items={posts} />
    </div>
  )
}
