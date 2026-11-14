import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Clock3, Database, ShieldCheck, XCircle } from 'lucide-react'
import { api } from './services/api'
import Sidebar from './components/Sidebar'
import MapPanel from './components/MapPanel'
import IncidentsTable from './components/IncidentsTable'
import GallerySection from './components/GallerySection'
import { ConfidenceChart, StatusChart, TypeChart } from './components/Charts'

const initialMetrics = { total: 0, pendentes: 0, confirmados: 0, descartados: 0, confianca_media: null }
function Metric({ icon: Icon, label, value, hint, tone }) { return <div className={`metric metric-${tone}`}><div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={16} /></span></div><div className="metric-value">{value}</div><div className="metric-hint">{hint}</div></div> }
const timestamp = value => value ? new Date(value).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'

export default function App() {
  const [alerts, setAlerts] = useState([])
  const [metrics, setMetrics] = useState(initialMetrics)
  const [stats, setStats] = useState(null)
  const [connection, setConnection] = useState('loading')
  const [updatedAt, setUpdatedAt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState('overview')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [events, indicators, statistics, health] = await Promise.all([api.alertas(), api.indicadores(), api.estatisticas(), api.health()])
      setAlerts(events); setMetrics(indicators); setStats(statistics); setConnection(health.status); setUpdatedAt(new Date())
    } catch (e) { setConnection('disconnected'); setError(e.message || 'Falha ao consultar a API AlertaVida.') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const navigate = key => { setSelected(key); document.getElementById(key === 'overview' ? 'overview' : key)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
  const confidence = metrics.confianca_media == null ? '—' : `${(Number(metrics.confianca_media) <= 1 ? Number(metrics.confianca_media) * 100 : Number(metrics.confianca_media)).toFixed(1)}%`
  const simulated = alerts.filter(a => a.simulado === true || a.simulado === 1 || String(a.simulado).toLowerCase() === 'true').length

  return <div className="app-shell"><Sidebar connection={connection} selected={selected} onSelect={navigate} alertCount={metrics.total} /><main className="main-content" id="overview"><header className="topbar"><div><div className="breadcrumb">MONITORAMENTO <span>/</span> PAINEL GERAL</div><div className="page-heading"><div><h1>Central de operações</h1><p>Acompanhamento e triagem de possíveis ocorrências de trânsito</p></div></div></div><div className="top-actions"><div className="live-status"><span className={`connection-dot ${connection === 'connected' ? 'online' : connection === 'loading' ? 'loading' : ''}`} /><div><strong>{connection === 'connected' ? 'Sistema operacional' : connection === 'loading' ? 'Conectando' : 'Conexão indisponível'}</strong><small>Databricks SQL Warehouse</small></div></div><div className="update-time"><Clock3 size={14} /><span>Atualizado {timestamp(updatedAt)}</span></div></div></header>
      {error && <div className="error-banner"><AlertTriangle size={16} /><div><strong>Não foi possível carregar os dados</strong><span>{error} Verifique se a API está em execução.</span></div><button onClick={() => load()}>Tentar novamente</button></div>}
      <section className="demo-banner"><span className="demo-icon"><ShieldCheck size={16} /></span><div><strong>Ambiente demonstrativo</strong><span>Os {simulated} registros simulados identificados não representam acidentes reais. Este sistema não possui vínculo com órgãos públicos ou forças policiais e não aciona serviços de emergência.</span></div><span className="demo-tag">SEM VALOR OPERACIONAL</span></section>
      <section className="metrics-section"><div className="section-heading"><div><span className="eyebrow">RESUMO OPERACIONAL</span><h2>Indicadores em tempo real</h2></div><span className="data-scope"><Activity size={13} /> {metrics.total} eventos na camada Gold</span></div><div className="metrics-grid"><Metric icon={Database} label="Total de alertas" value={metrics.total} hint="Registros na fonte oficial" tone="blue" /><Metric icon={AlertTriangle} label="Pendentes" value={metrics.pendentes} hint="Aguardando triagem" tone="amber" /><Metric icon={CheckCircle2} label="Confirmados" value={metrics.confirmados} hint="Marcados como confirmados" tone="green" /><Metric icon={XCircle} label="Descartados" value={metrics.descartados} hint="Marcados como descartados" tone="red" /><Metric icon={Activity} label="Confiança média" value={confidence} hint="Média das detecções" tone="violet" /></div></section>
      <div className="primary-grid"><MapPanel alerts={alerts} /><TypeChart stats={stats} /></div>
      <IncidentsTable alerts={alerts} />
      <section className="analytics-section" id="metrics"><div className="section-heading"><div><span className="eyebrow">LEITURA DE DADOS</span><h2>Indicadores de detecção</h2></div><span className="data-scope">Com base nos registros carregados</span></div><div className="analytics-grid"><StatusChart stats={stats} /><ConfidenceChart alerts={alerts} /></div></section>
      <GallerySection />
      <footer className="footer"><span>ALERTAVIDA <i>·</i> SISTEMA DE APOIO À TRIAGEM</span><span><Database size={12} /> Databricks · workspace.alertavida.gold_mvp_alertas</span></footer>
    </main></div>
}
