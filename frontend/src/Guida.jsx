import { useT } from './i18n.js'

// Guida in linea: una voce per argomento, in italiano e in inglese.
const GUIDA = {
  it: [
    ['Come funziona', `Sbob ascolta una registrazione e la trasforma in materiale di studio: **trascritto**, **dispensa**, **mappa mentale**, **flashcard**, **domande di autoverifica** e **glossario**.
Tutto avviene **su questo Mac**: le tue registrazioni non vengono mandate a nessun servizio esterno.
Ogni testo è scritto da un'intelligenza artificiale: **rileggilo sempre**, soprattutto prima di studiarci sopra per un esame.`],
    ['Prima di tutto: i corsi', `Vai su **Corsi** e crea un corso per ogni materia (per esempio «Analisi 1»).
Nel campo **Vocabolario** scrivi, uno per riga, i nomi propri e le sigle che il docente usa spesso: «Weierstrass», «Cauchy», «PDE»… Sbob li riconoscerà meglio nella trascrizione.
I corsi compaiono nella barra a sinistra: un clic mostra solo le lezioni di quel corso.`],
    ['Caricare una lezione', `Premi **＋ Nuova registrazione**.
1. **Trascina il file** (audio o video, anche quello registrato col telefono) oppure **incolla un link**, per esempio di YouTube. Usa i link solo per contenuti che hai il diritto di scaricare.
2. Scegli il **profilo**: per le lezioni lascia **Lezione**.
3. Scegli il **corso**.
4. Premi **Avvia**.
Le **opzioni avanzate** (lingua, termini in più, separazione delle voci) di solito non servono.`],
    ['Mentre lavora', `Sbob ti racconta a che punto è: estrae l'audio, trascrive, prende appunti blocco per blocco, poi scrive dispensa e prodotti di studio.
La fase più lunga è la **trascrizione**. Per un'ora di lezione servono in tutto circa **15-30 minuti**.
Puoi chiudere il browser: il lavoro continua e il Mac non va in stop finché non ha finito. Sbob resta acceso in sottofondo; per chiuderlo usa **Esci** in fondo alla barra a sinistra.
Puoi caricare più lezioni di fila: vengono elaborate una alla volta.`],
    ['Leggere i risultati', `Apri una lezione dallo storico. In alto trovi le sezioni:
- **Capitoli**: in breve, capitoli con timestamp e concetti chiave.
- **Dispensa**: il testo da studiare, discorsivo e continuo come una pubblicazione, senza minutaggio. Si crea su richiesta scegliendo **Sintetica** o **Approfondita**.
- **Mappa**: la mappa mentale, in vista **Lineare** o **Radiale**. Clic su un nodo per aprirlo o chiuderlo (e centrarlo); **doppio clic** per isolare quel ramo, **Esc** per tornare su; **Cerca nella mappa** trova e apre il nodo; frecce per spostarti, **+ − 0** per lo zoom, **⛶** per lo schermo intero.
- **Flashcard**: clicca la carta per girarla, frecce per scorrere.
- **Autoverifica**: prova a rispondere, poi **Mostra risposta**.
- **Glossario**: i termini della lezione.
- **Trascritto**: tutto il testo parlato.
I riquadri viola con l'orario (▶ 12:30) sono **cliccabili**: l'audio riparte da quel punto, così puoi riascoltare la spiegazione originale.`],
    ['Il player', `Il player in basso ha: play/pausa, **↺15** per tornare indietro di 15 secondi, la barra per spostarti e la **velocità** (1×, 1,25×, 1,5×, 2×).
Nel trascritto la riga che stai ascoltando si evidenzia da sola.`],
    ['Togliere parti dal trascritto', `A volte una registrazione contiene parti inutili: pause, chiacchiere prima della lezione, pubblicità in un video.
Nel **Trascritto** passa sopra una riga e premi **✕** per escluderla; tieni premuto **Maiusc** e clicca un'altra riga per escludere tutto l'intervallo. Premi **↺** per rimetterla.
Poi premi **Rigenera ora** nell'avviso in alto: dispensa e prodotti verranno riscritti senza quelle parti.`],
    ['Termini attesi', `Nel **Glossario** ogni termine ha il pulsante **＋ Termini attesi**: lo aggiunge al vocabolario del corso, così nelle lezioni successive Sbob lo scriverà giusto. Nel menu **Azioni Glossario** puoi aggiungerli tutti insieme.
Se la lezione non ha un corso, il termine finisce nei **termini attesi globali**, che trovi in **Impostazioni**.`],
    ['Azioni, Esporta e Dettagli', `- **Azioni Capitoli ▾** (e Azioni Mappa, Azioni Flashcard…), sopra il contenuto, agiscono **solo su quella sezione**: rigenerarla o scaricarla in PDF, Markdown, o per Anki.
- **Esporta ▾**, in alto a destra, scarica **tutta la lezione** in un unico PDF o Markdown.
- **ⓘ Dettagli** contiene titolo, corso, le fasi con i tempi, «Rigenera tutti i prodotti» ed **Elimina**.`],
    ['Flashcard in Anki', `Da **Azioni Flashcard → Scarica Anki (.txt)** ottieni un file da importare in Anki: in Anki scegli **File → Importa**, seleziona il file e conferma. Le carte hanno l'etichetta «sbob».`],
    ['Lo stato dei modelli', `Nella Home vedi i due «cervelli» di Sbob: il modello che **trascrive** e il modello che **scrive** (LLM).
- **WARM**: è già in memoria, parte subito.
- **COLD**: è installato ma non caricato; il primo lavoro impiegherà qualche secondo in più.
- **UP**: sta lavorando adesso.
- **DOWN**: non è disponibile. Di solito vuol dire che l'app **Ollama** non è aperta: aprila dalle Applicazioni e ricarica la pagina.
**Riscalda i modelli** li carica in anticipo: utile prima di caricare una lezione.`],
    ['Riunioni, interviste, confronti', `Oltre a **Lezione**, Sbob ha tre profili: **Riunione** (decisioni, azioni, punti aperti), **Intervista** (domande e risposte) e **Confronto a due parti**.
Questi usano la **separazione delle voci** (chi parla), che si attiva una volta sola in **Impostazioni** incollando un token gratuito di Hugging Face (serve accettare le condizioni dei modelli pyannote sul sito di Hugging Face).
Dopo l'elaborazione puoi dare un nome alle voci in **Dettagli**.`],
    ['Se qualcosa va storto', `- **Una fase è rossa**: apri **Dettagli**, leggi il messaggio e premi **Riprova**.
- **«Ollama non è raggiungibile»**: apri l'app Ollama e premi Riprova.
- **La pagina non si apre**: fai doppio clic su **Sbob** sulla Scrivania; se era già aperto, si apre solo il browser. Se ancora non va, il registro degli errori è in ~/Sbob/sbob.log.
- **La dispensa non c'entra nulla o è in un'altra lingua**: in Nuova registrazione → Opzioni avanzate imposta la lingua della registrazione, poi ricarica la lezione.
- **Il Mac è lento mentre Sbob lavora**: è normale, sta usando quasi tutta la memoria. Lascialo finire.`],
    ['Dove sono i miei file', `Tutto è nella cartella **Sbob** della tua cartella Inizio (~/Sbob): lo storico, le registrazioni e le impostazioni. Per fare un backup, o per spostare tutto su un altro Mac, copia quella cartella.`],
  ],
  en: [
    ['How it works', `Sbob listens to a recording and turns it into study material: **transcript**, **study notes**, **mind map**, **flashcards**, **self-assessment questions** and **glossary**.
Everything happens **on this Mac**: your recordings are not sent to any external service.
Every text is written by an AI: **always review it**, especially before studying for an exam.`],
    ['First: courses', `Go to **Courses** and create one course per subject (e.g. "Calculus 1").
In **Vocabulary** write, one per line, the names and acronyms your teacher uses often. Sbob will recognise them better.
Courses appear in the left bar: one click shows only that course's lectures.`],
    ['Uploading a lecture', `Press **＋ New recording**.
1. **Drop the file** (audio or video, including phone recordings) or **paste a link**, e.g. YouTube. Only use links for content you have the right to download.
2. Choose the **profile**: for lectures keep **Lecture**.
3. Choose the **course**.
4. Press **Start**.
**Advanced options** (language, extra terms, voice separation) are usually not needed.`],
    ['While it works', `Sbob tells you what it is doing: extracting audio, transcribing, taking notes block by block, then writing the study notes and products.
The longest step is **transcription**. An hour-long lecture takes about **15-30 minutes** in total.
You can close the browser: the job continues and the Mac does not sleep until it is done. Sbob keeps running in the background; to close it use **Quit** at the bottom of the left bar.
You can upload several lectures in a row: they are processed one at a time.`],
    ['Reading the results', `Open a lecture from the history. At the top you find the sections:
- **Chapters**: TL;DR, chapters with timestamps and key concepts.
- **Handout**: the text to study, continuous discursive prose like a publication, without timestamps. Created on request, choosing **Concise** or **In depth**.
- **Map**: the mind map, in **Linear** or **Radial** view. Click a node to open or close it (and center it); **double click** to isolate that branch, **Esc** to go back up; **Search the map** finds and opens the node; arrows to move, **+ − 0** to zoom, **⛶** for full screen.
- **Flashcards**: click the card to flip it, arrows to browse.
- **Self-test**: try to answer, then **Show answer**.
- **Glossary**: the lecture's terms.
- **Transcript**: all the spoken text.
The purple boxes with a time (▶ 12:30) are **clickable**: the audio plays from that point, so you can listen to the original explanation.`],
    ['The player', `The player at the bottom has play/pause, **↺15** to go back 15 seconds, the seek bar and the **speed** (1×, 1.25×, 1.5×, 2×).
In the transcript the line you are listening to is highlighted.`],
    ['Removing parts of the transcript', `Recordings sometimes contain useless parts: pauses, chat before the lecture, ads in a video.
In **Transcript** hover a line and press **✕** to exclude it; hold **Shift** and click another line to exclude the whole range. Press **↺** to restore it.
Then press **Regenerate now** in the banner: notes and products will be rewritten without those parts.`],
    ['Expected terms', `In the **Glossary** every term has a **＋ Expected terms** button: it adds the term to the course vocabulary so future lectures spell it right. The **Glossary actions** menu adds them all at once.
If the lecture has no course, the term goes to the **global expected terms** in **Settings**.`],
    ['Actions, Export and Details', `- **Chapters actions ▾** (and Map actions, Flashcards actions…), above the content, act **only on that section**: regenerate it or download it as PDF, Markdown or for Anki.
- **Export ▾**, top right, downloads **the whole lecture** as a single PDF or Markdown file.
- **ⓘ Details** holds title, course, the stages with their times, "Regenerate all products" and **Delete**.`],
    ['Flashcards in Anki', `**Flashcards actions → Download Anki (.txt)** gives you a file to import into Anki: choose **File → Import**, select the file and confirm. Cards are tagged "sbob".`],
    ['Model status', `The home page shows Sbob's two "brains": the model that **transcribes** and the model that **writes** (LLM).
- **WARM**: already in memory, starts immediately.
- **COLD**: installed but not loaded; the first job takes a few more seconds.
- **UP**: working right now.
- **DOWN**: not available. Usually the **Ollama** app is not open: open it from Applications and reload the page.
**Warm up models** loads them in advance: useful before uploading a lecture.`],
    ['Meetings, interviews, discussions', `Besides **Lecture**, Sbob has three profiles: **Meeting** (decisions, actions, open points), **Interview** (questions and answers) and **Two-party discussion**.
They use **voice separation** (who speaks), enabled once in **Settings** by pasting a free Hugging Face token (you need to accept the pyannote model terms on the Hugging Face website).
After processing you can name the voices in **Details**.`],
    ['If something goes wrong', `- **A stage is red**: open **Details**, read the message and press **Retry**.
- **"Ollama is not reachable"**: open the Ollama app and press Retry.
- **The page does not open**: double-click **Sbob** on the Desktop; if it was already running, only the browser opens. If it still fails, the error log is in ~/Sbob/sbob.log.
- **The notes are off-topic or in the wrong language**: in New recording → Advanced options set the recording language, then upload the lecture again.
- **The Mac is slow while Sbob works**: that is normal, it is using most of the memory. Let it finish.`],
    ['Where my files are', `Everything is in the **Sbob** folder of your home folder (~/Sbob): history, recordings and settings. To back up, or move everything to another Mac, copy that folder.`],
  ],
}

