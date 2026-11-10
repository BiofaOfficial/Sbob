import { useContext, useEffect, useState } from 'react'
import { api } from './api.js'
import { LinguaCtx, useT } from './i18n.js'

function Spia({ ok, si, no }) {
  return <li className={ok ? 'ok' : 'ko'}>{ok ? '✓' : '✗'} {ok ? si : no}</li>
}

export default function Impostazioni() {
  const { t } = useT()
  const { lingua, setLingua } = useContext(LinguaCtx)
  const [imp, setImp] = useState(null)
  const [stato, setStato] = useState(null)
  const [token, setToken] = useState('')
  const [msg, setMsg] = useState('')
  useEffect(() => {
    api.get('/api/impostazioni').then(setImp)
    api.get('/api/stato').then(setStato)
  }, [])
  if (!imp) return <p className="centro">…</p>
  async function salva(e) {
    e.preventDefault()
    const corpo = { whisper_modello: imp.whisper_modello, llm_modello: imp.llm_modello, llm_ctx: Number(imp.llm_ctx), vocabolario_globale: imp.vocabolario_globale }
    if (token.trim()) corpo.hf_token = token.trim()
    setImp(await api.put('/api/impostazioni', corpo))
    setToken('')
    setStato(await api.get('/api/stato'))
    setMsg(t('salvato'))
    setTimeout(() => setMsg(''), 2000)
  }
  const set = (k) => (e) => setImp({ ...imp, [k]: e.target.value })
  return (
    <>
      <div className="top"><b>{t('impostazioni')}</b></div>
      <form className="pagina stretta impostazioni" onSubmit={salva}>
        <section>
          <h3>{t('sez_interfaccia')}</h3>
          <div className="griglia">
            <label className="campo"><span>{t('lingua_ui')}</span>
              <select value={lingua} onChange={(e) => setLingua(e.target.value)}>
                <option value="it">Italiano</option><option value="en">English</option>
              </select></label>
            <label className="campo"><span>{t('cartella_dati')}</span><input value={stato?.cartella_dati || ''} readOnly /></label>
          </div>
        </section>
        <section>
          <h3>{t('sez_modelli')}</h3>
          <div className="griglia">
            <label className="campo"><span>{t('modello_whisper')}</span><input value={imp.whisper_modello} onChange={set('whisper_modello')} /></label>
            <label className="campo"><span>{t('modello_llm')}</span><input value={imp.llm_modello} onChange={set('llm_modello')} /></label>
            <label className="campo"><span>{t('contesto_llm')}</span><input type="number" step="1024" value={imp.llm_ctx} onChange={set('llm_ctx')} /></label>
            <div className={`campo campo-token ${imp.hf_token_impostato ? '' : 'da-impostare'}`}>
              <span className="etichetta-token">
                {t('token')} <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noreferrer">Hugging Face</a> ({t('separazione_voci')})
                <details className="aiuto-token">
                  <summary aria-label={t('come_ottenerlo')}>?</summary>
                  <div className="popover">
                    <b>{t('come_ottenerlo')}</b>
                    <ol>
                      <li>{t('hf_1a')} <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noreferrer">Settings → Access Tokens</a> {t('hf_1b')}</li>
                      <li>{t('hf_2')} <a href="https://huggingface.co/pyannote/speaker-diarization-3.1" target="_blank" rel="noreferrer">speaker-diarization-3.1</a> {t('e')} <a href="https://huggingface.co/pyannote/segmentation-3.0" target="_blank" rel="noreferrer">segmentation-3.0</a>.</li>
                      <li>{t('hf_3')}</li>
                    </ol>
                  </div>
                </details>
              </span>
              <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)}
                placeholder={imp.hf_token_impostato ? t('token_sostituisci') : 'hf_…'} />
              {!imp.hf_token_impostato && <small className="avviso-token">{t('token_manca')}</small>}
            </div>
          </div>
        </section>
        <section>
          <h3>{t('sez_termini')}</h3>
          <label className="campo"><textarea rows="4" value={imp.vocabolario_globale || ''} onChange={set('vocabolario_globale')} />
            <small>{t('vocabolario_aiuto').split('.')[0]}.</small></label>
        </section>
        <div className="azioni">{msg && <span className="ok">{msg}</span>}<button className="btn primario">{t('salva')}</button></div>
        {stato && (
          <section>
            <h3>{t('sez_stato')} <small className="in-linea">{t('versione')} {stato.versione}</small></h3>
            {stato.motori === 'fake' && <p className="avviso">{t('motori_finti')}</p>}
            <ul className="spie">
              <Spia ok={stato.ffmpeg} si="ffmpeg" no="ffmpeg" />
              {stato.llm.raggiungibile !== undefined && <Spia ok={stato.llm.raggiungibile} si={t('ollama_ok')} no={t('ollama_ko')} />}
              {stato.llm.modello_presente !== undefined && <Spia ok={stato.llm.modello_presente} si={t('modello_ok')} no={t('modello_ko')} />}
              {stato.trascrittore.installato !== undefined && <Spia ok={stato.trascrittore.installato} si={t('whisper_ok')} no={t('whisper_ok')} />}
              {stato.separatore.installato !== undefined && <Spia ok={stato.separatore.installato && stato.separatore.token} si={t('voci_ok')} no={t('voci_ko')} />}
            </ul>
          </section>
        )}
      </form>
    </>
  )
}
