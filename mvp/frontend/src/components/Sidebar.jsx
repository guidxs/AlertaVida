import { Activity, BarChart3, Database, Film, MapPin, ShieldAlert, Table2 } from 'lucide-react'

const links = [
  [Activity, 'Painel geral', 'overview'],
  [MapPin, 'Mapa de ocorrências', 'map'],
  [Table2, 'Registro de alertas', 'incidents'],
  [BarChart3, 'Estatísticas', 'metrics'],
  [Film, 'Galeria de Detecções', 'gallery'],
]

export default function Sidebar({ connection, selected, onSelect, alertCount = 0 }) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark"><ShieldAlert size={21} strokeWidth={1.8} /></span><span>Alerta<span className="brand-accent">Vida</span></span></div>
    <div className="brand-caption">SISTEMA DE MONITORAMENTO</div>
    <div className="nav-label">NAVEGAÇÃO PRINCIPAL</div>
    <nav>{links.map(([Icon, label, key]) => <button key={key} className={`nav-item ${selected === key ? 'active' : ''}`} onClick={() => onSelect(key)}><Icon size={17} /><span>{label}</span>{key === 'incidents' && <span className="nav-count">{String(alertCount).padStart(2, '0')}</span>}</button>)}</nav>
    <div className="sidebar-bottom">
      <div className="nav-label">ESTADO DO SISTEMA</div>
      <div className="connection-card"><span className={`connection-dot ${connection === 'connected' ? 'online' : connection === 'loading' ? 'loading' : ''}`} /><div><strong>Databricks</strong><small>{connection === 'connected' ? 'Warehouse conectado' : connection === 'loading' ? 'Verificando conexão' : 'Sem conexão'}</small></div><Database size={15} className="connection-icon" /></div>
      <div className="source-note">Fonte oficial<br /><span>workspace.alertavida · Gold</span></div>
      <div className="sidebar-foot"><span className="foot-mark">AV</span><div><strong>AlertaVida</strong><small>Plataforma demonstrativa</small></div></div>
    </div>
  </aside>
}