const ICONE = ['💡', '📚', '⬆️', '⏳', '📘', '🎧', '✂️', '🔤', '🧰', '🃏', '🧠', '👥', '🛟', '📁']
const PASSI = {
  it: [['Crea un corso', 'Una volta per materia, con i nomi e le sigle che il docente usa spesso.'],
    ['Carica la lezione', 'Trascina il file o incolla un link, scegli il corso e premi Avvia.'],
    ['Studia', 'Dispensa, mappa, flashcard e domande: i timestamp ti riportano al punto dell\'audio.']],
  en: [['Create a course', 'Once per subject, with the names and acronyms your teacher uses often.'],
    ['Upload the lecture', 'Drop the file or paste a link, choose the course and press Start.'],
    ['Study', 'Notes, map, flashcards and questions: timestamps take you back to the audio.']],
}
const PROBLEMI = 12 // indice della voce «Se qualcosa va storto»: diventa un elenco di domande apribili

function testo(s) {
  // grassetto minimo: **parola**
  return s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') ? <b key={i}>{p.slice(2, -2)}</b> : p))
}

function Blocco({ corpo }) {
  const out = []
  let lista = null
  corpo.split('\n').forEach((r) => {
    const m = r.match(/^(- |\d+\. )(.*)/)
    if (m) {
      if (!lista) { lista = { ordinata: /\d/.test(m[1]), voci: [] }; out.push(lista) }
      lista.voci.push(m[2])
    } else {
      lista = null
      out.push(r)
    }
  })
  return out.map((x, i) => typeof x === 'string'
    ? <p key={i}>{testo(x)}</p>
    : x.ordinata ? <ol key={i}>{x.voci.map((v, k) => <li key={k}>{testo(v)}</li>)}</ol>
      : <ul key={i}>{x.voci.map((v, k) => <li key={k}>{testo(v)}</li>)}</ul>)
}

