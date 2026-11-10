import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { useT } from './i18n.js'

const LINGUE = ['it', 'en', 'es', 'fr', 'de', 'pt']
const NOMI_LINGUE = { it: 'Italiano', en: 'English', es: 'Español', fr: 'Français', de: 'Deutsch', pt: 'Português' }
const termini = (testo) => [...new Set((testo || '').split(/[\n,;]+/).map((x) => x.trim()).filter(Boolean))]

function invia(form, onProgress) {
  return new Promise((ok, ko) => {
    const x = new XMLHttpRequest()
    x.open('POST', '/api/lavori')
    x.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total)
    x.onload = () => {
      let j = {}
      try { j = JSON.parse(x.responseText) } catch (e) { /* vuoto */ }
      if (x.status >= 200 && x.status < 300) ok(j)
      else ko(new Error(typeof j.detail === 'string' ? j.detail : x.statusText))
    }
    x.onerror = () => ko(new Error('Rete'))
    x.send(form)
  })
}

/** Termini come etichette eliminabili; Invio o virgola ne aggiunge uno. */
function Tag({ voci, onTogli, classe = '' }) {
  return voci.map((v) => (
    <span key={v} className={`tag ${classe}`}>{v}<button type="button" onClick={() => onTogli(v)} aria-label={`✕ ${v}`}>✕</button></span>
  ))
}

