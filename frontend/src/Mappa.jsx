import { useEffect, useRef, useState } from 'react'
import { Transformer } from 'markmap-lib'
import { hierarchy, tree, select, zoom as d3zoom, zoomIdentity, linkHorizontal, linkRadial } from 'd3'
import { useT } from './i18n.js'

const trasformatore = new Transformer([]) // nessun plugin: niente risorse esterne
const COLORI = ['#4e79a7', '#f28e2b', '#59a14f', '#e15759', '#b07aa1', '#76b7b2', '#edc948', '#ff9da7', '#9c755f']
const RIGA = 17 // altezza di una riga di testo (layout lineare)
const COLONNA = 270 // distanza tra i livelli (lineare)
const ANELLO = 240 // distanza tra i livelli (radiale)
const DURATA = 380 // animazione di apertura/chiusura (ms)
const SCALA_MIN = 0.45 // "Adatta" non scende sotto: il testo diventerebbe illeggibile

const STILE_EXPORT = `.mm-t{font:13px "Atkinson Hyperlegible Next",-apple-system,Helvetica,Arial,sans-serif;fill:#222}
.mm-radice .mm-t{font-size:16px;font-weight:700}.mm-pill{fill:#fff;stroke-width:1.5}.mm-radice .mm-pill{stroke:#888}
.mm-link{fill:none;stroke-opacity:.55;stroke-width:1.5}.mm-foglia .mm-t{paint-order:stroke;stroke:#fff;stroke-width:3px}
.mm-badge{fill:#fff;stroke-width:1.5}.mm-badge-t{font:600 10px sans-serif;fill:#444}`

const testoDa = (html) => new DOMParser().parseFromString(html || '', 'text/html').body.textContent.trim()

function avvolgi(s, max) {
  const righe = []
  let r = ''
  for (const p of s.split(/\s+/)) {
    if (r && (r + ' ' + p).length > max) { righe.push(r); r = p } else r = r ? r + ' ' + p : p
  }
  if (r) righe.push(r)
  if (righe.length > 4) { righe.length = 4; righe[3] += '…' }
  return righe
}

let progressivo = 0
function annota(n, padre = null, colore = null) {
  n.uid = ++progressivo
  n.testo = testoDa(n.content) || '—'
  n.padre = padre
  n.colore = colore
  ;(n.children || []).forEach((c, i) => annota(c, n, colore ?? COLORI[i % COLORI.length]))
}

function piega(nodo, livelloMax, livello = 0) {
  nodo.payload = { ...(nodo.payload || {}), fold: livelloMax !== null && livello >= livelloMax && nodo.children?.length ? 1 : 0 }
  nodo.children?.forEach((c) => piega(c, livelloMax, livello + 1))
}

function* tutti(n) { yield n; for (const c of n.children || []) yield* tutti(c) }

function scarica(nome, blob) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = nome
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 2000)
}

const leggiModo = () => { try { return localStorage.getItem('sbob-mappa-modo') || 'lineare' } catch { return 'lineare' } }

