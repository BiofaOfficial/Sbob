import { useState } from 'react'
import { api } from './api.js'
import { useT } from './i18n.js'
import { Inline } from './Markdown.jsx'

export function Flashcard({ dati, seek }) {
  const { t } = useT()
  const [i, setI] = useState(0)
  const [girata, setGirata] = useState(false)
  const carte = dati.carte
  const vai = (n) => { setI((n + carte.length) % carte.length); setGirata(false) }
  const c = carte[i]
  return (
    <div className="flash">
      <div className="flash-testa">
        <button className="btn piccolo" onClick={() => vai(i - 1)}>←</button>
        <span>{t('carta')} <b>{i + 1}</b> {t('di')} {carte.length}</span>
        <button className="btn piccolo" onClick={() => vai(i + 1)}>→</button>
      </div>
      <div className={`carta ${girata ? 'girata' : ''}`} onClick={() => setGirata(!girata)}>
        <div className="domanda"><Inline testo={c.domanda} seek={seek} /></div>
        {girata ? <div className="risposta"><Inline testo={c.risposta} seek={seek} /></div> : <small>{t('gira')}</small>}
      </div>
      <details className="tutte">
        <summary>{carte.length} {t('f_flashcard').toLowerCase()}</summary>
        <ol>{carte.map((x, k) => <li key={k}><strong><Inline testo={x.domanda} seek={seek} /></strong><br /><Inline testo={x.risposta} seek={seek} /></li>)}</ol>
      </details>
    </div>
  )
}

export function Autoverifica({ dati, seek }) {
  const { t } = useT()
  const [aperte, setAperte] = useState({})
  return (
    <ol className="autoverifica">
      {dati.domande.map((d, k) => (
        <li key={k}>
          <p className="domanda"><Inline testo={d.domanda} seek={seek} /></p>
          <div className="av-riga">
            <button className="btn piccolo" onClick={() => setAperte({ ...aperte, [k]: !aperte[k] })}>{aperte[k] ? t('nascondi') : t('mostra')}</button>
            {aperte[k] && <p className="risposta"><Inline testo={d.risposta} seek={seek} /></p>}
          </div>
        </li>
      ))}
    </ol>
  )
}

export function Glossario({ dati, seek, lav, setLav }) {
  const { t } = useT()
  const noti = new Set((lav.vocabolario || []).map((x) => x.toLowerCase()))
  const termini = [...dati.termini].sort((a, b) => a.termine.localeCompare(b.termine))
  async function aggiungi(termine) {
    const r = await api.post(`/api/lavori/${lav.id}/vocabolario`, { termini: [termine] })
    setLav({ ...lav, vocabolario: r.vocabolario })
  }
  return (
    <table className="glossario">
      <thead><tr><th>{t('termine')}</th><th>{t('definizione')}</th><th /></tr></thead>
      <tbody>{termini.map((x, k) => (
        <tr key={k}>
          <td><strong>{x.termine}</strong></td>
          <td><Inline testo={x.definizione} seek={seek} /></td>
          <td className="col-voc">{noti.has(x.termine.toLowerCase())
            ? <span className="ok" title={t('nei_termini')}>✓ {t('nei_termini')}</span>
            : <button className="link" onClick={() => aggiungi(x.termine)}>＋ {t('aggiungi_termine')}</button>}</td>
        </tr>
      ))}</tbody>
    </table>
  )
}
