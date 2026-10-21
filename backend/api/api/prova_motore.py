"""Prove a mano con il motore (finto di default): python -m api.prova_motore [nome_file ...]

Carica documenti SINTETICI (contenuto inventato, il nome sceglie lo scenario del finto),
fa girare il worker e stampa come l'applicazione presenta il risultato.
Richiede il seed (python -m api.seed) e ESPOSTI_AMBIENTE=sviluppo.
"""
import sys

from fastapi.testclient import TestClient

from .config import get_settings
from .main import app
from .seed import PASSWORD_SVILUPPO
from .worker import esegui_coda

SCENARI = ["esposto_cani.pdf", "foglio_manoscritto.pdf", "riscontro_ats.pdf", "lettera.pages",
           "esposto_scaduto.pdf", "esposto_instabile.pdf", "esposto_invalido.pdf"]


def riga(testo: str = "") -> None:
    print(testo)


def main() -> None:
    if get_settings().ambiente != "sviluppo":
        raise SystemExit("Le prove girano solo con ESPOSTI_AMBIENTE=sviluppo")
    nomi = sys.argv[1:] or SCENARI
    c = TestClient(app, base_url="https://prova")
    r = c.post("/api/v1/auth/login", json={"username": "smistatore", "password": PASSWORD_SVILUPPO})
    if r.status_code != 200:
        raise SystemExit("Login non riuscito: hai eseguito `python -m api.seed`?")
    ids = {}
    for nome in nomi:
        r = c.post("/api/v1/pratiche", files=[("files", (nome, f"contenuto sintetico di {nome}".encode(), "application/pdf"))])
        ids[nome] = r.json()["pratica"]["id"]
    riga(f"Worker: {esegui_coda(dormi=lambda s: None)}\n")
    for nome, pid in ids.items():
        d = c.get(f"/api/v1/pratiche/{pid}").json()
        riga(f"=== {nome} → {d['numero']}  stato={d['stato']}  analisi={d['stato_analisi']['stato']}"
             f" (tentativi {d['stato_analisi']['tentativi']}, errore={d['stato_analisi']['codice_errore']})")
        for a in d["avvisi"]:
            riga(f"    ⚠ [{a['codice']}] {a['testo']}")
        a = d["analisi"]
        if a:
            p = a["proposta"]
            riga(f"    tipo: {a['tipo_documento']}   protocollo letto: {a['protocollo_letto']}   comune: {d['comune']}")
            riga(f"    proposta IA (suggerimento): esito={p['esito']} urgenza={p['urgenza']} azione={p['azione']}")
            riga(f"    domanda decisiva: {p['domanda_decisiva']}")
            for campo in ("ambito", "problematica", "elementi"):
                for v in a["scheda"][campo]:
                    riga(f"    {campo}: {v['valore']}  ← «{v['frase']}» (p. {v['pagina']})")
            riga(f"    temi proposti: {[t['valore'] for t in a['temi_proposti']]}")
            if a["valori_non_riconosciuti"]:
                riga(f"    fuori vocabolario: {a['valori_non_riconosciuti']}")
        riga()


if __name__ == "__main__":
    main()
