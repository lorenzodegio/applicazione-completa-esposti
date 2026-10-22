import hashlib
import io
import uuid

import pytest

from documenti import ArchivioCartellaLocale, ErroreArchivio


@pytest.fixture
def arch(tmp_path):
    return ArchivioCartellaLocale(tmp_path / "archivio")


def test_salva_apri_impronta(arch):
    dati = b"contenuto sintetico"
    rif = arch.salva(uuid.uuid4(), "esposto.pdf", io.BytesIO(dati))
    assert rif.sha256 == hashlib.sha256(dati).hexdigest() and rif.dimensione == len(dati)
    assert rif.id_archivio.endswith(".pdf") and "esposto" not in rif.id_archivio
    assert arch.apri(rif.id_archivio).read() == dati and arch.impronta(rif.id_archivio) == rif.sha256


def test_salva_accanto_usa_lo_stesso_id(arch):
    doc = uuid.uuid4()
    rif = arch.salva(uuid.uuid4(), "a.pdf", io.BytesIO(b"x"), id_documento=doc)
    t = arch.salva_accanto(rif, "testo.json", b'{"pagine": []}')
    assert t.id_archivio == rif.id_archivio.replace(".pdf", ".testo.json") and str(doc) in t.id_archivio


def test_percorsi_fuori_dall_archivio_rifiutati(arch):
    for chiave in ("../fuori.txt", "/etc/passwd", "a/../../fuori"):
        with pytest.raises(ErroreArchivio):
            arch.apri(chiave)
    rif = arch.salva(uuid.uuid4(), "../../x/evil.pdf", io.BytesIO(b"x"))
    assert rif.id_archivio.count("/") == 1  # il nome del file non può spostare nulla
    with pytest.raises(ErroreArchivio):
        arch.salva_accanto(rif, "../x", b"x")


def test_nessun_file_parziale(arch):
    arch.salva(uuid.uuid4(), "a.pdf", io.BytesIO(b"x"))
    assert not list(arch.radice.rglob("*.parziale"))


def test_verifica_di_salute(arch, tmp_path):
    arch.verifica()                                        # scrivibile: nessun errore, nessun file lasciato
    assert not list(arch.radice.glob(".salute-*"))
    finto = tmp_path / "non_una_cartella"
    finto.write_bytes(b"x")
    arch.radice = finto                                    # la radice non è più una cartella usabile
    with pytest.raises(ErroreArchivio):
        arch.verifica()
