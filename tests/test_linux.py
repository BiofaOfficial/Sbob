"""Motore Linux (faster-whisper) provato con una libreria finta: niente modelli da scaricare."""
import sys
import types

import pytest

from sbob import config, engines


class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


@pytest.fixture
def fw_finto(monkeypatch):
    """Finto modulo faster_whisper: registra i caricamenti; sulla «cuda» la trascrizione fallisce."""
    caricamenti = []

    class WhisperModel:
        def __init__(self, modello, device, compute_type):
            self.device = device
            caricamenti.append((modello, device, compute_type))

        def transcribe(self, wav, **kw):
            if self.device == "cuda":
                raise RuntimeError("libcudnn non trovata")
            info = types.SimpleNamespace(language="it", duration=10.0)
            return iter([_Seg(0.0, 4.0, " Buongiorno a tutti. "), _Seg(4.0, 5.0, "  "), _Seg(5.0, 10.0, "Oggi parliamo di limiti.")]), info

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=WhisperModel))
    return caricamenti


def test_trascrizione_su_cpu(fw_finto, monkeypatch):
    from sbob.engines.faster_whisper import TrascrittoreFW
    monkeypatch.setattr(TrascrittoreFW, "_preferito", staticmethod(lambda: ("cpu", "int8")))
    t = TrascrittoreFW("large-v3-turbo")
    passi = []
    lingua, segs = t.trascrivi("x.wav", "auto", None, passi.append)
    assert lingua == "it"
    assert segs == [{"start_ms": 0, "end_ms": 4000, "testo": "Buongiorno a tutti."},
                    {"start_ms": 5000, "end_ms": 10000, "testo": "Oggi parliamo di limiti."}]
    assert passi[-1] == 1.0 and passi == sorted(passi)
    t.trascrivi("x.wav", "it", None)
    assert fw_finto == [("large-v3-turbo", "cpu", "int8")]  # il modello resta in memoria tra due lavori
    t.modello = "small"
    t.trascrivi("x.wav", "it", None)
    assert fw_finto[-1] == ("small", "cpu", "int8")  # cambiato in Impostazioni: si ricarica
    t.scarica()
    assert t.stato()["caricato"] is False


def test_ripiego_sulla_cpu_se_la_scheda_nvidia_fallisce(fw_finto, monkeypatch):
    from sbob.engines.faster_whisper import TrascrittoreFW
    monkeypatch.setattr(TrascrittoreFW, "_preferito", staticmethod(lambda: ("cuda", "float16")))
    t = TrascrittoreFW("large-v3-turbo")
    _, segs = t.trascrivi("x.wav", "it", None)
    assert len(segs) == 2 and t.dispositivo == "cpu"
    assert [c[1] for c in fw_finto] == ["cuda", "cpu"]


def test_scelta_dei_motori_su_linux(monkeypatch):
    monkeypatch.delenv("SBOB_MOTORI")
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setattr(config.importlib.util, "find_spec", lambda nome: object())
    assert config.motori_effettivi({"motori": "auto"}) == "linux"
    monkeypatch.setattr(config.importlib.util, "find_spec", lambda nome: None)
    assert config.motori_effettivi({"motori": "auto"}) == "fake"
    m = engines.crea(dict(config.DEFAULTS), "linux")
    assert m.nome == "linux" and type(m.trascrittore).__name__ == "TrascrittoreFW"
