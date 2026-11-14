import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const palette = ['#44c3ff', '#f7b84b', '#f27878', '#a78bfa', '#50d4a4']
const statusColor = { PENDENTE: '#f7b84b', CONFIRMADO: '#50d4a4', DESCARTADO: '#f27878' }
function ChartCard({ title, subtitle, children, className = '' }) { return <section className={`panel chart-panel ${className}`}><div className="panel-heading"><div><div className="eyebrow">ANÁLISE</div><h2>{title}</h2></div></div>{subtitle && <div className="chart-subtitle">{subtitle}</div>}{children}</section> }
const TooltipBox = ({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><strong>{label}</strong><span>{payload[0].value} evento(s)</span></div> : null

export function TypeChart({ stats }) {
  const data = Object.entries(stats?.por_tipo || {}).map(([name, value]) => ({ name, value }))
  return <ChartCard title="Alertas por tipo" subtitle="Volume por categoria de ocorrência" className="type-chart-panel"><div className="chart-area type-chart-area">{data.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }}><CartesianGrid stroke="#202b38" horizontal={false} /><XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#8090a3', fontSize: 11 }} /><YAxis type="category" dataKey="name" width={112} axisLine={false} tickLine={false} tick={{ fill: '#aab6c5', fontSize: 11 }} /><Tooltip content={<TooltipBox />} cursor={{ fill: '#ffffff08' }} /><Bar dataKey="value" radius={[0, 5, 5, 0]} barSize={13}>{data.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}</Bar></BarChart></ResponsiveContainer> : <span className="empty-note">Sem dados de categoria</span>}</div></ChartCard>
}
export function StatusChart({ stats }) {
  const data = Object.entries(stats?.por_status || {}).map(([name, value]) => ({ name, value, fill: statusColor[name.toUpperCase()] || '#44c3ff' }))
  return <ChartCard title="Distribuição por status" subtitle="Estado atual dos registros"><div className="status-chart">{data.length ? data.map(d => <div className="status-row" key={d.name}><div className="status-row-top"><span><i style={{ background: d.fill }} />{d.name}</span><strong>{d.value}</strong></div><div className="status-track"><i style={{ width: `${Math.max(10, d.value / Math.max(...data.map(x => x.value)) * 100)}%`, background: d.fill }} /></div></div>) : <span className="empty-note">Sem dados de status</span>}</div></ChartCard>
}
export function ConfidenceChart({ alerts }) {
  const data = alerts.filter(a => a.confianca != null).map(a => ({ name: a.evento_id, valor: Math.round((Number(a.confianca) <= 1 ? Number(a.confianca) * 100 : Number(a.confianca))) }))
  return <ChartCard title="Confiança das detecções" subtitle="Nível de confiança informado pela origem (%)"><div className="chart-area confidence-area">{data.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 5, right: 8, bottom: 0, left: -18 }}><CartesianGrid stroke="#202b38" vertical={false} /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#8090a3', fontSize: 10 }} /><YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#8090a3', fontSize: 10 }} /><Tooltip content={<TooltipBox />} /><Bar dataKey="valor" name="Confiança" fill="#44c3ff" radius={[4, 4, 0, 0]} barSize={28} /></BarChart></ResponsiveContainer> : <span className="empty-note">Sem valores de confiança</span>}</div></ChartCard>
}
