import { useEffect, useState } from 'react'
import { AlertCircle, Check, Clock3, Film, ScanLine } from 'lucide-react'
import { api } from '../services/api'
import './GallerySection.css'

const typeLabels = {
  'head-on': 'Colisão frontal',
  'rear-end': 'Colisão traseira',
  sideswipe: 'Colisão lateral',
  single: 'Veículo único',
  't-bone': 'Colisão perpendicular',
}

function formatDuration(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0))
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}

function accidentLabel(index) {
  return `Acidente ${String(index + 1).padStart(2, '0')}`
}

function VideoPlayer({ title, path, accidentName }) {
  const [failed, setFailed] = useState(false)
  const src = api.galleryVideoUrl(path)

  return <article className="gallery-player">
    <div className="gallery-player-heading">
      <span className="gallery-player-icon"><Film size={17} /></span>
      <div><h3>{title}</h3><span>{accidentName}</span></div>
    </div>
    <div className="gallery-video-frame">
      {failed ? <div className="gallery-video-error"><AlertCircle size={19} /><span>Não foi possível reproduzir este vídeo.</span></div> :
        <video
          key={src}
          controls
          playsInline
          preload="metadata"
          src={src}
          onError={() => setFailed(true)}
          onLoadedMetadata={() => setFailed(false)}
          aria-label={`${title} — ${accidentName}`}
        />}
    </div>
  </article>
}

function Detail({ icon: Icon, label, value, description }) {
  return <div className="gallery-detail">
    <span className="gallery-detail-icon"><Icon size={17} /></span>
    <div><span className="gallery-detail-label">{label}</span><strong>{value}</strong>
      {description && <small>{description}</small>}</div>
  </div>
}

export default function GallerySection() {
  const [manifest, setManifest] = useState(null)
  const [selectedName, setSelectedName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.gallery()
      .then(data => {
        if (!active) return
        setManifest(data)
        setSelectedName(current => current || data.videos?.[0]?.name || '')
      })
      .catch(reason => {
        if (active) setError(reason.message || 'Não foi possível carregar a galeria.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const videos = manifest?.videos || []
  const selectedIndex = videos.findIndex(video => video.name === selectedName)
  const selected = selectedIndex >= 0 ? videos[selectedIndex] : videos[0]
  const selectedLabel = selected ? accidentLabel(Math.max(0, selectedIndex)) : ''

  return <section className="gallery-section" id="gallery">
    <div className="section-heading gallery-section-heading">
      <div>
        <span className="eyebrow">DEMONSTRAÇÃO DO MODELO</span>
        <h2>Galeria de Detecções</h2>
        <p>Explore os casos e compare cada gravação com o resultado da análise.</p>
      </div>
      <span className="gallery-count"><Film size={16} /> {manifest?.video_count ?? '—'} acidentes</span>
    </div>

    {loading && <div className="gallery-state"><span className="gallery-loading-dot" /> Carregando vídeos da galeria...</div>}
    {!loading && error && <div className="gallery-state gallery-state-error"><AlertCircle size={18} />{error} Verifique se a API está em execução.</div>}
    {!loading && !error && !videos.length && <div className="gallery-state">Nenhum vídeo disponível no manifesto da galeria.</div>}

    {!loading && !error && selected && <>
      <div className="gallery-selected-heading">
        <div className="gallery-selected-title">
          <span className="gallery-selected-kicker"><span className="gallery-live-dot" /> CASO SELECIONADO</span>
          <h3>{selectedLabel}</h3>
        </div>
        <div className="gallery-selected-meta">
          <span className="gallery-type-tag">{typeLabels[selected.accident_type] || selected.accident_type}</span>
          <span className="gallery-duration"><Clock3 size={15} /> {formatDuration(selected.duration_seconds)}</span>
        </div>
      </div>

      <div className="gallery-comparison-grid">
        <VideoPlayer title="Vídeo original" path={selected.original_video} accidentName={selectedLabel} />
        <VideoPlayer title="Detecção pelo modelo" path={selected.processed_video} accidentName={selectedLabel} />
      </div>

      <div className="gallery-details">
        <Detail icon={Clock3} label="Instante do acidente" value={`${Number(selected.accident_time_seconds ?? 0).toFixed(2)} s`} description={`Duração total: ${formatDuration(selected.duration_seconds)}`} />
        <Detail icon={ScanLine} label="Quadros com detecção" value={selected.detected_frames ?? 0} description={`de ${selected.total_frames ?? 0} quadros analisados`} />
        {selected.observation && <div className="gallery-observation">
          <span>OBSERVAÇÃO DA REVISÃO</span>
          <p>{selected.observation}</p>
        </div>}
      </div>

      <div className="gallery-list-heading">
        <div><span className="eyebrow">ACERVO DE DEMONSTRAÇÃO</span><h3>Escolha um acidente</h3></div>
        <span>{videos.length} vídeos</span>
      </div>
      <div className="gallery-card-grid" role="list" aria-label="Acidentes de demonstração">
        {videos.map((video, index) => {
          const active = selected.name === video.name
          return <button
            key={video.name}
            type="button"
            role="listitem"
            className={`gallery-select-card ${active ? 'active' : ''}`}
            onClick={() => setSelectedName(video.name)}
            aria-pressed={active}
            aria-label={`${accidentLabel(index)}, ${typeLabels[video.accident_type] || video.accident_type}, ${formatDuration(video.duration_seconds)}`}
          >
            <span className="gallery-card-index">{String(index + 1).padStart(2, '0')}</span>
            <span className="gallery-card-copy">
              <strong>{accidentLabel(index)}</strong>
              <small>{typeLabels[video.accident_type] || video.accident_type}</small>
            </span>
            <span className="gallery-card-duration">{formatDuration(video.duration_seconds)}</span>
            <span className="gallery-card-selected" aria-hidden="true">{active && <Check size={15} />}</span>
          </button>
        })}
      </div>
      <p className="gallery-disclaimer">Demonstração acadêmica: os resultados podem conter falsos positivos ou deixar de identificar eventos e não confirmam a ocorrência de um acidente.</p>
    </>}
  </section>
}
