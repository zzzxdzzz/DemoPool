import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../lib/api'
import { getToken } from '../lib/auth'

type Location = { id:number; title:string; kind:string; lat:number; lon:number; address?:string; description?:string }
type Props = {
  locations: Location[]
  onBboxChange: (bbox: string)=>void
  onPick: (loc: Location)=>void
  onCreate: (loc: Location)=>void
}

export function MapView({locations, onBboxChange, onPick, onCreate}: Props){
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)

  useEffect(()=>{
    if (!mapRef.current){
      const map = L.map('map', { center: [38.99,-77.1], zoom: 10 })
      mapRef.current = map
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map)
      markersRef.current = L.layerGroup().addTo(map)

      map.on('moveend', () => {
        const b = map.getBounds()
        const bbox = `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`
        onBboxChange(bbox)
      })

      map.on('click', async (e: any)=>{
        if (!confirm('Create a location here?')) return
        const title = prompt('Title (e.g., Earth Treks Rockville)') || 'Untitled spot'
        const kind = prompt('Type (restaurant, climbing_gym, ski_resort, city, running_route, hiking_route)') || 'city'
        try {
          const token = getToken()
          const loc = await api<Location>('/locations', {
            method: 'POST',
            body: JSON.stringify({ title, kind, lat: e.latlng.lat, lon: e.latlng.lng })
          }, token)
          onCreate(loc)
        } catch(err){ alert('Login first (right sidebar).') }
      })
    }
  }, [])

  useEffect(()=>{
    if (!mapRef.current || !markersRef.current) return
    markersRef.current.clearLayers()
    locations.forEach((loc)=>{
      const m = L.marker([loc.lat, loc.lon]).addTo(markersRef.current!)
      m.bindTooltip(`${loc.title} • ${loc.kind}`)
      m.on('click', ()=> onPick(loc))
    })
  }, [locations])

  return <div id="map" className="leaflet-container" />
}
