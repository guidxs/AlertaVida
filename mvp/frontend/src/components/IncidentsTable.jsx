import { Search, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'

const statusLabels = { PENDENTE: 'Pendente', CONFIRMADO: 'Confirmado', DESCARTADO: 'Descartado' }
const normalizeConfidence = value => value == null ? null : Number(value) <= 1 ? Number(value) * 100 : Number(value)
export default function IncidentsTable({ alerts }) {
  const [status, setStatus] = useState('Todos os status')
  const [type, setType] = useState('Todos os tipos')
  const [search, setSearch] = useState('')
  const types = [...new Set(alerts.map(a => a.tipo_ocorrencia).filter(Boolean))]
  const rows = useMemo(() => alerts.filter(a => (status === 'Todos os status' || a.status === status) && (type === 'Todos os tipos' || a.tipo_ocorrencia === type) && String(a.evento_id).toLowerCase().includes(search.toLowerCase())), [alerts, status, type, search])
  const dateLabel = value => { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }) }
  return <section className="panel incidents-panel" id="incidents"><div className="panel-heading"><div><div className="eyebrow">FILA DE TRIAGEM</div><h2>Registro de ocorrências</h2></div><span className="table-total">{rows.length} registros</span></div>
    <div className="table-toolbar"><label className="search-box"><Search size={15} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar identificador" /></label><label className="select-box"><SlidersHorizontal size={14} /><select value={status} onChange={e => setStatus(e.target.value)}><option>Todos os status</option>{[...new Set(alerts.map(a => a.status).filter(Boolean))].map(s => <option key={s}>{s}</option>)}</select></label><label className="select-box"><select value={type} onChange={e => setType(e.target.value)}><option>Todos os tipos</option>{types.map(t => <option key={t}>{t}</option>)}</select></label></div>
    <div className="table-scroll"><table><thead><tr><th>IDENTIFICADOR</th><th>TIPO DE OCORRÊNCIA</th><th>DATA DO EVENTO</th><th>CONFIANÇA</th><th>STATUS</th><th>ORIGEM</th></tr></thead><tbody>{rows.map(a => { const confidence = normalizeConfidence(a.confianca); return <tr key={a.evento_id}><td><span className="event-id">{a.evento_id}</span></td><td><span className="type-cell"><i style={{ background: '#44c3ff' }} />{a.tipo_ocorrencia || '—'}</span></td><td>{dateLabel(a.data_evento)}</td><td><span className="confidence-cell"><span className="confidence-track"><i style={{ width: `${Math.max(0, Math.min(100, confidence || 0))}%` }} /></span>{confidence == null ? '—' : `${confidence.toFixed(0)}%`}</span></td><td><span className={`status-pill ${(a.status || '').toLowerCase()}`}><i />{statusLabels[a.status] || a.status || 'Sem status'}</span></td><td><span className={`origin-pill ${a.simulado ? 'simulated' : ''}`}>{a.simulado ? 'Simulado' : 'Databricks'}</span></td></tr> })}</tbody></table>{!rows.length && <div className="table-empty">Nenhum registro corresponde aos filtros.</div>}</div>
  </section>
}
