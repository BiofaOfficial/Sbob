import { useEffect, useState } from 'react'
import { LinguaCtx, linguaIniziale, useT } from './i18n.js'
import { api } from './api.js'
import Home from './Home.jsx'
import Nuovo from './Nuovo.jsx'
import Dettaglio from './Dettaglio.jsx'
import Corsi from './Corsi.jsx'
import Impostazioni from './Impostazioni.jsx'
import Guida from './Guida.jsx'

const COLORI = ['#8b7cf6', '#4cc38a', '#e5a14b', '#5b8def', '#e5674b', '#c66bd6', '#3fb8c4']
export const coloreCorso = (id) => COLORI[(Number(id) || 0) % COLORI.length]

function usaHash() {
  const [h, setH] = useState(window.location.hash || '#/')
  useEffect(() => {
    const f = () => setH(window.location.hash || '#/')
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  return h
}

function Barra({ h, stato }) {
  const { t } = useT()
  const [corsi, setCorsi] = useState([])
  const [attivi, setAttivi] = useState(0)
  useEffect(() => {
    let vivo = true
    const carica = () => {
      api.get('/api/corsi').then((c) => vivo && setCorsi(c)).catch(() => {})
      api.get('/api/lavori?stato=attivi').then((l) => vivo && setAttivi(l.length)).catch(() => {})
    }
    carica()
    const id = setInterval(carica, 5000)
    return () => { vivo = false; clearInterval(id) }
  }, [h])
  const on = (x) => (h === x ? 'voce on' : 'voce')
  return (
    <aside className="barra">
      <a href="#/" className="logo" aria-label="Sbob"><svg viewBox="0 0 20 20" aria-hidden="true"><rect x="2" y="7" width="3" height="6" rx="1.5" /><rect x="8.5" y="3" width="3" height="14" rx="1.5" /><rect x="15" y="6" width="3" height="8" rx="1.5" /></svg>sbob</a>
      <a href="#/nuovo" className="btn primario pieno">＋ {t('nuova_reg')}</a>
      <nav>
        <a href="#/" className={h === '#/' || h === '#' ? 'voce on' : 'voce'}>{t('tutti_lavori')}</a>
        <a href="#/?stato=attivi" className={on('#/?stato=attivi')}>{t('attivi')}{attivi > 0 && <span className="conta">{attivi}</span>}</a>
        <div className="sez"><span>{t('corsi')}</span><a href="#/corsi" title={t('nuovo_corso')}>＋</a></div>
        {corsi.map((c) => (
          <a key={c.id} href={`#/?corso=${c.id}`} className={on(`#/?corso=${c.id}`)}>
            <span className="dot" style={{ background: coloreCorso(c.id) }} />{c.nome}
          </a>
        ))}
      </nav>
      <div className="spazio" />
      {stato?.motori === 'fake' && <div className="avviso">{t('motori_finti')}</div>}
      <a href="#/guida" className={on('#/guida')}>? {t('guida')}</a>
      <a href="#/corsi" className={on('#/corsi')}>☰ {t('corsi')}</a>
      <a href="#/impostazioni" className={on('#/impostazioni')}>⚙ {t('impostazioni')}</a>
      <button className="voce esci" onClick={async () => {
        if (!window.confirm(attivi > 0 ? t('esci_conferma_attivi') : t('esci_conferma'))) return
        await api.post('/api/esci').catch(() => {})
        document.body.innerHTML = `<div class="chiuso"><b>${t('chiuso_titolo')}</b><p>${t('chiuso_testo')}</p></div>`
      }}>⏻ {t('esci')}</button>
    </aside>
  )
}

export default function App() {
  const [lingua, setLinguaStato] = useState(linguaIniziale())
  const [profili, setProfili] = useState(null)
  const [stato, setStato] = useState(null)
  const h = usaHash()
  const setLingua = (l) => {
    setLinguaStato(l)
    try { localStorage.setItem('sbob.lingua', l) } catch (e) { /* ignora */ }
    api.put('/api/impostazioni', { lingua_ui: l }).catch(() => {})
  }
  useEffect(() => {
    api.get('/api/profili').then(setProfili)
    api.get('/api/stato').then(setStato).catch(() => {})
    api.get('/api/impostazioni').then((i) => {
      let salvata = null
      try { salvata = localStorage.getItem('sbob.lingua') } catch (e) { /* ignora */ }
      if (!salvata && (i.lingua_ui === 'it' || i.lingua_ui === 'en')) setLinguaStato(i.lingua_ui)
    }).catch(() => {})
  }, [])
  useEffect(() => { document.documentElement.lang = lingua }, [lingua])

  let pagina
  const m = h.match(/^#\/lavoro\/([\w-]+)/)
  if (!profili) pagina = <p className="centro">…</p>
  else if (h.startsWith('#/nuovo')) pagina = <Nuovo profili={profili} />
  else if (m) pagina = <Dettaglio id={m[1]} profili={profili} />
  else if (h.startsWith('#/corsi')) pagina = <Corsi />
  else if (h.startsWith('#/impostazioni')) pagina = <Impostazioni />
  else if (h.startsWith('#/guida')) pagina = <Guida />
  else pagina = <Home profili={profili} h={h} />

  return (
    <LinguaCtx.Provider value={{ lingua, setLingua }}>
      <div className="app">
        <Barra h={h} stato={stato} />
        <main key={m ? 'dettaglio' : h.split('?')[0]}>{pagina}</main>
      </div>
    </LinguaCtx.Provider>
  )
}
