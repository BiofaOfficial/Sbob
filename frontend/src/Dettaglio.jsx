import { useEffect, useRef, useState } from 'react'
import { api, durataFase, mmss } from './api.js'
import { useT } from './i18n.js'
import { Stato, trascorso, useTick } from './Fasi.jsx'
import { coloreCorso } from './App.jsx'
import Markdown from './Markdown.jsx'
import Mappa from './Mappa.jsx'
import { Autoverifica, Flashcard, Glossario } from './Studio.jsx'

const SCHEDE = ['prodotto', 'dispensa', 'mappa', 'flashcard', 'autoverifica', 'glossario', 'trascritto']
const EXPORT = {
  prodotto: ['pdf', 'md'], dispensa: ['pdf', 'md'], mappa: ['md'], flashcard: ['txt', 'pdf', 'md'],
  autoverifica: ['pdf', 'md'], glossario: ['pdf', 'md'], trascritto: ['pdf', 'md'],
}
// fase da cui dipende ogni sezione (per raccontare a che punto siamo)
const FASE_DI = { prodotto: 'prodotto', dispensa: 'dispensa', mappa: 'mappa', flashcard: 'flashcard', autoverifica: 'autoverifica', glossario: 'glossario', trascritto: 'trascrizione' }

function Tendina({ etichetta, children, classe = '' }) {
  const [aperta, setAperta] = useState(false)
  const rif = useRef()
  useEffect(() => {
    if (!aperta) return
    const chiudi = (e) => { if (!rif.current?.contains(e.target)) setAperta(false) }
    document.addEventListener('mousedown', chiudi)
    return () => document.removeEventListener('mousedown', chiudi)
  }, [aperta])
  return (
    <div className="menu-wrap" ref={rif}>
      <button className={`btn piccolo ${classe}`} onClick={() => setAperta(!aperta)}>{etichetta} ▾</button>
      {aperta && <div className="menu" onClick={() => setAperta(false)}>{children}</div>}
    </div>
  )
}

/** Lavoro fermo: una fase è in errore e quelle dopo non possono partire. Dice quale, perché e come uscirne. */
function Fermo({ lav, prodottoNome, azioni }) {
  const { t } = useT()
  const f = lav.fasi.find((x) => x.stato === 'errore')
  if (!f) return null
  const nome = f.nome === 'prodotto' ? prodottoNome : t('f_' + f.nome)
  return (
    <div className="fermo">
      <span className="fermo-icona">!</span>
      <div className="fermo-testo">
        <b>{t('n_bloccato').replace('{fase}', nome)}</b>
        {f.errore && <small>{f.errore}</small>}
        <div className="fermo-azioni">
          {f.nome === 'voci' && <button className="btn piccolo primario" onClick={azioni.senzaVoci}>{t('senza_voci')}</button>}
          <button className="btn piccolo" onClick={() => azioni.riprova(f.nome)}>↻ {t('riprova')}</button>
        </div>
      </div>
    </div>
  )
}

/** Striscia sempre visibile mentre Sbob lavora sul lavoro aperto (anche dopo «Rigenera»). */
function Striscia({ lav, prodottoNome }) {
  const { t } = useT()
  const corrente = lav.fasi.find((f) => f.stato === 'corso')
  const inCoda = lav.fasi.some((f) => f.stato === 'coda')
  const fermo = lav.fasi.some((f) => f.stato === 'errore')
  useTick(!!corrente)
  if (!corrente && (!inCoda || fermo)) return null
  const vis = lav.fasi.filter((f) => f.stato !== 'saltata' && f.stato !== 'manuale')
  const fatte = vis.filter((f) => f.stato === 'fatto').length
  const quota = Math.round(((fatte + (corrente?.progress || 0)) / Math.max(vis.length, 1)) * 100)
  return (
    <div className="striscia">
      <span className="spinner" />
      <div className="striscia-testo">
        <b>{corrente ? fraseFase(corrente, lav, t, prodottoNome) : t('n_coda')}</b>
        {corrente && <small>{t('fase_n')} {fatte + 1} {t('di_')} {vis.length}, {t('da_tempo')} {trascorso(corrente.inizio)}</small>}
      </div>
      <div className="striscia-barra"><i style={{ width: `${quota}%` }} /></div>
    </div>
  )
}

