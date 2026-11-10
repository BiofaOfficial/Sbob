import subprocess
import time

import pytest


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SBOB_HOME", str(tmp_path / "Sbob"))
    monkeypatch.setenv("SBOB_MOTORI", "fake")
    return tmp_path / "Sbob"


@pytest.fixture(scope="session")
def audio(tmp_path_factory):
    p = tmp_path_factory.mktemp("media") / "lezione.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=60",
                    str(p)], check=True)
    return p


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from sbob.api import crea_app
    with TestClient(crea_app(), base_url="http://127.0.0.1") as c:
        yield c


def attendi(client, lid, condizione, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = client.get(f"/api/lavori/{lid}").json()
        if condizione(d):
            return d
        time.sleep(0.2)
    raise AssertionError(f"timeout: {[(f['nome'], f['stato'], f['inizio'], f['fine']) for f in d['fasi']]}")


def finito(d):
    return all(f["stato"] in ("fatto", "saltata", "manuale", "errore") for f in d["fasi"])
