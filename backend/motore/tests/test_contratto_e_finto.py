import io
import json
from pathlib import Path

import pytest

from motore.client import (
    MotoreOccupato, MotoreRifiuto, RisultatoNonValido, motore_finto_in_processo,
)
from motore.contratto import Risultato, StatoLavoro

CONTRATTO = Path(__file__).resolve().parent.parent / "contratto"
SHA = "a" * 64


def invia_e_concludi(m, nome, dati=b"x", sha=None, id_lavoro="lavoro-1"):
    import hashlib
    sha = sha or hashlib.sha256(dati).hexdigest()
    m.invia(id_lavoro=id_lavoro, documento=io.BytesIO(dati), nome_file=nome, tipo_mime="application/pdf",
            documento_id="doc-1", sha256=sha)
    s = m.stato(id_lavoro)
    assert s.stato == "in_corso" and s.avanzamento
    return m.stato(id_lavoro)


@pytest.mark.parametrize("nome", ["lettura_pulita", "lettura_incerta", "riscontro"])
def test_esempi_rispettano_il_contratto(nome):
    testo = (CONTRATTO / "esempi" / f"{nome}.json").read_text().replace("{{documento_id}}", "d").replace("{{sha256}}", SHA)
    Risultato.model_validate_json(testo)


def test_schemi_json_in_sincronia_con_i_modelli():
    for nome, modello in (("risultato", Risultato), ("stato_lavoro", StatoLavoro)):
        atteso = json.dumps(modello.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        assert (CONTRATTO / f"schema_{nome}.json").read_text() == atteso, \
            f"rigenera schema_{nome}.json dopo aver cambiato i modelli"


def test_campi_sconosciuti_ignorati():
    testo = (CONTRATTO / "esempi" / "lettura_pulita.json").read_text().replace("{{documento_id}}", "d").replace("{{sha256}}", SHA)
    dati = json.loads(testo); dati["campo_nuovo"] = 1; dati["scheda"]["altro"] = 2
    Risultato.model_validate(dati)


def test_incoerenza_lettura_incerta_rifiutata():
    testo = (CONTRATTO / "esempi" / "lettura_incerta.json").read_text().replace("{{documento_id}}", "d").replace("{{sha256}}", SHA)
    dati = json.loads(testo); dati["lettura_incerta"] = False
    with pytest.raises(ValueError):
        Risultato.model_validate(dati)


def test_percorso_felice():
    s = invia_e_concludi(motore_finto_in_processo(), "esposto_cani.pdf")
    assert s.stato == "completato" and s.risultato.documento.sha256 and not s.risultato.lettura_incerta


def test_manoscritto_lettura_incerta():
    s = invia_e_concludi(motore_finto_in_processo(), "foglio_manoscritto.pdf")
    assert s.risultato.lettura_incerta and s.risultato.pagine_incerte == [2]


def test_riscontro():
    s = invia_e_concludi(motore_finto_in_processo(), "riscontro_ats.pdf")
    assert s.risultato.tipo_documento.valore == "riscontro_ats"


@pytest.mark.parametrize("nome,codice,ritentabile", [
    ("lettera.pages", "formato_non_supportato", False),
    ("illeggibile.pdf", "documento_illeggibile", False),
    ("scaduto.pdf", "tempo_scaduto", True),
])
def test_errori(nome, codice, ritentabile):
    s = invia_e_concludi(motore_finto_in_processo(), nome)
    assert s.stato == "errore" and s.errore.codice == codice and s.errore.ritentabile is ritentabile


def test_impronta_errata_422():
    m = motore_finto_in_processo()
    with pytest.raises(MotoreRifiuto) as e:
        m.invia(id_lavoro="l", documento=io.BytesIO(b"x"), nome_file="a.pdf", tipo_mime=None,
                documento_id="d", sha256=SHA)
    assert e.value.errore.codice == "impronta_non_coincide" and e.value.errore.ritentabile


def test_uno_alla_volta_e_idempotenza():
    import hashlib
    m = motore_finto_in_processo()
    h = hashlib.sha256(b"x").hexdigest()
    kw = dict(documento_id="d", sha256=h, tipo_mime=None, nome_file="a.pdf")
    m.invia(id_lavoro="l1", documento=io.BytesIO(b"x"), **kw)
    assert m.invia(id_lavoro="l1", documento=io.BytesIO(b"x"), **kw) == "l1"   # stesso id: nessun secondo lavoro
    with pytest.raises(MotoreOccupato):
        m.invia(id_lavoro="l2", documento=io.BytesIO(b"x"), **kw)


def test_conferma_cancella_il_lavoro():
    m = motore_finto_in_processo()
    invia_e_concludi(m, "a.pdf", id_lavoro="l9")
    m.conferma("l9")
    assert m.stato("l9").stato == "errore"  # il lavoro non esiste più


def test_risultato_invalido_segnala_solo_i_percorsi():
    s = None
    with pytest.raises(RisultatoNonValido) as e:
        invia_e_concludi(motore_finto_in_processo(), "esposto_invalido.pdf")
    assert any("frase" in p for p in e.value.percorsi) and "xxx" not in str(e.value.percorsi)


# --- codici HTTP del motore (stato) e contratto 1.2 -------------------------------------------------------

def _motore_con(risposta):
    import httpx
    from motore.client import MotoreHttp
    return MotoreHttp(http_client=httpx.Client(transport=httpx.MockTransport(lambda req: risposta(req)),
                                               base_url="http://motore:8080"))


def test_stato_500_testuale_e_irraggiungibile():
    import httpx
    from motore.client import MotoreIrraggiungibile
    m = _motore_con(lambda req: httpx.Response(500, text="Internal Server Error"))
    with pytest.raises(MotoreIrraggiungibile):
        m.stato("l1")


def test_stato_404_con_corpo_non_valido_e_irraggiungibile():
    import httpx
    from motore.client import MotoreIrraggiungibile
    m = _motore_con(lambda req: httpx.Response(404, json={"detail": "Not Found"}))   # MOTORE_URL sbagliato, proxy
    with pytest.raises(MotoreIrraggiungibile):
        m.stato("l1")


def test_stato_404_dopo_riavvio_del_motore_resta_un_errore_ritentabile():
    import httpx
    corpo = {"id_lavoro": "l1", "stato": "errore",
             "errore": {"codice": "errore_interno", "messaggio": "Lavoro sconosciuto.", "ritentabile": True}}
    s = _motore_con(lambda req: httpx.Response(404, json=corpo)).stato("l1")
    assert s.stato == "errore" and s.errore.codice == "errore_interno" and s.errore.ritentabile


def test_stato_200_fuori_contratto_resta_risultato_non_valido():
    import httpx
    m = _motore_con(lambda req: httpx.Response(200, json={"id_lavoro": "l1", "stato": "completato"}))
    with pytest.raises(RisultatoNonValido):
        m.stato("l1")


def test_metadati_malformati_422_richiesta_non_valida():
    from fastapi.testclient import TestClient
    from motore.finto.app import crea_app
    c = TestClient(crea_app())
    for metadati in ("non json", json.dumps({"id_lavoro": "l1"}), json.dumps({"id_lavoro": "l1", "documento": {}})):
        r = c.post("/v1/analisi", files={"documento": ("a.pdf", b"x")}, data={"metadati": metadati})
        assert r.status_code == 422
        assert r.json()["errore"] == {"codice": "richiesta_non_valida", "messaggio": "Metadati mancanti o malformati.",
                                     "ritentabile": False}


def test_il_client_rifiuta_senza_ritentare_una_richiesta_non_valida():
    import httpx
    corpo = {"id_lavoro": None, "stato": "errore",
             "errore": {"codice": "richiesta_non_valida", "messaggio": "x", "ritentabile": False}}
    m = _motore_con(lambda req: httpx.Response(422, json=corpo))
    with pytest.raises(MotoreRifiuto) as e:
        m.invia(id_lavoro="l1", documento=io.BytesIO(b"x"), nome_file="a.pdf", tipo_mime=None, documento_id="d", sha256=SHA)
    assert e.value.errore.codice == "richiesta_non_valida" and not e.value.errore.ritentabile


@pytest.mark.parametrize("versione,valida", [("1.0", True), ("1.1", True), ("1.2", True), ("1.17", True),
                                              ("2.0", False), ("1", False), ("1.x", False)])
def test_si_accetta_qualunque_versione_1_x(versione, valida):
    from pydantic import ValidationError
    dati = json.loads((CONTRATTO / "esempi" / "lettura_pulita.json").read_text(encoding="utf-8")
                      .replace("{{documento_id}}", "d").replace("{{sha256}}", SHA))
    dati["versione_contratto"] = versione
    if valida:
        assert Risultato.model_validate(dati).versione_contratto == versione
    else:
        with pytest.raises(ValidationError):
            Risultato.model_validate(dati)


def test_versione_del_contratto_e_1_2():
    from motore.contratto import VERSIONE_CONTRATTO
    assert VERSIONE_CONTRATTO == "1.2"
