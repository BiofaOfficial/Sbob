import { useEffect, useState } from 'react'
import { api } from './api.js'
import { useT } from './i18n.js'
import { Stato } from './Fasi.jsx'
import { coloreCorso } from './App.jsx'

function Modello({ etichetta, m }) {
  const { t } = useT()
  return (
    <div className="stat">
      <span className="stat-et">{etichetta}</span>
      <span className="stat-val ellissi" title={m.nome}>{m.nome}</span>
      <span className={`spia spia-${m.stato}`}><i />{m.stato}<small>{t('m_' + m.stato)}</small></span>
    </div>
  )
}

function Cruscotto() {
  const { t } = useT()
  const [s, setS] = useState(null)
  const [scalda, setScalda] = useState(false)
  const [err, setErr] = useState('')
  useEffect(() => {
    let vivo = true
    const carica = () => api.get('/api/stato').then((x) => vivo && setS(x)).catch(() => {})
    carica()
    const id = setInterval(carica, 5000)
    return () => { vivo = false; clearInterval(id) }
  }, [])
  if (!s) return null
  async function riscalda() {
    setScalda(true); setErr('')
    try { setS(await api.post('/api/riscalda')) } catch (e) { setErr(e.message) }
    setScalda(false)
  }
  const freddi = ['COLD', 'DOWN'].some((x) => [s.modelli.llm.stato, s.modelli.whisper.stato].includes(x))
  return (
    <section className="cruscotto">
      <Modello etichetta={t('mod_llm')} m={s.modelli.llm} />
      <Modello etichetta={t('mod_trascr')} m={s.modelli.whisper} />
      <div className="stat">
        <span className="stat-et">{t('contesto_ctx')}</span>
        <span className="stat-val mono">{(s.ctx / 1024).toFixed(0)}k token</span>
      </div>
      <a className="stat" href="#/impostazioni">
        <span className="stat-et">{t('token_hf_breve')}</span>
        <span className={`spia ${s.hf_token ? 'spia-WARM' : 'spia-COLD'}`}><i />{s.hf_token ? t('token_impostato') : t('token_assente')}</span>
      </a>
      <div className="stat azione">
        <button className={`btn ${freddi ? 'primario' : ''}`} disabled={scalda} onClick={riscalda}>
          {scalda ? <><span className="spinner mini" />{t('riscaldando')}</> : t('riscalda')}
        </button>
        {err && <small className="errore">{err}</small>}
      </div>
    </section>
  )
}

export default function Home({ profili, h }) {
  const { t, lingua } = useT()
  const q = new URLSearchParams(h.split('?')[1] || '')
  const corso = q.get('corso') || ''
  const statoUrl = q.get('stato') || ''
  const [lavori, setLavori] = useState(null)
  const [corsi, setCorsi] = useState([])
  const [profilo, setProfilo] = useState('')
  const [stato, setStato] = useState('')

  useEffect(() => { api.get('/api/corsi').then(setCorsi) }, [])
  useEffect(() => {
    let vivo = true
    const carica = () => {
      const p = new URLSearchParams({ corso, profilo, stato: statoUrl || stato }).toString()
      api.get('/api/lavori?' + p).then((l) => vivo && setLavori(l)).catch(() => {})
    }
    carica()
    const id = setInterval(carica, 3000)
    return () => { vivo = false; clearInterval(id) }
  }, [corso, profilo, stato, statoUrl])

  const prof = Object.fromEntries(profili.profili.map((p) => [p.id, p]))
  const nomeCorso = corsi.find((c) => String(c.id) === corso)?.nome
  const titolo = nomeCorso || (statoUrl ? t('attivi') : t('tutti_lavori'))
  return (
    <>
      <div className="top">
        {nomeCorso && <span className="dot" style={{ background: coloreCorso(corso) }} />}
        <b>{titolo}</b>
        {lavori && <span className="tenue">{lavori.length}</span>}
        <span className="spazio" />
        <select className="mini" value={profilo} onChange={(e) => setProfilo(e.target.value)}>
          <option value="">{t('tutti_profili')}</option>
          {profili.profili.map((p) => <option key={p.id} value={p.id}>{p.icona} {p.label[lingua]}</option>)}
        </select>
        {!statoUrl && (
          <select className="mini" value={stato} onChange={(e) => setStato(e.target.value)}>
            <option value="">{t('tutti_stati')}</option>
            {['corso', 'coda', 'fatto', 'errore'].map((s) => <option key={s} value={s}>{t('st_' + s)}</option>)}
          </select>
        )}
      </div>
      <div className="pagina">
        {!corso && !statoUrl && <Cruscotto />}
        {lavori && lavori.length === 0 && (
          <div className="vuoto">
            <p>{t('vuoto')}</p>
            <a href="#/nuovo" className="btn primario">＋ {t('nuova_reg')}</a>
            <a href="#/guida" className="link">{t('guida_breve')}</a>
          </div>
        )}
        <div className="righe">
          {(lavori || []).map((l) => (
            <a key={l.id} href={`#/lavoro/${l.id}`} className="riga-lavoro">
              <div className="riga-testa">
                <span className="icona">{prof[l.profilo]?.icona}</span>
                <span className="titolo">{l.titolo}</span>
                {l.corso ? <span className="chip"><span className="dot" style={{ background: coloreCorso(l.corso_id) }} />{l.corso}</span> : <span />}
                <span className="cifra" title={t('durata_reg')}>
                  {l.durata_s ? (l.durata_s < 3600 ? <><b>{Math.max(1, Math.round(l.durata_s / 60))}</b><small>min</small></>
                    : <><b>{Math.floor(l.durata_s / 3600)}:{String(Math.round((l.durata_s % 3600) / 60)).padStart(2, '0')}</b><small>h</small></>) : <b>—</b>}
                  <em>{t('durata_reg')}</em>
                </span>
                <span className="cifra" title={new Date(l.creato).toLocaleString(lingua)}>
                  <b>{new Date(l.creato).toLocaleDateString(lingua, { day: '2-digit' })}</b>
                  <small>{new Date(l.creato).toLocaleDateString(lingua, { month: 'short' }).replace('.', '')}</small>
                  <em>{t('caricato')}</em>
                </span>
                <span className="col-stato"><Stato stato={l.stato} /></span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </>
  )
}
