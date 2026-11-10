"""Registry dei profili (unica fonte di verità) e prompt IT/EN.

Generico, bilingue, senza squadre.
NB: prompt costruiti per concatenazione, non str.format(): il trascritto può
contenere `{` e `}`.
"""
from __future__ import annotations

PROFILO_DEFAULT = "lezione"

PROFILI: dict[str, dict] = {
    "lezione": {
        "icona": "🎓", "voci_default": False, "studio_auto": True, "parti": False,
        "label": {"it": "Lezione / Video / Webinar", "en": "Lecture / Video / Webinar"},
        "prodotto": {"it": "Capitoli", "en": "Chapters"},
        "descrizione": {"it": "In breve, capitoli con timestamp, concetti chiave",
                        "en": "TL;DR, chapters with timestamps, key concepts"},
    },
    "riunione": {
        "icona": "👥", "voci_default": True, "studio_auto": False, "parti": False,
        "label": {"it": "Riunione / Call", "en": "Meeting / Call"},
        "prodotto": {"it": "Resoconto", "en": "Minutes"},
        "descrizione": {"it": "Decisioni, azioni (chi → cosa), punti aperti",
                        "en": "Decisions, action items (who → what), open points"},
    },
    "intervista": {
        "icona": "🎙️", "voci_default": True, "studio_auto": False, "parti": False,
        "label": {"it": "Intervista / Podcast", "en": "Interview / Podcast"},
        "prodotto": {"it": "Q&A", "en": "Q&A"},
        "descrizione": {"it": "Domande → risposte, citazioni salienti",
                        "en": "Questions → answers, notable quotes"},
    },
    "confronto": {
        "icona": "⚖️", "voci_default": True, "studio_auto": False, "parti": True,
        "label": {"it": "Confronto a due parti", "en": "Two-party discussion"},
        "prodotto": {"it": "Verbale del confronto", "en": "Discussion record"},
        "descrizione": {"it": "Temi: richiesta → risposta → esito",
                        "en": "Topics: request → response → outcome"},
    },
}

NOMI_LINGUA = {"it": "italiano", "en": "English", "es": "español", "fr": "français",
               "de": "Deutsch", "pt": "português"}


def profilo(nome: str | None) -> dict:
    return PROFILI.get(nome or PROFILO_DEFAULT, PROFILI[PROFILO_DEFAULT])


def lingua_prompt(lingua: str) -> str:
    """Lingua in cui sono scritti i prompt: italiano o inglese."""
    return "it" if lingua == "it" else "en"


def regole(lingua: str) -> str:
    if lingua_prompt(lingua) == "it":
        return ("REGOLE TASSATIVE: usa solo informazioni presenti nel testo; non inventare nulla; "
                'se un dato non emerge scrivi "non specificato"; ignora convenevoli, pause e problemi '
                "tecnici. Rispondi in italiano.")
    nome = NOMI_LINGUA.get(lingua, lingua)
    return ("STRICT RULES: use only information present in the text; do not invent anything; "
            'if something is not stated write "not specified"; ignore small talk, pauses and technical '
            f"issues. Write your answer in {nome}.")


def _parti(parti: list[str], it: bool) -> tuple[str, str]:
    a = parti[0] if len(parti) > 0 and parti[0] else ("Parte A" if it else "Party A")
    b = parti[1] if len(parti) > 1 and parti[1] else ("Parte B" if it else "Party B")
    return a, b


def _focus_note(prof: str, it: bool, parti: list[str]) -> str:
    if prof == "riunione":
        return ("- Decisioni: [mm:ss] <decisione presa>\n- Azioni: [mm:ss] <chi> → <cosa> <scadenza se detta>\n"
                "- Punti aperti: [mm:ss] <questione rimasta aperta>\n") if it else (
                "- Decisions: [mm:ss] <decision made>\n- Actions: [mm:ss] <who> → <what> <deadline if stated>\n"
                "- Open points: [mm:ss] <unresolved question>\n")
    if prof == "intervista":
        return ("- Domande: [mm:ss] <domanda> → <chi risponde>: <risposta fedele in 2-3 frasi>\n"
                '- Citazioni: "<frase testuale saliente>" — <chi> [mm:ss]\n') if it else (
                "- Questions: [mm:ss] <question> → <who answers>: <faithful answer in 2-3 sentences>\n"
                '- Quotes: "<notable verbatim sentence>" — <who> [mm:ss]\n')
    if prof == "confronto":
        a, b = _parti(parti, it)
        return (f"- Richiesta di {a}: <sintesi>\n- Risposta di {b}: <sintesi>\n- Esito: <concordato o da fare>\n") if it else (
                f"- Request from {a}: <summary>\n- Response from {b}: <summary>\n- Outcome: <agreed or to do>\n")
    return ""


