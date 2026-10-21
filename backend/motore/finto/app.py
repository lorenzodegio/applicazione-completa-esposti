"""Finto motore: stessa forma del vero (contratto 1.1), risposte deterministiche.

Non legge il contenuto dei documenti: sceglie lo scenario dal NOME del file.

    nome contiene …            scenario
    --------------------------------------------------------------------------
    riscontro                  riscontro ATS (esempio 6.3)
    manoscritto | incerto      foglio scritto a mano, lettura incerta (6.2)
    errore | .pages            formato_non_supportato, non ritentabile (6.4)
    illeggibile                documento_illeggibile, non ritentabile
    scaduto                    tempo_scaduto, ritentabile (fallisce sempre)
    instabile                  errore_interno la prima volta, poi riesce
    occupato                   la prima consegna riceve 429 + Retry-After
    invalido                   risultato che viola il contratto (frase > 300)
    (altro)                    esposto digitato, nessuna incertezza (6.1)

Ogni lavoro passa da in_coda → in_corso → concluso a ogni interrogazione
(MOTORE_FINTO_INTERROGAZIONI, default 2). Si avvia anche da solo:
    uvicorn motore.finto.app:app --port 8080
"""
import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Response, UploadFile
from fastapi.responses import JSONResponse

from ..contratto import VERSIONE_CONTRATTO

ESEMPI = Path(__file__).resolve().parent.parent / "contratto" / "esempi"
VERSIONE_MOTORE = "finto-1.0.0"


class StatoFinto:
    def __init__(self) -> None:
        self.lavori: dict[str, dict] = {}
        self.tentativi_per_nome: dict[str, int] = {}
        self.interrogazioni_per_concludere = int(os.environ.get("MOTORE_FINTO_INTERROGAZIONI", "2"))

    def occupato(self) -> bool:
        return any(not j["concluso"] for j in self.lavori.values())