function fraseFase(f, lav, t, prodottoNome) {
  if (f.nome === 'acquisizione') return t(lav.sorgente_tipo === 'url' ? 'n_acquisizione_url' : 'n_acquisizione_file')
  if (f.nome === 'note') {
    const [i, n] = (f.dettaglio || '').split('/')
    return t('n_note') + (n ? ` (${t('blocco')} ${Math.min(Number(i) + 1, Number(n))} ${t('di_')} ${n}).` : '.')
  }
  if (f.nome === 'prodotto') return `${t('n_prodotto')}: ${prodottoNome}.`
  if (f.nome === 'dispensa' && f.dettaglio) {
    const [i, n] = f.dettaglio.split('/')
    return `${t('n_dispensa')} (${t('parte')} ${Math.min(Number(i) + 1, Number(n))} ${t('di_')} ${n}).`
  }
  return t('n_' + f.nome)
}

function SceltaDispensa({ crea }) {
  const { t } = useT()
  const [livello, setLivello] = useState('sintetica')
  return (
    <div className="scelta-dispensa">
      <p>{t('dispensa_intro')}</p>
      <div className="opzioni-dispensa">
        {['sintetica', 'approfondita'].map((l) => (
          <button key={l} className={`opzione ${livello === l ? 'on' : ''}`} onClick={() => setLivello(l)}>
            <b>{t('liv_' + l)}</b><small>{t('liv_' + l + '_desc')}</small>
          </button>
        ))}
      </div>
      <button className="btn primario" onClick={() => crea(livello)}>{t('crea_dispensa')}</button>
    </div>
  )
}

const ICONE_FONTE = {
  youtube: <svg viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="5" fill="#e62117" /><path d="M10 8.5v7l6-3.5z" fill="#fff" /></svg>,
  vimeo: <svg viewBox="0 0 24 24"><rect x="1" y="2" width="22" height="20" rx="5" fill="#1ab7ea" /><path d="M10 8.5v7l6-3.5z" fill="#fff" /></svg>,
  web: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9.5" /><path d="M2.5 12h19M12 2.5c3 3 3 16 0 19M12 2.5c-3 3-3 16 0 19" /></svg>,
  video: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2.5" y="5.5" width="13" height="13" rx="2.5" /><path d="M15.5 10l6-3.5v11l-6-3.5" /></svg>,
  audio: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="8.5" y="2.5" width="7" height="12" rx="3.5" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3.5" /></svg>,
  file: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M6 2.5h8l4.5 4.5v14.5H6z M14 2.5V7h4.5" /></svg>,
}

function tipoFonte(l) {
  if (l.sorgente_tipo === 'url') {
    const u = l.sorgente.toLowerCase()
    return /youtube\.com|youtu\.be/.test(u) ? 'youtube' : /vimeo\.com/.test(u) ? 'vimeo' : 'web'
  }
  const ext = (l.sorgente.split('.').pop() || '').toLowerCase()
  if (['mp4', 'mov', 'mkv', 'webm', 'avi', 'm4v', 'mpg', 'mpeg', 'wmv'].includes(ext)) return 'video'
  if (['m4a', 'mp3', 'wav', 'aac', 'ogg', 'oga', 'flac', 'opus', 'wma', 'aiff', 'aif', 'caf', 'amr'].includes(ext)) return 'audio'
  return 'file'
}

function Fonte({ lavoro }) {
  const { t } = useT()
  const tipo = tipoFonte(lavoro)
  return (
    <span className="fonte">
      <span className={`fonte-ico fonte-${tipo}`}>{ICONE_FONTE[tipo]}</span>
      <span className="fonte-testo">
        <b>{t('src_' + tipo)}</b>
        {lavoro.sorgente_tipo === 'url'
          ? <a href={lavoro.sorgente} target="_blank" rel="noreferrer">{lavoro.meta?.autore || lavoro.sorgente}</a>
          : <span className="tenue">{lavoro.sorgente}</span>}
      </span>
    </span>
  )
}