def prompt_note(prof: str, testo: str, lingua: str, parti: list[str] | None = None) -> str:
    """Map: note di blocco ricche, una volta sola, base di tutti i prodotti."""
    it = lingua_prompt(lingua) == "it"
    focus = _focus_note(prof, it, parti or [])
    if it:
        testa = ("Sei l'assistente che prende appunti accurati su un estratto di una registrazione. "
                 "Per ogni argomento trattato produci una scheda ESATTAMENTE in questo formato:\n\n"
                 "### ARGOMENTO: <titolo breve>\n- Inizio: [mm:ss]\n- Sintesi: <riassunto fedele in 3-6 frasi>\n"
                 "- Concetti: <termine — spiegazione come data nella registrazione> [mm:ss]; <termine — spiegazione> [mm:ss]\n"
                 "- Definizioni: <termine: definizione, solo se data esplicitamente>\n"
                 "- Passaggi chiave: [mm:ss] <affermazione, esempio, formula o dato importante>\n")
        coda = "\nTRASCRIZIONE:\n"
    else:
        testa = ("You are the assistant taking accurate notes on an excerpt of a recording. "
                 "For each topic covered produce a card EXACTLY in this format:\n\n"
                 "### TOPIC: <short title>\n- Start: [mm:ss]\n- Summary: <faithful summary in 3-6 sentences>\n"
                 "- Concepts: <term — explanation as given in the recording> [mm:ss]; <term — explanation> [mm:ss]\n"
                 "- Definitions: <term: definition, only if explicitly given>\n"
                 "- Key passages: [mm:ss] <important statement, example, formula or figure>\n")
        coda = "\nTRANSCRIPT:\n"
    return testa + focus + "\n" + regole(lingua) + "\n" + coda + testo


def prompt_condensa(note: str, lingua: str) -> str:
    """Reduce intermedia: unisce schede consecutive mantenendo il formato."""
    if lingua_prompt(lingua) == "it":
        return ("Unisci le schede di appunti qui sotto, estratte da blocchi consecutivi della STESSA registrazione. "
                "Mantieni ESATTAMENTE lo stesso formato a schede, unisci gli argomenti duplicati o spezzati "
                "(timestamp più antico), non perdere concetti, definizioni né passaggi chiave.\n\n"
                + regole(lingua) + "\n\nSCHEDE:\n" + note)
    return ("Merge the note cards below, extracted from consecutive blocks of the SAME recording. "
            "Keep EXACTLY the same card format, merge duplicated or split topics (earliest timestamp), "
            "do not drop concepts, definitions or key passages.\n\n" + regole(lingua) + "\n\nCARDS:\n" + note)