export default function Mappa({ testo, titolo, azioni }) {
  const { t } = useT()
  const svgRef = useRef(), gRef = useRef(), boxRef = useRef(), cercaRef = useRef()
  const zRef = useRef(), posRef = useRef(new Map()), clicRef = useRef()
  const dopo = useRef(null) // dopo il prossimo disegno: 'adatta' oppure il nodo da centrare
  const [radice, setRadice] = useState(null)
  const [focus, setFocus] = useState(null)
  const [modo, setModo] = useState(leggiModo)
  const [giro, setGiro] = useState(0) // ridisegna dopo apri/chiudi
  const [q, setQ] = useState('')
  const [trovati, setTrovati] = useState([])
  const [idx, setIdx] = useState(0)
  const [evid, setEvid] = useState(null)
  const ora = useRef({})
  ora.current = { focus, modo } // per i listener registrati una volta sola

  useEffect(() => {
    const z = d3zoom().scaleExtent([0.1, 3]).on('zoom', (e) => select(gRef.current).attr('transform', e.transform))
    select(svgRef.current).call(z).on('dblclick.zoom', null)
    zRef.current = z
    const f = () => setTimeout(adatta, 100)
    document.addEventListener('fullscreenchange', f)
    return () => document.removeEventListener('fullscreenchange', f)
  }, [])

  useEffect(() => {
    const { root } = trasformatore.transform(testo || '# —')
    annota(root)
    piega(root, 2)
    select(gRef.current).selectAll('*').remove()
    posRef.current = new Map()
    dopo.current = 'adatta'
    setRadice(root); setFocus(root); setQ(''); setEvid(null)
  }, [testo])

  useEffect(disegna, [focus, modo, giro, evid])

  useEffect(() => {
    if (!radice) return
    const s = q.trim().toLowerCase()
    const r = s.length < 2 ? [] : [...tutti(radice)].filter((n) => n.testo.toLowerCase().includes(s))
    setTrovati(r); setIdx(0)
    if (r.length) vaiA(r[0]); else setEvid(null)
  }, [q, radice])

  // ── disegno ────────────────────────────────────────────────
  function disegna() {
    if (!focus) return
    const g = select(gRef.current)
    const radiale = modo === 'radiale'
    const h = hierarchy(focus, (n) => (n.payload?.fold ? null : n.children))
    h.each((d) => {
      d.chiuso = !!(d.data.payload?.fold && d.data.children?.length)
      d.foglia = radiale && d.depth > 0 && !d.children && !d.chiuso
      d.righe = avvolgi(d.data.testo, d.depth === 0 ? 24 : d.foglia ? 34 : 28)
    })
    if (radiale) {
      const n = h.leaves().length
      tree().size([2 * Math.PI * (n > 1 ? n / (n + 1) : 1), Math.max(1, h.height) * ANELLO])
        .separation((a, b) => ((a.righe.length + b.righe.length) / 2) * (a.parent === b.parent ? 1 : 1.5) / Math.max(1, a.depth))(h)
      h.each((d) => { const a = d.x - Math.PI / 2; d.px = d.y * Math.cos(a); d.py = d.y * Math.sin(a) })
    } else {
      tree().nodeSize([RIGA, COLONNA])
        .separation((a, b) => (a.righe.length + b.righe.length) / 2 + (a.parent === b.parent ? 0.8 : 1.4))(h)
      h.each((d) => { d.px = d.y; d.py = d.x })
    }
    h.each((d) => { d.rot = d.foglia ? (d.x * 180) / Math.PI - 90 : 0 })
    const prima = posRef.current
    const ora_ = new Map(h.descendants().map((d) => [d.data, d]))
    posRef.current = ora_
    // da dove entra un nodo (posizione precedente dell'antenato visibile) e dove esce
    const origine = (n) => { for (let x = n; x; x = x.padre) if (prima.has(x)) return prima.get(x); return ora_.get(n) }
    const destino = (n) => { for (let x = n; x; x = x.padre) if (ora_.has(x)) return ora_.get(x); return prima.get(n) }
    const pr = (a, r) => [r * Math.cos(a - Math.PI / 2), r * Math.sin(a - Math.PI / 2)]
    const lk = ({ source: s, target: t }) => {
      if (radiale) {
        const m = (s.y + t.y) / 2, [x1, y1] = pr(s.x, m), [x2, y2] = pr(t.x, m)
        return `M${s.px},${s.py}C${x1},${y1} ${x2},${y2} ${t.px},${t.py}`
      }
      const m = (s.px + t.px) / 2
      return `M${s.px},${s.py}C${m},${s.py} ${m},${t.py} ${t.px},${t.py}`
    }
    const punto = (o) => (o ? `M${o.px},${o.py}C${o.px},${o.py} ${o.px},${o.py} ${o.px},${o.py}` : null)
    const tf = (p, rot) => `translate(${p.px},${p.py}) rotate(${rot})`
    const tr = () => g.transition().duration(DURATA)

    const strato = (c) => (g.select('.' + c).empty() ? g.append('g').attr('class', c) : g.select('.' + c))
    const sl = strato('mm-strato-link'), sn = strato('mm-strato-nodi')

    sl.selectAll('path').data(h.links(), (l) => l.target.data.uid).join(
      (en) => en.append('path').attr('class', 'mm-link').attr('d', (l) => punto(origine(l.target.data))),
      (up) => up,
      (ex) => ex.transition(tr()).attr('d', (l) => punto(destino(l.target.data))).remove(),
    ).attr('stroke', (l) => l.target.data.colore).transition(tr()).attr('d', lk)

    sn.selectAll('g.mm-nodo').data(h.descendants(), (d) => d.data.uid).join(
      (en) => en.append('g').attr('opacity', 0)
        .attr('transform', (d) => tf(origine(d.data), d.rot)),
      (up) => up,
      (ex) => ex.transition(tr()).attr('opacity', 0)
        .attr('transform', (d) => tf(destino(d.data), d.rot)).remove(),
    )
      .attr('class', (d) => `mm-nodo${d.depth === 0 ? ' mm-radice' : ''}${d.foglia ? ' mm-foglia' : ''}${d.data === evid ? ' mm-trovato' : ''}`)
      .on('click', (e, d) => clic(d.data))
      .on('dblclick', (e, d) => isola(d.data))
      .each(function (d) {
        const n = select(this)
        n.selectAll('*').remove()
        n.append('title').text(d.data.testo)
        const tx = n.append('text').attr('class', 'mm-t')
        let x = 0
        if (d.foglia) {
          const sx = d.x >= Math.PI // metà sinistra: testo capovolto per restare leggibile
          x = sx ? -8 : 8
          n.insert('circle', 'text').attr('r', 3).attr('fill', d.data.colore)
          tx.attr('transform', sx ? 'rotate(180)' : null).attr('text-anchor', sx ? 'end' : 'start')
        } else tx.attr('text-anchor', 'middle')
        const lh = d.depth === 0 ? 19 : 15.5
        const y0 = -((d.righe.length - 1) * lh) / 2
        d.righe.forEach((r, i) => tx.append('tspan').attr('x', x).attr('y', y0 + i * lh).attr('dy', '0.35em').text(r))
        if (d.foglia) return
        const b = tx.node().getBBox()
        const pill = n.insert('rect', 'text').attr('class', 'mm-pill').attr('rx', 8)
          .attr('x', b.x - 10).attr('y', b.y - 5).attr('width', b.width + 20).attr('height', b.height + 10)
        if (d.data.colore) pill.attr('stroke', d.data.colore)
        if (d.chiuso) {
          const cx = b.x + b.width + 10
          n.append('circle').attr('class', 'mm-badge').attr('cx', cx).attr('r', 9).attr('stroke', d.data.colore || '#888')
          n.append('text').attr('class', 'mm-badge-t').attr('x', cx).attr('dy', '0.35em').attr('text-anchor', 'middle')
            .text(d.data.children.length)
        }
      })
      .transition(tr()).attr('opacity', 1).attr('transform', (d) => tf(d, d.rot))

    const a = dopo.current
    dopo.current = null
    if (a === 'adatta') setTimeout(adatta, DURATA + 20) // a disegno assestato
    else if (a) centra(a)
  }

  // ── navigazione ────────────────────────────────────────────
  const svgSel = () => select(svgRef.current).transition().duration(300)
  function adatta() {
    const svg = svgRef.current, g = gRef.current
    if (!svg || !g) return
    const b = g.getBBox()
    const { width: W, height: H } = svg.getBoundingClientRect()
    if (!b.width || !W) return
    let k = Math.min(W / (b.width + 60), H / (b.height + 60), 1.2)
    let cx = b.x + b.width / 2, cy = b.y + b.height / 2
    if (k < SCALA_MIN) { // troppo grande: leggibile, partendo dal nodo centrale
      k = SCALA_MIN
      const r = posRef.current.get(ora.current.focus)
      if (r) { cy = r.py; cx = ora.current.modo === 'radiale' ? r.px : b.x + (W / 2 - 40) / k }
    }
    svgSel().call(zRef.current.transform, zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-cx, -cy))
  }
  function centra(nodo) {
    const r = posRef.current.get(nodo)
    if (r) svgSel().call(zRef.current.translateTo, r.px, r.py)
  }
  const zoom = (f) => select(svgRef.current).transition().duration(200).call(zRef.current.scaleBy, f)

  function clic(nodo) { // clic singolo: apre/chiude e centra; il doppio clic isola il ramo
    clearTimeout(clicRef.current)
    clicRef.current = setTimeout(() => {
      if (nodo.children?.length) {
        nodo.payload = { ...nodo.payload, fold: nodo.payload?.fold ? 0 : 1 }
        dopo.current = nodo
        setGiro((x) => x + 1)
      } else centra(nodo)
    }, 220)
  }
  function isola(nodo) {
    clearTimeout(clicRef.current)
    if (nodo === focus || !nodo.children?.length) return
    nodo.payload = { ...nodo.payload, fold: 0 }
    dopo.current = 'adatta'
    setFocus(nodo)
  }
  function vaiA(n) {
    for (let p = n.padre; p; p = p.padre) p.payload = { ...p.payload, fold: 0 }
    let dentro = false
    for (let x = n; x; x = x.padre) if (x === focus) dentro = true
    dopo.current = n
    setEvid(n); setGiro((x) => x + 1)
    if (!dentro) setFocus(radice)
  }
  function scorri(passo) {
    if (!trovati.length) return
    const i = (idx + passo + trovati.length) % trovati.length
    setIdx(i); vaiA(trovati[i])
  }
  function espandi(tutto) {
    piega(focus, tutto ? null : 1)
    dopo.current = 'adatta'
    setGiro((x) => x + 1)
  }
  function cambiaModo(m) {
    try { localStorage.setItem('sbob-mappa-modo', m) } catch { /* niente */ }
    dopo.current = 'adatta'
    setModo(m)
  }
  const schermoIntero = () => (document.fullscreenElement ? document.exitFullscreen() : boxRef.current.requestFullscreen())

  function tasto(e) {
    if (e.target.tagName === 'INPUT') {
      if (e.key === 'Enter') { e.preventDefault(); scorri(e.shiftKey ? -1 : 1) }
      if (e.key === 'Escape') { setQ(''); boxRef.current.focus() }
      return
    }
    const k = svgRef.current.__zoom?.k || 1, p = 90 / k
    const sposta = { ArrowLeft: [p, 0], ArrowRight: [-p, 0], ArrowUp: [0, p], ArrowDown: [0, -p] }[e.key]
    if (sposta) select(svgRef.current).transition().duration(150).call(zRef.current.translateBy, ...sposta)
    else if (e.key === '+' || e.key === '=') zoom(1.25)
    else if (e.key === '-') zoom(0.8)
    else if (e.key === '0') adatta()
    else if (e.key === '/') cercaRef.current.focus()
    else if (e.key === 'Escape' && focus?.padre) { dopo.current = 'adatta'; setFocus(focus.padre) }
    else return
    e.preventDefault()
  }

  // ── export ─────────────────────────────────────────────────
  function svgTesto() {
    const clone = svgRef.current.cloneNode(true)
    const { width, height } = svgRef.current.getBoundingClientRect()
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    clone.setAttribute('width', width)
    clone.setAttribute('height', height)
    clone.querySelectorAll('title').forEach((x) => x.remove())
    const st = document.createElement('style')
    st.textContent = STILE_EXPORT
    clone.insertBefore(st, clone.firstChild)
    return { s: new XMLSerializer().serializeToString(clone), width, height }
  }
  if (azioni) {
    azioni.current = {
      svg: () => scarica(`${titolo} - mappa.svg`, new Blob([svgTesto().s], { type: 'image/svg+xml' })),
      png: () => {
        const { s, width, height } = svgTesto()
        const img = new Image()
        img.onload = () => {
          const c = document.createElement('canvas')
          c.width = width * 2; c.height = height * 2
          const ctx = c.getContext('2d')
          ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height)
          ctx.scale(2, 2); ctx.drawImage(img, 0, 0)
          c.toBlob((b) => scarica(`${titolo} - mappa.png`, b))
        }
        img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(s)
      },
    }
  }

  const via = []
  for (let x = focus; x; x = x.padre) via.unshift(x)

  return (
    <div className="mappa-box" ref={boxRef} tabIndex={0} onKeyDown={tasto}
      onMouseDown={(e) => { if (!e.target.closest('input,button')) boxRef.current.focus({ preventScroll: true }) }}>
      <svg ref={svgRef} className="mappa"><g ref={gRef} /></svg>
      <div className="mappa-sinistra">
        <div className="mappa-cerca">
          <input ref={cercaRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder={`⌕ ${t('cerca_mappa')}`} />
          {q.trim().length >= 2 && <>
            <span className="tenue">{trovati.length ? `${idx + 1}/${trovati.length}` : '0'}</span>
            <button onClick={() => scorri(-1)} disabled={!trovati.length}>↑</button>
            <button onClick={() => scorri(1)} disabled={!trovati.length}>↓</button>
          </>}
        </div>
        {via.length > 1 && (
          <div className="mappa-briciole">
            {via.map((n, i) => (
              <span key={i}>{i > 0 && ' › '}
                {i < via.length - 1
                  ? <button onClick={() => { dopo.current = 'adatta'; setFocus(n) }}>{i === 0 ? '⌂ ' : ''}{n.testo.slice(0, 32)}</button>
                  : <b>{n.testo.slice(0, 40)}</b>}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="mappa-strumenti">
        <button className={modo === 'lineare' ? 'on' : ''} onClick={() => cambiaModo('lineare')}>{t('lineare')}</button>
        <button className={modo === 'radiale' ? 'on' : ''} onClick={() => cambiaModo('radiale')}>{t('radiale')}</button>
        <span className="sep" />
        <button onClick={() => espandi(true)}>{t('espandi')}</button>
        <button onClick={() => espandi(false)}>{t('comprimi')}</button>
        <span className="sep" />
        <button onClick={() => zoom(0.8)} title="−">−</button>
        <button onClick={() => zoom(1.25)} title="+">+</button>
        <button onClick={adatta}>{t('adatta')}</button>
        <span className="sep" />
        <button onClick={schermoIntero} title={t('schermo_intero')}>⛶</button>
      </div>
      <p className="mappa-aiuto">{t('mappa_aiuto')}</p>
    </div>
  )
}
