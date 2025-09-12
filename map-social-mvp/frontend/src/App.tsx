import React, { useEffect, useMemo, useState } from 'react'
import { MapView } from './components/MapView'
import { LocationDrawer } from './components/LocationDrawer'
import { AuthGate } from './components/AuthGate'
import { api } from './lib/api'
import { getToken, getUser, signOut } from './lib/auth'

type Location = { id:number; title:string; kind:string; lat:number; lon:number; address?:string; description?:string }

export default function App() {
  const [bbox, setBbox] = useState<string>('')
  const [locations, setLocations] = useState<Location[]>([])
  const [active, setActive] = useState<Location | null>(null)
  const token = getToken()
  const me = getUser()

  useEffect(() => {
    const query = bbox ? `?bbox=${encodeURIComponent(bbox)}` : ''
    api<Location[]>(`/locations${query}`).then(setLocations).catch(console.error)
  }, [bbox])

  return (
    <div className="app">
      <div>
        <div className="header">
          <div className="flex">
            <strong>🗺️ Map Social</strong>
            <span className="small">MVP</span>
          </div>
          <div className="flex">
            {me ? (<>
              <span className="small">Hi, {me.display_name}</span>
              <button className="btn" onClick={()=>signOut()}>Sign out</button>
            </>) : null}
          </div>
        </div>
        <MapView locations={locations} onBboxChange={setBbox} onPick={setActive} onCreate={(loc)=>setActive(loc)} />
      </div>
      <div className="sidebar">
        <AuthGate />
        {active ? <LocationDrawer location={active} onClose={()=>setActive(null)} /> : (
          <div className="small">Select a marker to view posts & sessions. Pan the map to load locations.</div>
        )}
      </div>
    </div>
  )
}