def crea_app() -> FastAPI:
    app = FastAPI(title="Finto motore (contratto 1.1)")
    stato = StatoFinto()
    app.state.finto = stato

    def esempio(nome: str, **sostituzioni: str) -> dict:
        testo = (ESEMPI / f"{nome}.json").read_text(encoding="utf-8")
        for k, v in sostituzioni.items():
            testo = testo.replace("{{" + k + "}}", v)
        return json.loads(testo)

    def scenario(nome_file: str) -> str:
        n = nome_file.lower()
        if "riscontro" in n: return "riscontro"
        if "manoscritto" in n or "incerto" in n: return "lettura_incerta"
        if "errore" in n or n.endswith(".pages"): return "errore_formato"
        if "illeggibile" in n: return "errore_illeggibile"
        if "scaduto" in n: return "errore_scaduto"
        if "instabile" in n: return "instabile"
        if "invalido" in n: return "invalido"
        return "lettura_pulita"

    def risultato_per(job: dict) -> dict:
        sc = job["scenario"]
        if sc == "errore_formato":
            return {"errore": esempio("errore_formato_non_supportato", id_lavoro=job["id"])["errore"]}
        if sc == "errore_illeggibile":
            return {"errore": {"codice": "documento_illeggibile", "ritentabile": False,
                               "messaggio": "Nessuna pagina contiene testo riconoscibile."}}
        if sc == "errore_scaduto":
            return {"errore": {"codice": "tempo_scaduto", "ritentabile": True,
                               "messaggio": "Analisi oltre il tempo massimo."}}
        if sc == "instabile" and job["tentativo_nome"] == 1:
            return {"errore": {"codice": "errore_interno", "ritentabile": True, "messaggio": "Errore interno."}}
        base = {"instabile": "lettura_pulita", "invalido": "lettura_pulita"}.get(sc, sc)
        r = esempio(base, documento_id=job["documento_id"], sha256=job["sha256"])
        r["versione_motore"] = VERSIONE_MOTORE
        if sc == "invalido":
            r["scheda"]["comune"]["frase"] = "x" * 301  # viola il limite di 300 caratteri
        return {"risultato": r}

    @app.get("/v1/salute")
    def salute() -> dict:
        return {"stato": "pronto", "versione_motore": VERSIONE_MOTORE,
                "versione_contratto": VERSIONE_CONTRATTO, "occupato": stato.occupato()}

    @app.post("/v1/analisi", status_code=202)
    async def consegna(documento: UploadFile = File(...), metadati: str = Form(...)):
        meta = json.loads(metadati)
        id_lavoro = meta["id_lavoro"]
        if id_lavoro in stato.lavori:  # idempotenza
            return {"id_lavoro": id_lavoro, "stato": stato.lavori[id_lavoro]["stato"]}
        nome = meta["documento"]["nome_file"]
        if "occupato" in nome.lower() and stato.tentativi_per_nome.get(nome + "#429", 0) == 0:
            stato.tentativi_per_nome[nome + "#429"] = 1
            return JSONResponse({"id_lavoro": id_lavoro, "stato": "errore", "errore": {
                "codice": "occupato", "messaggio": "Un altro lavoro è in corso.", "ritentabile": True}},
                status_code=429, headers={"Retry-After": "1"})
        if stato.occupato():
            return JSONResponse({"id_lavoro": id_lavoro, "stato": "errore", "errore": {
                "codice": "occupato", "messaggio": "Un altro lavoro è in corso.", "ritentabile": True}},
                status_code=429, headers={"Retry-After": "1"})
        contenuto = await documento.read()
        if hashlib.sha256(contenuto).hexdigest() != meta["documento"]["sha256"]:
            return JSONResponse({"id_lavoro": id_lavoro, "stato": "errore", "errore": {
                "codice": "impronta_non_coincide", "messaggio": "Il file è arrivato danneggiato.",
                "ritentabile": True}}, status_code=422)
        stato.tentativi_per_nome[nome] = stato.tentativi_per_nome.get(nome, 0) + 1
        stato.lavori[id_lavoro] = {
            "id": id_lavoro, "stato": "in_coda", "concluso": False, "interrogazioni": 0,
            "scenario": scenario(nome), "documento_id": meta["documento"]["id"],
            "sha256": meta["documento"]["sha256"], "tentativo_nome": stato.tentativi_per_nome[nome]}
        return {"id_lavoro": id_lavoro, "stato": "in_coda"}

    @app.get("/v1/analisi/{id_lavoro}")
    def leggi(id_lavoro: str):
        job = stato.lavori.get(id_lavoro)
        if job is None:
            return JSONResponse({"id_lavoro": id_lavoro, "stato": "errore", "errore": {
                "codice": "errore_interno", "messaggio": "Lavoro sconosciuto.", "ritentabile": True}},
                status_code=404)
        if job["concluso"]:
            return job["esito"]
        job["interrogazioni"] += 1
        if job["interrogazioni"] < stato.interrogazioni_per_concludere:
            job["stato"] = "in_corso"
            return {"id_lavoro": id_lavoro, "stato": "in_corso",
                    "avanzamento": {"pagine_lette": job["interrogazioni"], "pagine_totali": stato.interrogazioni_per_concludere}}
        parti = risultato_per(job)
        job["concluso"] = True
        if "risultato" in parti:
            job["stato"] = "completato"
            job["esito"] = {"id_lavoro": id_lavoro, "stato": "completato", "risultato": parti["risultato"]}
        else:
            job["stato"] = "errore"
            job["esito"] = {"id_lavoro": id_lavoro, "stato": "errore", "errore": parti["errore"]}
        return job["esito"]

    @app.delete("/v1/analisi/{id_lavoro}", status_code=204)
    def conferma(id_lavoro: str) -> Response:
        stato.lavori.pop(id_lavoro, None)  # cancella tutto ciò che resta del lavoro
        return Response(status_code=204)

    return app


app = crea_app()
