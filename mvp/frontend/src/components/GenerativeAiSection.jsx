import { useState } from 'react'
import { AlertTriangle, BrainCircuit, CheckCircle2 } from 'lucide-react'

const apiUrl = import.meta.env.VITE_GENAI_URL || '/genai'
const examples = {
  trapped: { event_type: 'possivel_colisao', confidence: '0.87', observacao: 'operador relata pessoa presa nas ferragens' },
  motorcycle: { event_type: 'queda_motociclista', confidence: '0.91', observacao: 'pessoa caída ao lado de uma motocicleta; vítima não identificada' },
  unknown: { event_type: 'possivel_colisao', confidence: '0.74', observacao: 'alerta da câmera sem confirmação visual de vítimas' },
  custom: { event_type: '', confidence: '0.50', observacao: '' },
}

const initialForm = { camera_id: 'CAM-01', timestamp: '2026-11-10T14:32', ...examples.trapped, pergunta: 'Classifique a ocorrência e indique o próximo passo do operador.' }

export default function GenerativeAiSection() {
  const [form, setForm] = useState(initialForm)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showJson, setShowJson] = useState(false)

  const update = event => setForm(current => ({ ...current, [event.target.name]: event.target.value }))
  const selectExample = event => setForm(current => ({ ...current, ...examples[event.target.value] }))

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiUrl}/triage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evento: { camera_id: form.camera_id, timestamp: form.timestamp, event_type: form.event_type, confidence: Number(form.confidence), observacao: form.observacao }, pergunta: form.pergunta }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'Falha ao consultar a triagem.')
      setResult(body)
      setShowJson(false)
    } catch (reason) {
      setError(`Não foi possível concluir a triagem: ${reason.message}`)
    } finally {
      setLoading(false)
    }
  }

  const triagem = result?.triagem

  return <section className="generative-ai-section" id="generative-ai">
    <div className="section-heading generative-ai-heading">
      <div>
        <span className="eyebrow">APOIO À DECISÃO</span>
        <h2>Central de triagem com IA</h2>
        <p>Consulte uma sugestão fundamentada para o evento detectado antes de registrar o desfecho.</p>
      </div>
      <span className="generative-ai-status"><span /> IA disponível</span>
    </div>
    <div className="generative-ai-panel">
      <form className="generative-ai-form" onSubmit={submit}>
        <div className="generative-ai-panel-head"><span className="generative-ai-step">01</span><div><h3>Novo alerta</h3><span>Dados do evento e observações do operador</span></div></div>
        <label>Cenário de exemplo
          <select onChange={selectExample} defaultValue="trapped">
            <option value="trapped">Pessoa presa nas ferragens</option>
            <option value="motorcycle">Queda de motociclista</option>
            <option value="unknown">Alerta sem confirmação de vítima</option>
            <option value="custom">Preencher manualmente</option>
          </select>
        </label>
        <div className="generative-ai-fields">
          <label>Câmera<input name="camera_id" value={form.camera_id} onChange={update} required /></label>
          <label>Data e hora<input name="timestamp" type="datetime-local" value={form.timestamp} onChange={update} required /></label>
          <label>Tipo do evento<input name="event_type" value={form.event_type} onChange={update} required /></label>
          <label>Confiança (0 a 1)<input name="confidence" type="number" min="0" max="1" step="0.01" value={form.confidence} onChange={update} required /></label>
        </div>
        <label>Observação do operador<textarea name="observacao" value={form.observacao} onChange={update} required /></label>
        <label>Pergunta para a triagem<textarea name="pergunta" value={form.pergunta} onChange={update} required /></label>
        <div className="generative-ai-actions"><button className="generative-ai-submit" type="submit" disabled={loading}>{loading ? 'Analisando...' : 'Analisar alerta'}</button><span>A IA sugere. O operador decide.</span></div>
        <div className="generative-ai-flow"><span className="generative-ai-flow-title">FLUXO DE TRIAGEM</span><div><strong>01</strong><span>Evento recebido da câmera</span></div><div><strong>02</strong><span>IA consulta fontes e sugere uma conduta</span></div><div><strong>03</strong><span>Operador valida antes do encaminhamento</span></div></div>
      </form>
      <div className="generative-ai-result">
        <div className="generative-ai-panel-head"><span className="generative-ai-step">02</span><div><h3>Painel de triagem</h3><span>Síntese, prioridade e fontes consultadas</span></div></div>
        {error && <div className="generative-ai-error"><AlertTriangle size={16} />{error}</div>}
        {!error && !triagem && <div className="generative-ai-empty"><BrainCircuit size={25} /><strong>Aguardando triagem</strong><span>Preencha os dados do alerta para consultar a análise.</span></div>}
        {triagem && <div className="generative-ai-result-body">
          <div className="generative-ai-result-top"><div><span className="eyebrow">RESULTADO DA ANÁLISE</span><h3>{triagem.recusa ? 'Triagem recusada' : String(triagem.tipo_provavel || 'Não informado').replaceAll('_', ' ')}</h3></div><span className={`generative-ai-badge ${triagem.recusa ? 'refused' : ''}`}>{triagem.recusa ? 'Revisão necessária' : 'Sugestão gerada'}</span></div>
          <div className="generative-ai-result-metrics"><div><span>Prioridade</span><strong>{triagem.recusa ? '—' : triagem.prioridade_sugerida || '—'}</strong></div><div><span>Referências</span><strong>{result.trechos_recuperados.length} trecho(s)</strong></div></div>
          <div className="generative-ai-next"><span>PRÓXIMO PASSO</span><p>{triagem.recusa ? triagem.motivo_recusa : triagem.proximo_passo || 'Não informado'}</p></div>
          <div className="generative-ai-missing"><span>INFORMAÇÕES AUSENTES</span><div className="generative-ai-chips">{(triagem.informacoes_ausentes || []).length ? triagem.informacoes_ausentes.map(item => <span key={item}>{item.replaceAll('_', ' ')}</span>) : <span>Nenhuma informada</span>}</div></div>
          <div className="generative-ai-references"><span>TRECHOS UTILIZADOS</span>{result.trechos_recuperados.map(item => <div className="generative-ai-reference" key={item.id}><strong>{item.id}</strong><span>{item.fonte}{item.url ? ` · ${item.url}` : ''}</span><small>relevância {item.relevancia}</small></div>)}</div>
          <div className="generative-ai-human"><CheckCircle2 size={15} /> Validação humana obrigatória antes de qualquer encaminhamento.</div>
          <button className="generative-ai-json-toggle" type="button" onClick={() => setShowJson(value => !value)}>{showJson ? 'Ocultar JSON completo' : 'Mostrar JSON completo'}</button>
          {showJson && <pre className="generative-ai-json">{JSON.stringify(result, null, 2)}</pre>}
        </div>}
      </div>
    </div>
  </section>
}
