import { marked } from 'marked'
import { secondiDa } from './api.js'

const RE_TS = /\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g

function sicuro(testo) {
  return testo.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export function conTimestamp(html) {
  return html.replace(RE_TS, (_, ts) => `<button class="ts" data-t="${secondiDa(ts)}">▶ ${ts}</button>`)
}

export function clicTimestamp(seek) {
  return (e) => {
    const b = e.target.closest('.ts')
    if (b) seek(Number(b.dataset.t))
  }
}

export default function Markdown({ testo, seek }) {
  const html = conTimestamp(marked.parse(sicuro(testo || '')))
  return <div className="md" onClick={clicTimestamp(seek)} dangerouslySetInnerHTML={{ __html: html }} />
}

export function Inline({ testo, seek }) {
  const html = conTimestamp(marked.parseInline(sicuro(testo || '')))
  return <span onClick={clicTimestamp(seek)} dangerouslySetInnerHTML={{ __html: html }} />
}