def prompt_prodotto(prof: str, note: str, lingua: str, parti: list[str] | None = None) -> str:
    """Reduce finale: il prodotto del profilo, dalle note di blocco."""
    it = lingua_prompt(lingua) == "it"
    if prof == "riunione":
        corpo = ("Redigi il RESOCONTO di UNA riunione a partire dagli appunti qui sotto, ESATTAMENTE in questo formato:\n"
                 "### CONTESTO\n<2-3 frasi su tema e scopo>\n### DECISIONI\n- [mm:ss] <decisione>\n"
                 "### AZIONI\n- [mm:ss] <chi> → <cosa> <scadenza se presente>\n"
                 "### PUNTI APERTI\n- [mm:ss] <questione aperta; escludi ciò che risulta risolto>\n"
                 "Unisci i duplicati e ordina ogni sezione per timestamp.") if it else (
                "Write the MINUTES of ONE meeting from the notes below, EXACTLY in this format:\n"
                "### CONTEXT\n<2-3 sentences on topic and purpose>\n### DECISIONS\n- [mm:ss] <decision>\n"
                "### ACTIONS\n- [mm:ss] <who> → <what> <deadline if any>\n"
                "### OPEN POINTS\n- [mm:ss] <open question; exclude what was resolved>\n"
                "Merge duplicates and sort each section by timestamp.")
    elif prof == "intervista":
        corpo = ("Redigi il Q&A di UNA intervista a partire dagli appunti qui sotto:\n"
                 "### DOMANDA: <domanda in breve>\n- Timestamp: [mm:ss]\n- Chi risponde: <nome o voce>\n"
                 "- Risposta: <sintesi fedele in 2-4 frasi>\n"
                 "Ordina per timestamp e chiudi con:\n### CITAZIONI SALIENTI\n- \"<citazione testuale>\" — <chi> [mm:ss] (le 3-6 migliori)") if it else (
                "Write the Q&A of ONE interview from the notes below:\n"
                "### QUESTION: <short question>\n- Timestamp: [mm:ss]\n- Answered by: <name or voice>\n"
                "- Answer: <faithful summary in 2-4 sentences>\n"
                "Sort by timestamp and end with:\n### NOTABLE QUOTES\n- \"<verbatim quote>\" — <who> [mm:ss] (the best 3-6)")
    elif prof == "confronto":
        a, b = _parti(parti or [], it)
        corpo = (f"Redigi il VERBALE di un confronto tra {a} e {b} a partire dagli appunti qui sotto. "
                 "Per ogni tema, ESATTAMENTE:\n### TEMA: <titolo breve>\n- Timestamp: [mm:ss]\n"
                 f"- Richiesta di {a}: <1-2 frasi>\n- Risposta di {b}: <1-2 frasi>\n- Esito: <concordato o da fare>\n"
                 "Unisci i temi duplicati (timestamp più antico) e ordina per timestamp.") if it else (
                f"Write the RECORD of a discussion between {a} and {b} from the notes below. "
                "For each topic, EXACTLY:\n### TOPIC: <short title>\n- Timestamp: [mm:ss]\n"
                f"- Request from {a}: <1-2 sentences>\n- Response from {b}: <1-2 sentences>\n- Outcome: <agreed or to do>\n"
                "Merge duplicate topics (earliest timestamp) and sort by timestamp.")
    else:
        corpo = ("Redigi la DISPENSA di UNA lezione a partire dagli appunti qui sotto, ESATTAMENTE in questo formato:\n"
                 "# <titolo della lezione, dedotto dal contenuto>\n### IN BREVE\n<riassunto complessivo in 4-6 righe>\n"
                 "### CAPITOLI\n#### [mm:ss] <titolo del capitolo>\n<contenuto in 1-2 paragrafi, con esempi e passaggi chiave>\n"
                 "### CONCETTI CHIAVE\n- **<termine>** — <spiegazione in una riga, solo se spiegato nella lezione> "
                 "[mm:ss del punto in cui è spiegato, per poterlo riascoltare]\n"
                 "Unisci i capitoli sullo stesso argomento (timestamp più antico) e ordina per timestamp.") if it else (
                "Write the STUDY NOTES of ONE lecture from the notes below, EXACTLY in this format:\n"
                "# <lecture title, inferred from the content>\n### TL;DR\n<overall summary in 4-6 lines>\n"
                "### CHAPTERS\n#### [mm:ss] <chapter title>\n<content in 1-2 paragraphs, with examples and key passages>\n"
                "### KEY CONCEPTS\n- **<term>** — <one-line explanation, only if explained in the lecture> "
                "[mm:ss of where it is explained, so it can be replayed]\n"
                "Merge chapters on the same topic (earliest timestamp) and sort by timestamp.")
    etichetta = "\n\nAPPUNTI:\n" if it else "\n\nNOTES:\n"
    return corpo + "\n\n" + regole(lingua) + etichetta + note


def per_api(lingua_ui: str = "it") -> list[dict]:
    """Registry per l'interfaccia (endpoint /api/profili): niente copie nel frontend."""
    return [{"id": k, **v} for k, v in PROFILI.items()]
