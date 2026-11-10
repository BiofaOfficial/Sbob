import { useEffect, useState } from 'react'
import { api } from './api.js'
import { useT } from './i18n.js'
import { coloreCorso } from './App.jsx'

const conta = (v) => v.split(/[\n,;]+/).filter((x) => x.trim()).length

function Corso({ corso, onSalva, onElimina }) {
  const { t } = useT()
  const [aperto, setAperto] = useState(false)
  const [c, setC] = useState(corso)
  return (
    <li className={`corso-riga ${aperto ? 'aperto' : ''}`}>
      <div className="corso-testa">
        <span className="dot" style={{ background: coloreCorso(corso.id) }} />
        <a href={`#/?corso=${corso.id}`} className="corso-nome">{corso.nome}</a>
        <span className="tenue">{corso.n_lavori} {t('lavori')}</span>
        <span className="tenue">{conta(corso.vocabolario)} {t('termini_n')}</span>
        <button className="btn piccolo" onClick={() => setAperto(!aperto)}>{aperto ? t('chiudi') : t('modifica')}</button>
      </div>
      {aperto && (
        <div className="corso-corpo">
          <label className="campo"><span>{t('nome')}</span>
            <input value={c.nome} onChange={(e) => setC({ ...c, nome: e.target.value })} /></label>
          <label className="campo"><span>{t('vocabolario')}</span>
            <textarea rows="6" value={c.vocabolario} onChange={(e) => setC({ ...c, vocabolario: e.target.value })} />
            <small>{t('vocabolario_aiuto')}</small></label>
          <div className="azioni">
            <button className="link pericolo" onClick={() => window.confirm(t('conferma_corso')) && onElimina(corso.id)}>{t('elimina')}</button>
            <span className="spazio" />
            <button className="btn primario" onClick={async () => { await onSalva(c); setAperto(false) }}>{t('salva')}</button>
          </div>
        </div>
      )}
    </li>
  )
}

export default function Corsi() {
  const { t } = useT()
  const [corsi, setCorsi] = useState([])
  const [nome, setNome] = useState('')
  const [errore, setErrore] = useState('')
  const carica = () => api.get('/api/corsi').then(setCorsi)
  useEffect(() => { carica() }, [])
  const prova = (f) => async (...a) => { setErrore(''); try { await f(...a); await carica() } catch (e) { setErrore(e.message) } }
  const crea = prova(async () => { await api.post('/api/corsi', { nome: nome.trim(), vocabolario: '' }); setNome('') })
  return (
    <>
      <div className="top"><b>{t('corsi')}</b></div>
      <div className="pagina stretta">
        <p className="intro">{t('corsi_intro')}</p>
        <form className="nuovo-corso" onSubmit={(e) => { e.preventDefault(); nome.trim() && crea() }}>
          <input value={nome} placeholder={t('nuovo_corso_ph')} onChange={(e) => setNome(e.target.value)} />
          <button className="btn primario" disabled={!nome.trim()}>{t('crea_corso')}</button>
        </form>
        {errore && <p className="errore">{errore}</p>}
        <ul className="corsi-lista">
          {corsi.map((c) => <Corso key={c.id + c.nome + c.vocabolario} corso={c}
            onSalva={prova((x) => api.put(`/api/corsi/${c.id}`, { nome: x.nome, vocabolario: x.vocabolario }))}
            onElimina={prova((cid) => api.del(`/api/corsi/${cid}`))} />)}
        </ul>
      </div>
    </>
  )
}