function Problemi({ corpo }) {
  return (
    <div className="faq">
      {corpo.split('\n').filter((r) => r.startsWith('- ')).map((r, i) => {
        const [domanda, ...resto] = r.slice(2).split(/(?<=\*\*):\s*/)
        return (
          <details key={i}>
            <summary>{testo(domanda)}</summary>
            <p>{testo(resto.join(': ').replace(/^./, (c) => c.toUpperCase()))}</p>
          </details>
        )
      })}
    </div>
  )
}

export default function Guida() {
  const { t, lingua } = useT()
  const voci = GUIDA[lingua] || GUIDA.it
  const passi = PASSI[lingua] || PASSI.it
  return (
    <>
      <div className="top"><b>{t('guida')}</b></div>
      <div className="pagina guida">
        <header className="guida-eroe">
          <div>
            <h1>{lingua === 'it' ? 'Sbob in 3 passi' : 'Sbob in 3 steps'}</h1>
            <p>{testo(voci[0][1].split('\n')[0])}</p>
          </div>
        </header>
        <div className="passi-guida">
          {passi.map(([titolo, corpo], i) => (
            <div key={i} className="passo"><span className="numero">{i + 1}</span><b>{titolo}</b><p>{corpo}</p></div>
          ))}
        </div>
        <div className="schede-guida">
          {voci.map(([titolo, corpo], i) => i === 0 ? null : (
            <section key={i} className={`scheda-guida ${i === PROBLEMI ? 'larga' : ''}`}>
              <h2>{titolo}</h2>
              {i === PROBLEMI ? <Problemi corpo={corpo} /> : <Blocco corpo={corpo} />}
            </section>
          ))}
        </div>
        <p className="nota-guida">{testo(voci[0][1].split('\n').slice(1).join(' '))}</p>
      </div>
    </>
  )
}
