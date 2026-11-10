import { useEffect } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { Crosshair, MapPin } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

const colors = ['#44c3ff', '#f7b84b', '#f27878', '#a78bfa']
const colorFor = (type = '') => colors[[...type].reduce((n, c) => n + c.charCodeAt(0), 0) % colors.length]
function FitMarkers({ alerts }) {
  const map = useMap()
  useEffect(() => {
    const points = alerts.filter(a => Number.isFinite(Number(a.latitude)) && Number.isFinite(Number(a.longitude)))
    if (points.length) map.fitBounds(points.map(a => [Number(a.latitude), Number(a.longitude)]), { padding: [42, 42], maxZoom: 13 })
  }, [alerts, map])
  return null
}

export default function MapPanel({ alerts }) {
  const mapped = alerts.filter(a => Number.isFinite(Number(a.latitude)) && Number.isFinite(Number(a.longitude)))
  return <section className="panel map-panel" id="map"><div className="panel-heading"><div><div className="eyebrow">QUADRO SITUACIONAL</div><h2>Mapa de ocorrências</h2></div><span className="panel-meta"><MapPin size={14} /> {mapped.length} pontos</span></div>
    {mapped.length ? <div className="map-wrap"><MapContainer center={[Number(mapped[0].latitude), Number(mapped[0].longitude)]} zoom={12} scrollWheelZoom className="leaflet-map"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} /><FitMarkers alerts={mapped} />{mapped.map(a => <CircleMarker key={a.evento_id} center={[Number(a.latitude), Number(a.longitude)]} radius={8} pathOptions={{ color: colorFor(a.tipo_ocorrencia), fillColor: colorFor(a.tipo_ocorrencia), fillOpacity: .86, weight: 2 }}><Popup><strong>{a.tipo_ocorrencia || 'Ocorrência'}</strong><br />{a.evento_id}<br />Status: {a.status}<br />{a.simulado ? 'Registro simulado' : 'Registro do sistema'}</Popup></CircleMarker>)}</MapContainer><div className="map-scale"><Crosshair size={13} /> <span>OpenStreetMap · visualização escura</span></div></div> : <div className="map-empty"><MapPin size={20} /><span>Sem coordenadas válidas para exibir</span></div>}
    <div className="map-legend"><span className="legend-label">TIPO DE OCORRÊNCIA</span>{[...new Set(mapped.map(a => a.tipo_ocorrencia).filter(Boolean))].map(t => <span className="legend-item" key={t}><i style={{ background: colorFor(t) }} />{t}</span>)}</div>
  </section>
}
