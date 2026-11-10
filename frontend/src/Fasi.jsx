import { useEffect, useState } from 'react'
import { durataFase } from './api.js'
import { useT } from './i18n.js'

const ICONE = { fatto: '✓', corso: '', coda: '○', errore: '!', manuale: '◌' }

export function trascorso(inizio) {
  const s = Math.max(0, Math.round((Date.now() - new Date(inizio)) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}

export function useTick(attivo) {
  const [, set] = useState(0)
  useEffect(() => {
    if (!attivo) return
    const id = setInterval(() => set((x) => x + 1), 1000)
    return () => clearInterval(id)
  }, [attivo])
}

function secondi(f) {
  if (f.inizio && f.fine) return Math.max(0, (new Date(f.fine) - new Date(f.inizio)) / 1000)
  if (f.stato === 'corso' && f.inizio) return Math.max(0, (Date.now() - new Date(f.inizio)) / 1000)
  return 0
}

/** Tempo totale di elaborazione (aggiornato dal vivo mentre lavora), come numero grande + unità. */
export function TempoTotale({ fasi }) {
  const vis = fasi.filter((f) => f.stato !== 'saltata' && f.stato !== 'manuale')
  useTick(vis.some((f) => f.stato === 'corso'))
  const s = vis.map(secondi).reduce((a, b) => a + b, 0)
  if (s < 1) return <b>—</b>
  if (s < 60) return <><b>{Math.round(s)}</b><small>s</small></>
  const m = Math.round(s / 60)
  return m < 60 ? <><b>{m}</b><small>min</small></> : <><b>{Math.floor(m / 60)}:{String(m % 60).padStart(2, '0')}</b><small>h</small></>
}

/** Linea del tempo del lavoro: ogni fase occupa uno spazio proporzionale alla sua durata. */
export function LineaFasi({ fasi, nomeProdotto }) {
  const { t } = useT()
  const vis = fasi.filter((f) => f.stato !== 'saltata' && f.stato !== 'manuale')
  useTick(vis.some((f) => f.stato === 'corso'))
  const durate = vis.map(secondi)
  const tot = durate.reduce((a, b) => a + b, 0)
  // radice quadrata: le fasi lunghe pesano meno, quelle brevi restano leggibili
  const pesi = durate.map((s) => Math.sqrt(s))
  const base = Math.max(pesi.reduce((a, b) => a + b, 0) / vis.length, 1) * 0.6
  const nome = (f) => (f.nome === 'prodotto' && nomeProdotto ? nomeProdotto : t('f_' + f.nome))
  const durata = (f, s) => (f.stato === 'fatto' || f.stato === 'corso') && s >= 1 ? (s < 60 ? `${Math.round(s)} s` : `${Math.round(s / 60)} min`) : ''
  return (
    <div className="linea" role="list">
      {vis.map((f, i) => (
        <div key={f.nome} role="listitem" className={`tratto st-${f.stato}`} style={{ flexGrow: pesi[i] + base }}
          title={`${nome(f)}: ${t('st_' + f.stato)}${durata(f, durate[i]) ? ', ' + durata(f, durate[i]) : ''}${f.errore ? ' — ' + f.errore : ''}`}>
          <span className="tratto-nome">{nome(f)}</span>
          <span className="tratto-tempo">{f.stato === 'corso' && f.nome === 'note' && f.dettaglio ? f.dettaglio : durata(f, durate[i])}</span>
        </div>
      ))}
      {tot > 0 && <span className="linea-tot">{tot < 60 ? `${Math.round(tot)} s` : `${Math.round(tot / 60)} min`}</span>}
    </div>
  )
}

/** Fasi di un lavoro come pillole: nome, stato, durata. */
export function CatenaFasi({ fasi, nomeProdotto }) {
  const { t } = useT()
  const vis = fasi.filter((f) => f.stato !== 'saltata')
  useTick(vis.some((f) => f.stato === 'corso'))
  return (
    <div className="catena">
      {vis.map((f) => (
        <span key={f.nome} className={`fase st-${f.stato}`} title={f.errore || t('st_' + f.stato)}>
          {f.stato === 'corso' ? <span className="spinner mini" /> : <b>{ICONE[f.stato]}</b>}
          {f.nome === 'prodotto' && nomeProdotto ? nomeProdotto : t('f_' + f.nome)}
          <em>{f.stato === 'fatto' ? durataFase(f)
            : f.stato === 'corso' ? (f.dettaglio && f.nome === 'note' ? f.dettaglio : f.progress > 0 && f.progress < 1 ? `${Math.round(f.progress * 100)}%` : trascorso(f.inizio))
            : ''}</em>
        </span>
      ))}
    </div>
  )
}

export function Stato({ stato }) {
  const { t } = useT()
  return <span className={`badge st-${stato}`}><i />{t('st_' + stato)}</span>
}