/** Racconta in parole che cosa sta facendo Sbob, invece di un generico «in lavorazione». */
function Avanzamento({ lav, sezione, prodottoNome, azioni }) {
  const { t } = useT()
  const corrente = lav.fasi.find((f) => f.stato === 'corso')
  useTick(!!corrente)
  const vis = lav.fasi.filter((f) => f.stato !== 'saltata' && f.stato !== 'manuale')
  const frase = (f) => fraseFase(f, lav, t, prodottoNome)
  const obiettivo = FASE_DI[sezione]
  return (
    <div className="avanzamento">
      {corrente ? (
        <div className="ora">
          <span className="spinner" />
          <div>
            <p>{frase(corrente)}</p>
            <small>{t('da_tempo')} {trascorso(corrente.inizio)}{corrente.progress > 0 && corrente.progress < 1 ? `, ${Math.round(corrente.progress * 100)}%` : ''}</small>
          </div>
        </div>
      ) : lav.fasi.some((f) => f.stato === 'errore') ? <Fermo lav={lav} prodottoNome={prodottoNome} azioni={azioni} />
        : <div className="ora"><span className="spinner" /><p>{t('n_coda')}</p></div>}
      <ol className="percorso">
        {vis.map((f) => (
          <li key={f.nome} className={`st-${f.stato} ${f.nome === obiettivo ? 'obiettivo' : ''}`}>
            <span className="pallino" />{f.nome === 'prodotto' ? prodottoNome : t('f_' + f.nome)}
            <em>{f.stato === 'fatto' ? durataFase(f) : f.stato === 'corso' ? trascorso(f.inizio) : ''}</em>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Lettore({ id, audioRef, tempo, setTempo }) {
  const [durata, setDurata] = useState(0)
  const [play, setPlay] = useState(false)
  const [vel, setVel] = useState(1)
  const a = audioRef.current
  const cambiaVel = () => {
    const v = { 1: 1.25, 1.25: 1.5, 1.5: 2, 2: 1 }[vel]
    setVel(v)
    if (a) a.playbackRate = v
  }
  return (
    <div className="player">
      <audio ref={audioRef} preload="metadata" src={`/api/lavori/${id}/audio`}
        onLoadedMetadata={(e) => setDurata(e.target.duration)} onTimeUpdate={(e) => setTempo(e.target.currentTime)}
        onPlay={() => setPlay(true)} onPause={() => setPlay(false)} />
      <button className="play" onClick={() => a && (a.paused ? a.play() : a.pause())}>{play ? '❚❚' : '▶'}</button>
      <button className="salto" onClick={() => a && (a.currentTime = Math.max(0, a.currentTime - 15))} title="-15s">↺15</button>
      <span className="mono tenue">{mmss(tempo * 1000)}</span>
      <input type="range" className="barra-audio" min="0" max={durata || 0} step="1" value={tempo}
        style={{ '--p': `${durata ? (tempo / durata) * 100 : 0}%` }}
        onChange={(e) => { if (a) a.currentTime = Number(e.target.value) }} />
      <span className="mono tenue">{mmss(durata * 1000)}</span>
      <button className="salto" onClick={cambiaVel}>{vel}×</button>
    </div>
  )
}

function Trascritto({ lav, setLav, seek, tempo }) {
  const { t } = useT()
  const segmenti = lav.segmenti
  const attivo = segmenti.findIndex((s) => tempo * 1000 >= s.start_ms && tempo * 1000 < s.end_ms)
  const rif = useRef()
  const ultimo = useRef(null)
  useEffect(() => { rif.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [attivo])
  async function alterna(e, s) {
    const escluso = !s.escluso
    let indici = [s.indice]
    if (e.shiftKey && ultimo.current !== null) {
      const [a, b] = [Math.min(ultimo.current, s.indice), Math.max(ultimo.current, s.indice)]
      indici = segmenti.filter((x) => x.indice >= a && x.indice <= b).map((x) => x.indice)
    }
    ultimo.current = s.indice
    setLav(await api.put(`/api/lavori/${lav.id}/segmenti`, { indici, escluso }))
  }
  return (
    <div className="trascritto">
      <p className="aiuto">{t('escludi_aiuto')}</p>
      {segmenti.map((s, i) => (
        <p key={s.indice} ref={i === attivo ? rif : null} className={`${i === attivo ? 'attivo' : ''} ${s.escluso ? 'escluso' : ''}`}>
          <button className="ts" onClick={() => seek(s.start_ms / 1000)}>{mmss(s.start_ms)}</button>
          <span className="testo">{s.nome_voce && <strong className="nome-voce">{s.nome_voce} </strong>}{s.testo}</span>
          <button className="togli" onClick={(e) => alterna(e, s)} title={s.escluso ? '↺' : '✕'}>{s.escluso ? '↺' : '✕'}</button>
        </p>
      ))}
    </div>
  )
}

function Voci({ lavoro, ricarica }) {
  const { t } = useT()
  const [voci, setVoci] = useState(lavoro.voci)
  const [parti, setParti] = useState([lavoro.parti[0] || '', lavoro.parti[1] || ''])
  useEffect(() => setVoci(lavoro.voci), [lavoro.voci.length])
  const confronto = lavoro.profilo === 'confronto'
  if (!lavoro.voci_attive || !voci.length) return null
  const [err, setErr] = useState('')
  async function salva() {
    setErr('')
    try {
      if (confronto) await api.patch(`/api/lavori/${lavoro.id}`, { parti })
      ricarica(await api.put(`/api/lavori/${lavoro.id}/voci`, voci))
    } catch (e) { setErr(e.message) }
  }
  return (
    <section>
      <h5>{t('voci')}</h5>
      {confronto && (
        <div className="due spazio-sotto">
          <input value={parti[0]} placeholder={t('parte_a')} onChange={(e) => setParti([e.target.value, parti[1]])} />
          <input value={parti[1]} placeholder={t('parte_b')} onChange={(e) => setParti([parti[0], e.target.value])} />
        </div>
      )}
      {voci.map((v, i) => (
        <div key={v.etichetta} className="riga-voce">
          <span className="tenue">{i + 1}</span>
          <input value={v.nome} placeholder={`Voce ${i + 1}`} onChange={(e) => setVoci(voci.map((x) => x === v ? { ...x, nome: e.target.value } : x))} />
          {confronto && <select value={v.parte} onChange={(e) => setVoci(voci.map((x) => x === v ? { ...x, parte: e.target.value } : x))}>
            <option value="">—</option>
            {parti.filter(Boolean).map((p) => <option key={p} value={p}>{p}</option>)}
          </select>}
        </div>
      ))}
      <small>{t('rinomina_nota')}</small>
      {err && <p className="errore">{err}</p>}
      <button className="btn piccolo spazio-sopra" onClick={salva}>{t('salva')}</button>
    </section>
  )
}

function Dettagli({ lavoro, ricarica, chiudi, prodottoNome }) {
  const { t, lingua } = useT()
  const [corsi, setCorsi] = useState([])
  const [titolo, setTitolo] = useState(lavoro.titolo)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/api/corsi').then(setCorsi) }, [])
  const fai = async (richiesta) => { setErr(''); try { ricarica(await richiesta()) } catch (e) { setErr(e.message) } }
  const riprova = (nome) => fai(() => api.post(`/api/lavori/${lavoro.id}/fasi/${nome}/riprova`))
  const vociBloccate = !lavoro.voci_disponibili && !lavoro.voci_attive
  async function elimina() {
    if (!window.confirm(t('conferma_elimina'))) return
    await api.del(`/api/lavori/${lavoro.id}`)
    window.location.hash = '#/'
  }
  const fatte = lavoro.fasi.filter((f) => f.inizio && f.fine)
  const tot = fatte.reduce((s, f) => s + (new Date(f.fine) - new Date(f.inizio)), 0) / 1000
  return (
    <>
      <div className="velo" onClick={chiudi} />
      <aside className="cassetto">
        <div className="cassetto-testa"><b>{t('dettagli')}</b><button className="link" onClick={chiudi}>✕ {t('chiudi')}</button></div>
        {err && <p className="errore cassetto-errore">{err}</p>}
        <section>
          <label className="campo"><span>{t('titolo')}</span>
            <input value={titolo} onChange={(e) => setTitolo(e.target.value)}
              onBlur={() => titolo !== lavoro.titolo && fai(() => api.patch(`/api/lavori/${lavoro.id}`, { titolo }))} /></label>
          <label className="campo"><span>{t('corso')}</span>
            <select value={lavoro.corso_id || ''} onChange={(e) => fai(() => api.patch(`/api/lavori/${lavoro.id}`,
              e.target.value ? { corso_id: Number(e.target.value) } : { senza_corso: true }))}>
              <option value="">{t('nessuno')}</option>
              {corsi.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select></label>
          <label className="campo"><span>{t('lingua_breve')}</span>
            <select value={lavoro.lingua} onChange={(e) => window.confirm(t('conferma_lingua')) && fai(() => api.patch(`/api/lavori/${lavoro.id}`, { lingua: e.target.value }))}>
              <option value="auto">{t('auto')}{lavoro.lingua === 'auto' && lavoro.lingua_rilevata ? ` (${lavoro.lingua_rilevata})` : ''}</option>
              {['it', 'en', 'es', 'fr', 'de', 'pt'].map((l) => <option key={l} value={l}>{{ it: 'Italiano', en: 'English', es: 'Español', fr: 'Français', de: 'Deutsch', pt: 'Português' }[l]}</option>)}
            </select>
            <small>{t('lingua_aiuto')}</small></label>
          <div className={`voci-box ${vociBloccate ? 'bloccato' : ''}`}>
            <label className="spunta">
              <input type="checkbox" checked={!!lavoro.voci_attive} disabled={vociBloccate}
                onChange={(e) => fai(() => api.patch(`/api/lavori/${lavoro.id}`, { voci_attive: e.target.checked }))} />
              <span>{t('voci_sep')}
                {vociBloccate ? <small>{t('voci_senza_token')} <a href="#/impostazioni">{t('impostazioni')}</a>.</small>
                  : <small>{t('voci_nota_ok')}</small>}</span>
            </label>
          </div>
        </section>
        <Voci lavoro={lavoro} ricarica={ricarica} />
        <section>
          <h5>{t('fasi')}{tot > 0 && ` (${tot < 60 ? Math.round(tot) + ' s' : Math.round(tot / 60) + ' min'} ${t('totali')})`}</h5>
          {lavoro.fasi.filter((f) => f.stato !== 'saltata').map((f) => (
            <div key={f.nome} className={`fase-riga st-testo-${f.stato}`}>
              <span className="nome">{f.nome === 'prodotto' ? prodottoNome : t('f_' + f.nome)}</span>
              <span className="tenue">{t('st_' + f.stato)}</span>
              <span className="tenue mono">{durataFase(f)}</span>
              {['fatto', 'errore'].includes(f.stato) && f.nome !== 'voci' &&
                <button className="link" onClick={() => riprova(f.nome)}>{f.stato === 'errore' ? t('riprova') : '↻'}</button>}
              {f.errore && <div className="err">{f.errore}</div>}
            </div>
          ))}
          <button className="btn piccolo spazio-sopra" onClick={() => riprova('note')}>↻ {t('rigenera_tutto')}</button>
        </section>
        <section>
          <dl className="info">
            <dt>{t('fonte')}</dt><dd><Fonte lavoro={lavoro} /></dd>
            <dt>{t('creato')}</dt><dd>{new Date(lavoro.creato).toLocaleString(lingua, { dateStyle: 'medium', timeStyle: 'short' })}</dd>
            {lavoro.durata_s ? <><dt>{t('durata_reg')}</dt><dd>{mmss(lavoro.durata_s * 1000)}</dd></> : null}
            {lavoro.lingua_rilevata && <><dt>{t('lingua_breve')}</dt><dd>{lavoro.lingua_rilevata}</dd></>}
          </dl>
          <button className="link pericolo" onClick={elimina}>{t('elimina')}</button>
        </section>
      </aside>
    </>
  )
}

export default function Dettaglio({ id, profili }) {
  const { t } = useT()
  const [lav, setLav] = useState(null)
  const [errore, setErrore] = useState('')
  const [scheda, setScheda] = useState('prodotto')
  const [tempo, setTempo] = useState(0)
  const [dettagli, setDettagli] = useState(false)
  const [errAzione, setErrAzione] = useState('')
  const audioRef = useRef()
  const mappaRef = useRef({})

  useEffect(() => {
    let vivo = true, timer
    const carica = () => api.get(`/api/lavori/${id}`).then((l) => {
      if (!vivo) return
      setLav(l)
      const attivo = l.fasi.some((f) => f.stato === 'coda' || f.stato === 'corso')
      timer = setTimeout(carica, attivo ? 2000 : 15000)
    }).catch((e) => vivo && setErrore(e.message))
    carica()
    return () => { vivo = false; clearTimeout(timer) }
  }, [id])

  if (errore) return <p className="errore centro">{errore}</p>
  if (!lav) return <p className="centro">…</p>
  const prof = profili.profili.find((p) => p.id === lav.profilo)
  const fase = Object.fromEntries(lav.fasi.map((f) => [f.nome, f]))
  const seek = (s) => { const a = audioRef.current; if (a) { a.currentTime = s; a.play() } }
  const lp = lav.lingua_effettiva === 'it' ? 'it' : 'en'
  const conteggio = (s) => {
    const c = lav.prodotti[s]?.contenuto
    if (!c || typeof c !== 'object') return null
    return (c.carte || c.domande || c.termini || []).length
  }
  const etichetta = (s) => s === 'prodotto' ? prof.prodotto[lp] : t(s === 'trascritto' ? 'trascritto' : 'f_' + s)
  const pronto = (s) => s === 'trascritto' ? lav.segmenti.length > 0 : !!lav.prodotti[s] && fase[s]?.stato === 'fatto'
  const fai = async (richiesta) => { setErrAzione(''); try { setLav(await richiesta()) } catch (e) { setErrAzione(e.message) } }
  const rigenera = (nome) => fai(() => api.post(`/api/lavori/${id}/fasi/${nome}/riprova`))
  const creaDispensa = (livello) => fai(() => api.post(`/api/lavori/${id}/dispensa`, { livello }))
  const azioni = { riprova: rigenera, senzaVoci: () => fai(() => api.patch(`/api/lavori/${id}`, { voci_attive: false })) }
  const exp = (s, fmt) => `/api/lavori/${id}/export/${s}.${fmt}`
  const nomeFmt = (fmt) => fmt === 'txt' ? 'Anki (.txt)' : fmt === 'md' ? 'Markdown' : fmt.toUpperCase()
  const qualcosa = Object.keys(lav.prodotti).length > 0 || lav.segmenti.length > 0

  function contenuto() {
    const f = fase[FASE_DI[scheda]]
    if (scheda === 'trascritto') {
      if (!lav.segmenti.length) return <Avanzamento lav={lav} sezione={scheda} prodottoNome={prof.prodotto[lp]} azioni={azioni} />
      return <Trascritto lav={lav} setLav={setLav} seek={seek} tempo={tempo} />
    }
    if (scheda === 'dispensa' && f.stato === 'manuale') return <SceltaDispensa crea={creaDispensa} />
    if (f.stato === 'manuale') return (
      <div className="vuoto"><button className="btn primario" onClick={() => fai(() => api.post(`/api/lavori/${id}/studio`))}>{t('genera_studio')}</button></div>)
    if (f.stato === 'errore') return (
      <div className="vuoto"><p className="errore">{f.errore}</p><button className="btn" onClick={() => rigenera(scheda)}>{t('riprova')}</button></div>)
    if (!pronto(scheda)) return <Avanzamento lav={lav} sezione={scheda} prodottoNome={prof.prodotto[lp]} azioni={azioni} />
    const p = lav.prodotti[scheda]
    if (scheda === 'prodotto') return <Markdown testo={p.contenuto} seek={seek} />
    if (scheda === 'dispensa') return <div className="pubblicazione"><Markdown testo={p.contenuto} seek={seek} /></div>
    if (scheda === 'mappa') return <Mappa testo={p.contenuto} titolo={lav.titolo} azioni={mappaRef} />
    if (scheda === 'flashcard') return <Flashcard dati={p.contenuto} seek={seek} />
    if (scheda === 'autoverifica') return <Autoverifica dati={p.contenuto} seek={seek} />
    return <Glossario dati={p.contenuto} seek={seek} lav={lav} setLav={setLav} />
  }

  const esclusi = lav.segmenti.filter((s) => s.escluso).map((s) => s.indice)
  return (
    <>
      <div className="top">
        {lav.corso ? <a href={`#/?corso=${lav.corso_id}`} className="tenue briciola"><span className="dot" style={{ background: coloreCorso(lav.corso_id) }} />{lav.corso}</a>
          : <a href="#/" className="tenue briciola">{t('tutti_lavori')}</a>}
        <span className="spazio" />
        {qualcosa && (
          <Tendina etichetta={`⤓ ${t('esporta')}`}>
            <a href={exp('tutto', 'pdf')}>{t('tutto_pdf')}</a>
            <a href={exp('tutto', 'md')}>{t('tutto_md')}</a>
          </Tendina>
        )}
        <button className="btn piccolo" onClick={() => setDettagli(true)}>ⓘ {t('dettagli')}</button>
      </div>
      <div className="pagina dettaglio">
        <header className="testa-lavoro">
          <h1>{prof.icona} {lav.titolo}</h1>
          <Stato stato={lav.stato} />
        </header>
        {errAzione && <div className="banner banner-errore"><span>{errAzione}</span><button className="link" onClick={() => setErrAzione('')}>✕</button></div>}
        {(scheda === 'trascritto' ? lav.segmenti.length > 0 : pronto(scheda)) && <Striscia lav={lav} prodottoNome={prof.prodotto[lp]} />}
        {lav.trascritto_modificato && !['coda', 'corso'].includes(fase.note?.stato) ? (
          <div className="banner">
            <span>{t('trascr_mod')}</span>
            <button className="btn piccolo primario" onClick={() => rigenera('note')}>↻ {t('rigenera_ora')}</button>
          </div>
        ) : null}
        <div className="riga-schede">
          <div className="segmenti schede">
            {SCHEDE.map((s) => (
              <button key={s} className={s === scheda ? 'on' : ''} onClick={() => setScheda(s)}>
                {etichetta(s)}{conteggio(s) ? <span className="tenue"> {conteggio(s)}</span> : null}
                {fase[FASE_DI[s]]?.stato === 'corso' && <span className="spinner mini" />}
              </button>
            ))}
          </div>
          <span className="spazio" />
          {pronto(scheda) && (
            <Tendina etichetta={`${t('azioni_di')} ${etichetta(scheda)}`}>
              {!['trascritto', 'dispensa'].includes(scheda) && <button onClick={() => rigenera(scheda)}>↻ {t('rigenera')}</button>}
              {scheda === 'dispensa' && ['sintetica', 'approfondita'].map((l) => (
                <button key={l} onClick={() => creaDispensa(l)}>↻ {t('rigenera')} {t('liv_' + l).toLowerCase()}{lav.dispensa_livello === l ? ' ✓' : ''}</button>))}
              {scheda === 'glossario' && <button onClick={async () => {
                try {
                  const r = await api.post(`/api/lavori/${id}/vocabolario`, { termini: lav.prodotti.glossario.contenuto.termini.map((x) => x.termine) })
                  setLav({ ...lav, vocabolario: r.vocabolario })
                } catch (e) { setErrAzione(e.message) }
              }}>＋ {t('aggiungi_tutti')}</button>}
              {scheda === 'trascritto' && esclusi.length > 0 && <button onClick={() => fai(() => api.put(`/api/lavori/${id}/segmenti`, { indici: esclusi, escluso: false }))}>↺ {t('ripristina_tutto')}</button>}
              <hr />
              {EXPORT[scheda].map((fmt) => <a key={fmt} href={exp(scheda, fmt)}>⤓ {t('scarica')} {nomeFmt(fmt)}</a>)}
              {scheda === 'mappa' && <>
                <button onClick={() => mappaRef.current.svg?.()}>⤓ {t('scarica')} SVG</button>
                <button onClick={() => mappaRef.current.png?.()}>⤓ {t('scarica')} PNG</button>
              </>}
              {scheda !== 'trascritto' && <p className="avviso-testo">{t('da_rileggere')}</p>}
            </Tendina>
          )}
        </div>
        <div className={`doc ${scheda === 'mappa' && pronto('mappa') ? 'doc-mappa' : ''}`}>{contenuto()}</div>
      </div>
      {lav.audio && <Lettore id={id} audioRef={audioRef} tempo={tempo} setTempo={setTempo} />}
      {dettagli && <Dettagli lavoro={lav} ricarica={setLav} chiudi={() => setDettagli(false)} prodottoNome={prof.prodotto[lp]} />}
    </>
  )
}
