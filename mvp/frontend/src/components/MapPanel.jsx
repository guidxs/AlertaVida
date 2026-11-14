import { useEffect, useMemo, useState } from 'react'
import { divIcon } from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { ArrowLeft, Crosshair, MapPin } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

const colors = ['#44c3ff', '#f7b84b', '#f27878', '#a78bfa']
const colorFor = (type = '') => colors[[...type].reduce((n, c) => n + c.charCodeAt(0), 0) % colors.length]

function toCoordinate(value, min, max) {
  if (value === null || value === undefined || (typeof value === 'string' && !value.trim())) return null
  const number = Number(value)
  return Number.isFinite(number) && number >= min && number <= max ? number : null
}

function FitMarkers({ groups }) {
  const map = useMap()
  useEffect(() => {
    if (groups.length) {
      map.fitBounds(groups.map(group => [group.latitude, group.longitude]), { padding: [42, 42], maxZoom: 13 })
    }
  }, [groups, map])
  return null
}

function eventDate(value) {
  if (!value) return 'Data não informada'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

function confidenceLabel(value) {
  if (value === null || value === undefined || value === '') return 'Não informada'
  const number = Number(value)
  if (!Number.isFinite(number)) return 'Não informada'
  return `${(number <= 1 ? number * 100 : number).toFixed(0)}%`
}

function cameraFor(alert) {
  const aliases = new Set([
    'camera', 'cameraid', 'idcamera', 'identificacaocamera', 'identificadorcamera',
    'cameraidentificacao', 'cameranome', 'nomecamera', 'sourcecamera',
    'origemcamera', 'codigocamera', 'cameracode',
  ])
  const normalized = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '')
  const entry = Object.entries(alert).find(([key, value]) =>
    aliases.has(normalized(key)) && value !== null && value !== undefined && String(value).trim() !== '',
  )
  return entry ? String(entry[1]) : null
}

function AlertDetails({ alert, onBack }) {
  const camera = cameraFor(alert)
  return <div className="alert-detail">
    <button className="alert-back" onClick={onBack}><ArrowLeft size={13} /> Voltar aos alertas deste local</button>
    <div className="alert-detail-title">Detalhes do evento</div>
    <dl>
      <div><dt>ID do evento</dt><dd>{alert.evento_id || '—'}</dd></div>
      <div><dt>Tipo de ocorrência</dt><dd>{alert.tipo_ocorrencia || 'Não informado'}</dd></div>
      <div><dt>Data e horário</dt><dd>{eventDate(alert.data_evento)}</dd></div>
      <div><dt>Confiança</dt><dd>{confidenceLabel(alert.confianca)}</dd></div>
      <div><dt>Status</dt><dd>{alert.status || 'Não informado'}</dd></div>
      {camera && <div><dt>Câmera</dt><dd>{camera}</dd></div>}
    </dl>
    {(alert.simulado === true || alert.simulado === 1 || String(alert.simulado).toLowerCase() === 'true') &&
      <span className="alert-simulation-note">Registro simulado</span>}
  </div>
}

function AlertGroupPopup({ alerts }) {
  const [selected, setSelected] = useState(null)
  if (selected) return <AlertDetails alert={selected} onBack={() => setSelected(null)} />

  return <div className="alert-group-content">
    <div className="alert-group-heading">
      <strong>{alerts.length} alertas neste local</strong>
      <span>Selecione um evento para ver os detalhes</span>
    </div>
    <div className="alert-group-list">
      {alerts.map((alert, index) => {
        const camera = cameraFor(alert)
        return <button className="alert-group-item" key={`${alert.evento_id}-${alert.data_evento || index}`} onClick={() => setSelected(alert)}>
          <span className="alert-item-marker" style={{ background: colorFor(alert.tipo_ocorrencia) }} />
          <span className="alert-item-main">
            <strong>{alert.evento_id || `Evento ${index + 1}`}</strong>
            <span>{alert.tipo_ocorrencia || 'Ocorrência sem tipo'}</span>
            <small>{eventDate(alert.data_evento)}{camera ? ` · Câmera ${camera}` : ''}</small>
          </span>
          <span className="alert-item-status">{alert.status || '—'}</span>
        </button>
      })}
    </div>
  </div>
}

function markerIcon(count) {
  const html = count > 1
    ? `<span class="alert-marker alert-marker--group"><span>${count}</span></span>`
    : '<span class="alert-marker alert-marker--single"><span></span></span>'
  const size = count > 1 ? 38 : 25
  return divIcon({
    className: 'alert-marker-container',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  })
}

export default function MapPanel({ alerts }) {
  const groups = useMemo(() => {
    const byLocation = new Map()
    for (const alert of alerts) {
      const latitude = toCoordinate(alert.latitude, -90, 90)
      const longitude = toCoordinate(alert.longitude, -180, 180)
      if (latitude === null || longitude === null) continue
      const key = `${latitude},${longitude}`
      if (!byLocation.has(key)) byLocation.set(key, { latitude, longitude, alerts: [] })
      byLocation.get(key).alerts.push(alert)
    }
    return [...byLocation.values()]
  }, [alerts])
  const alertCount = groups.reduce((sum, group) => sum + group.alerts.length, 0)

  return <section className="panel map-panel" id="map">
    <div className="panel-heading">
      <div><div className="eyebrow">QUADRO SITUACIONAL</div><h2>Mapa de ocorrências</h2></div>
      <span className="panel-meta"><MapPin size={14} /> {groups.length} locais · {alertCount} alertas</span>
    </div>
    {groups.length ? <div className="map-wrap">
      <MapContainer center={[groups[0].latitude, groups[0].longitude]} zoom={12} scrollWheelZoom className="leaflet-map">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} />
        <FitMarkers groups={groups} />
        {groups.map(group => <Marker
          key={`${group.latitude},${group.longitude}`}
          position={[group.latitude, group.longitude]}
          icon={markerIcon(group.alerts.length)}
          title={`${group.alerts.length} alertas nesta localização`}
        >
          <Popup className="alert-group-popup" minWidth={280} maxWidth={340}>
            <AlertGroupPopup alerts={group.alerts} />
          </Popup>
        </Marker>)}
      </MapContainer>
      <div className="map-scale"><Crosshair size={13} /> <span>OpenStreetMap · visualização escura</span></div>
    </div> : <div className="map-empty"><MapPin size={20} /><span>Sem coordenadas válidas para exibir</span></div>}
    <div className="map-legend">
      <span className="legend-label">LEGENDA</span>
      <span className="legend-item"><i className="legend-single-dot" />Localização com 1 alerta</span>
      <span className="legend-item"><i className="legend-group-dot">2+</i>Localização com alertas agrupados</span>
    </div>
  </section>
}
