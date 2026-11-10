"""Prodotti di studio: prompt IT/EN e schemi dell'output strutturato."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .profili import lingua_prompt, regole


class Carta(BaseModel):
    domanda: str
    risposta: str


class Flashcard(BaseModel):
    carte: list[Carta] = Field(min_length=1)


class Domanda(BaseModel):
    domanda: str
    risposta: str


class Autoverifica(BaseModel):
    domande: list[Domanda] = Field(min_length=1)


class Termine(BaseModel):
    termine: str
    definizione: str


class Glossario(BaseModel):
    termini: list[Termine] = Field(min_length=1)


MODELLI = {"flashcard": Flashcard, "autoverifica": Autoverifica, "glossario": Glossario}

_ISTR = {
    "mappa": {
        "it": ("Costruisci una MAPPA MENTALE della registrazione a partire dagli appunti qui sotto. "
               "Usa SOLO Markdown gerarchico: una riga «# <tema centrale>», poi «## <ramo>» per i 4-8 temi "
               "principali, poi elenchi puntati annidati (- e due spazi per livello) con concetti brevi "
               "(massimo 8 parole per nodo). Puoi aggiungere [mm:ss] alla fine dei nodi. Nessun altro testo."),
        "en": ("Build a MIND MAP of the recording from the notes below. "
               "Use ONLY hierarchical Markdown: one line «# <central theme>», then «## <branch>» for the 4-8 "
               "main themes, then nested bullet lists (- and two spaces per level) with short concepts "
               "(at most 8 words per node). You may append [mm:ss] to nodes. No other text."),
    },
    "flashcard": {
        "it": ("Crea da 10 a 25 FLASHCARD per ripassare la registrazione, dagli appunti qui sotto. "
               "Ogni carta: «domanda» breve e precisa, «risposta» in 1-3 frasi. Copri i concetti più "
               "importanti, senza duplicati. Rispondi in JSON."),
        "en": ("Create 10 to 25 FLASHCARDS to review the recording, from the notes below. "
               "Each card: a short precise «domanda» (question), a «risposta» (answer) in 1-3 sentences. "
               "Cover the most important concepts, no duplicates. Answer in JSON."),
    },
    "autoverifica": {
        "it": ("Crea da 5 a 10 DOMANDE APERTE di autoverifica sulla registrazione, dagli appunti qui sotto: "
               "domande che richiedono di spiegare, collegare o applicare i concetti. Per ognuna una "
               "«risposta» modello in 2-5 frasi. Rispondi in JSON."),
        "en": ("Create 5 to 10 OPEN self-assessment QUESTIONS («domanda») about the recording, from the notes below: "
               "questions that require explaining, connecting or applying concepts. For each, a model "
               "«risposta» (answer) in 2-5 sentences. Answer in JSON."),
    },
    "glossario": {
        "it": ("Crea il GLOSSARIO della registrazione dagli appunti qui sotto: i termini tecnici, i nomi "
               "propri e le sigle importanti, ciascuno con una «definizione» di UNA riga coerente con la "
               "registrazione. Ordine alfabetico. Rispondi in JSON."),
        "en": ("Create the GLOSSARY of the recording from the notes below: technical terms, proper names "
               "and important acronyms («termine»), each with a ONE-line «definizione» (definition) consistent "
               "with the recording. Alphabetical order. Answer in JSON."),
    },
}


# ── dispensa: testo continuo da pubblicazione, senza minutaggio ──
LIVELLI = ("sintetica", "approfondita")
_STILE = {
    "it": ("Scrivi in prosa continua e discorsiva, come un capitolo di un libro di testo: paragrafi ben collegati, "
           "spiegazioni complete, esempi della registrazione. NIENTE timestamp, niente riferimenti a «la registrazione», "
           "«il relatore» o «gli appunti»: il testo deve stare in piedi da solo. Elenchi puntati solo se indispensabili. "
           "Usa il grassetto per i termini chiave alla prima occorrenza."),
    "en": ("Write in continuous, discursive prose, like a textbook chapter: well-connected paragraphs, complete "
           "explanations, examples from the recording. NO timestamps, no references to «the recording», «the speaker» "
           "or «the notes»: the text must stand on its own. Bullet lists only if essential. "
           "Bold key terms on first use."),
}


def _coda(note: str, lingua: str) -> str:
    lp = lingua_prompt(lingua)
    return "\n\n" + _STILE[lp] + "\n\n" + regole(lingua) + ("\n\nAPPUNTI:\n" if lp == "it" else "\n\nNOTES:\n") + note


def prompt_dispensa(note: str, lingua: str) -> str:
    """Livello sintetico: tutta la dispensa in una chiamata."""
    if lingua_prompt(lingua) == "it":
        testa = ("Redigi la DISPENSA della registrazione a partire dagli appunti qui sotto, in forma di breve pubblicazione:\n"
                 "# <titolo>\n<introduzione di un paragrafo>\n## <sezione>\n<1-2 paragrafi>\n... (segui l'ordine logico degli "
                 "argomenti, unisci quelli ripetuti)\n## In sintesi\n<un paragrafo conclusivo>. Sii sintetico ed essenziale.")
    else:
        testa = ("Write the STUDY HANDOUT of the recording from the notes below, as a short publication:\n"
                 "# <title>\n<one-paragraph introduction>\n## <section>\n<1-2 paragraphs>\n... (follow the logical order "
                 "of the topics, merge repeated ones)\n## Summary\n<one concluding paragraph>. Be concise and essential.")
    return testa + _coda(note, lingua)


def prompt_sezione(note: str, lingua: str, i: int, n: int, gia: list[str]) -> str:
    """Livello approfondito: una parte della dispensa per ogni blocco di appunti."""
    fatti = "; ".join(gia[-30:])
    if lingua_prompt(lingua) == "it":
        testa = (f"Stai scrivendo la parte {i} di {n} di una DISPENSA approfondita. Dagli appunti qui sotto scrivi una o più "
                 "sezioni «## <titolo>», ciascuna di 3-6 paragrafi ampi e discorsivi, con eventuali «### <sottotitolo>». "
                 "Niente titolo generale, niente introduzione né conclusione: solo le sezioni, in modo che proseguano il testo.")
        if fatti:
            testa += f" Sezioni già scritte (non ripeterle, al più richiamale brevemente): {fatti}."
    else:
        testa = (f"You are writing part {i} of {n} of an in-depth STUDY HANDOUT. From the notes below write one or more "
                 "«## <title>» sections, each with 3-6 broad discursive paragraphs, optionally with «### <subtitle>». "
                 "No overall title, no introduction or conclusion: only the sections, so that they continue the text.")
        if fatti:
            testa += f" Sections already written (do not repeat them, at most refer back briefly): {fatti}."
    return testa + _coda(note, lingua)


def prompt_apertura(sezioni: str, lingua: str) -> str:
    """Livello approfondito: titolo e introduzione, scritti dopo le sezioni."""
    if lingua_prompt(lingua) == "it":
        testa = ("Qui sotto c'è il corpo di una dispensa. Scrivi SOLO il titolo «# <titolo>» e un'introduzione di 1-2 "
                 "paragrafi che presenti gli argomenti e il filo del discorso. Non riscrivere le sezioni.")
        et = "\n\nCORPO:\n"
    else:
        testa = ("Below is the body of a study handout. Write ONLY the title «# <title>» and a 1-2 paragraph "
                 "introduction presenting the topics and the thread of the discussion. Do not rewrite the sections.")
        et = "\n\nBODY:\n"
    return testa + "\n\n" + regole(lingua) + et + sezioni


def senza_tempi(t: str) -> str:
    """Toglie i timestamp sfuggiti al modello."""
    t = re.sub(r"\s*\[\d{1,2}:\d{2}(?::\d{2})?\]", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def prompt(tipo: str, note: str, lingua: str) -> str:
    lp = lingua_prompt(lingua)
    etichetta = "\n\nAPPUNTI:\n" if lp == "it" else "\n\nNOTES:\n"
    return _ISTR[tipo][lp] + "\n\n" + regole(lingua) + etichetta + note


def schema(tipo: str) -> dict | None:
    m = MODELLI.get(tipo)
    return m.model_json_schema() if m else None