export default function Nuovo({ profili }) {
  const { t, lingua } = useT()
  const [file, setFile] = useState(null)
  const [url, setUrl] = useState('')
  const [profilo, setProfilo] = useState(profili.default)
  const [corsi, setCorsi] = useState([])
  const [imp, setImp] = useState(null)
  const [c, setC] = useState({ titolo: '', corso_id: '', lingua: lingua, lingua_prodotti: 'auto', parte_a: '', parte_b: '' })
  const [extra, setExtra] = useState([])
  const [scrivi, setScrivi] = useState('')
  const [voci, setVoci] = useState(false)
  const [errore, setErrore] = useState('')
  const [progress, setProgress] = useState(null)
  const [sopra, setSopra] = useState(false)
  const inputRef = useRef()

  const caricaCorsi = () => api.get('/api/corsi').then((cs) => { setCorsi(cs); return cs })
  useEffect(() => {
    caricaCorsi().then((cs) => {
      const ultimo = (() => { try { return localStorage.getItem('sbob.corso') } catch (e) { return null } })()
      if (ultimo && cs.some((x) => String(x.id) === ultimo)) setC((v) => ({ ...v, corso_id: ultimo }))
    })
    api.get('/api/impostazioni').then(setImp)
    api.get('/api/stato').then((s) => setImp((i) => ({ ...(i || {}), finti: s.motori === 'fake' })))
  }, [])
  const prof = profili.profili.find((p) => p.id === profilo)
  const tokenOk = !!imp && (imp.hf_token_impostato || imp.finti)
  useEffect(() => { setVoci(!!prof?.voci_default && tokenOk) }, [profilo, tokenOk])

  const corso = corsi.find((x) => String(x.id) === c.corso_id)
  const delCorso = termini(corso?.vocabolario)
  const globali = termini(imp?.vocabolario_globale)
  const sorgenteOk = !!file || /^https?:\/\/\S+$/i.test(url.trim())
  const set = (k) => (e) => setC({ ...c, [k]: e.target.value })
  const scegli = (f) => { if (f) { setFile(f); setUrl('') } }

  function aggiungi(v) {
    const nuovi = termini(v).filter((x) => !extra.some((e) => e.toLowerCase() === x.toLowerCase()))
    if (nuovi.length) setExtra([...extra, ...nuovi])
    setScrivi('')
  }
  async function togliDalCorso(v) {
    await api.put(`/api/corsi/${corso.id}`, { nome: corso.nome, vocabolario: delCorso.filter((x) => x !== v).join('\n') })
    caricaCorsi()
  }
  async function togliGlobale(v) {
    setImp({ ...imp, ...(await api.put('/api/impostazioni', { vocabolario_globale: globali.filter((x) => x !== v).join('\n') })) })
  }

  async function avvia() {
    setErrore('')
    const f = new FormData()
    if (file) f.append('file', file)
    else f.append('url', url.trim())
    const tutti = [...extra, ...termini(scrivi)]
    for (const [k, v] of Object.entries({ profilo, titolo: c.titolo, corso_id: c.corso_id, lingua: c.lingua,
      lingua_prodotti: c.lingua_prodotti, voci_attive: voci ? '1' : '0', termini_extra: tutti.join('\n') })) f.append(k, v)
    if (prof?.parti) f.append('parti', JSON.stringify([c.parte_a, c.parte_b]))
    try { localStorage.setItem('sbob.corso', c.corso_id) } catch (e) { /* ignora */ }
    setProgress(0)
    try {
      const l = await invia(f, setProgress)
      window.location.hash = `#/lavoro/${l.id}`
    } catch (e) {
      setErrore(e.message)
      setProgress(null)
    }
  }

  return (
    <>
      <div className="top"><b>{t('nuova_reg')}</b></div>
      <div className="pagina stretta nuovo">
        <div
          className={`drop ${sopra ? 'sopra' : ''} ${file ? 'pieno' : ''}`}
          onClick={() => !file && inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setSopra(true) }}
          onDragLeave={() => setSopra(false)}
          onDrop={(e) => { e.preventDefault(); setSopra(false); scegli(e.dataTransfer.files[0]) }}
        >
          {file ? (
            <div className="file-scelto">
              <span className="icona-file">♪</span>
              <div><strong>{file.name}</strong><small>{(file.size / 1048576).toFixed(1)} MB</small></div>
              <button className="btn piccolo" onClick={(e) => { e.stopPropagation(); setFile(null) }}>{t('cambia')}</button>
            </div>
          ) : (
            <>
              <span className="freccia">↑</span>
              <span>{t('trascina')}</span>
            </>
          )}
          <input ref={inputRef} type="file" hidden accept="audio/*,video/*,.m4a,.mp3,.wav,.mp4,.mov,.mkv,.webm,.ogg,.opus,.flac,.amr,.3gp,.caf"
            onChange={(e) => scegli(e.target.files[0])} />
        </div>
        {!file && (
          <div className="campo url">
            <input type="url" placeholder={`🔗  ${t('oppure_url')}`} value={url} onChange={(e) => setUrl(e.target.value)} />
            {url && <small>{t('url_diritti')}</small>}
          </div>
        )}

        <div className="etichetta">{t('profilo')}</div>
        <div className="scelta-profili" role="radiogroup">
          {profili.profili.map((p) => (
            <button key={p.id} role="radio" aria-checked={p.id === profilo} className={p.id === profilo ? 'on' : ''} onClick={() => setProfilo(p.id)}>
              <span className="icona">{p.icona}</span>
              <b>{p.label[lingua].split(' / ')[0]}</b>
              <small>{p.prodotto[lingua]}</small>
            </button>
          ))}
        </div>
        <p className="tenue piccolo">{prof.descrizione[lingua]}</p>

        <div className="griglia">
          <label className="campo"><span>{t('corso')}</span>
            <select value={c.corso_id} onChange={set('corso_id')}>
              <option value="">{t('nessuno')}</option>
              {corsi.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
            </select></label>
          <label className="campo"><span>{t('titolo')}</span>
            <input value={c.titolo} onChange={set('titolo')} placeholder={t('titolo_auto')} /></label>
        </div>

        <div className="campo termini">
          <span>{t('termini_attesi')}</span>
          <div className="tag-box" onClick={(e) => e.currentTarget.querySelector('input')?.focus()}>
            <Tag voci={delCorso} onTogli={togliDalCorso} classe="tag-corso" />
            <Tag voci={globali} onTogli={togliGlobale} classe="tag-globale" />
            <Tag voci={extra} onTogli={(v) => setExtra(extra.filter((x) => x !== v))} />
            <input value={scrivi} placeholder={t('termini_ph')} onChange={(e) => setScrivi(e.target.value)}
              onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ',') && scrivi.trim()) { e.preventDefault(); aggiungi(scrivi) }
                if (e.key === 'Backspace' && !scrivi && extra.length) setExtra(extra.slice(0, -1))
              }}
              onBlur={() => scrivi.trim() && aggiungi(scrivi)} />
          </div>
          <small>
            {delCorso.length > 0 && <><span className="tag-legenda tag-corso" /> {t('leg_corso')} {corso.nome}. </>}
            {globali.length > 0 && <><span className="tag-legenda tag-globale" /> {t('leg_globali')}. </>}
            {t('leg_extra')}
          </small>
        </div>

        {prof?.parti && (
          <div className="campo"><span>{t('parti')}</span>
            <div className="due">
              <input value={c.parte_a} onChange={set('parte_a')} placeholder={t('parte_a')} />
              <input value={c.parte_b} onChange={set('parte_b')} placeholder={t('parte_b')} />
            </div></div>
        )}

        <div className={`voci-box ${tokenOk ? '' : 'bloccato'}`}>
          <label className="spunta">
            <input type="checkbox" checked={voci} disabled={!tokenOk} onChange={(e) => setVoci(e.target.checked)} />
            <span>{t('voci_sep')}
              {tokenOk ? <small>{t('voci_nota_ok')}</small>
                : <small>{t('voci_senza_token')} <a href="#/impostazioni">{t('impostazioni')}</a>.</small>}
            </span>
          </label>
        </div>

        <details className="avanzate">
          <summary>{t('opzioni')}</summary>
          <div className="griglia">
            <label className="campo"><span>{t('lingua_reg')}</span>
              <select value={c.lingua} onChange={set('lingua')}>
                <option value="auto">{t('auto')}</option>
                {LINGUE.map((l) => <option key={l} value={l}>{NOMI_LINGUE[l]}</option>)}
              </select></label>
            <label className="campo"><span>{t('lingua_prod')}</span>
              <select value={c.lingua_prodotti} onChange={set('lingua_prodotti')}>
                <option value="auto">{t('come_reg')}</option>
                {LINGUE.map((l) => <option key={l} value={l}>{NOMI_LINGUE[l]}</option>)}
              </select></label>
          </div>
        </details>

        {progress !== null && <div className="progress"><div style={{ width: `${Math.round(progress * 100)}%` }} /><span>{t('caricamento')} {Math.round(progress * 100)}%</span></div>}
        {errore && <p className="errore">{errore}</p>}
        <div className="azioni">
          <a className="btn" href="#/">{t('annulla')}</a>
          <button className="btn primario" disabled={!sorgenteOk || progress !== null} onClick={avvia}>{t('avvia_lavoro')}</button>
        </div>
      </div>
    </>
  )
}
