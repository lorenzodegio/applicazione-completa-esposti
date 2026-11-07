"""Client HTTP del motore. L'applicazione usa solo questa interfaccia."""
import json
from pathlib import Path
from typing import BinaryIO, Protocol

import httpx

from .contratto.modelli import VERSIONE_CONTRATTO, Errore, Salute, StatoLavoro


class MotoreOccupato(Exception):
    def __init__(self, retry_after: float):
        super().__init__("motore occupato")
        self.retry_after = retry_after


class MotoreRifiuto(Exception):
    """Il motore ha rifiutato la consegna con un errore del contratto (es. impronta)."""
    def __init__(self, errore: Errore):
        super().__init__(errore.codice)
        self.errore = errore


class MotoreIrraggiungibile(Exception):
    """Rete, timeout o risposta non interpretabile: si tratta come errore_interno ritentabile."""


class ClientMotore(Protocol):
    def salute(self) -> Salute: ...
    def invia(self, *, id_lavoro: str, documento: BinaryIO, nome_file: str, tipo_mime: str | None,
              documento_id: str, sha256: str, contesto: dict | None = None) -> str: ...
    def stato(self, id_lavoro: str) -> StatoLavoro: ...
    def conferma(self, id_lavoro: str) -> None: ...


class MotoreHttp:
    def __init__(self, base_url: str = "http://motore:8080", *, http_client: httpx.Client | None = None,
                 timeout: float = 30.0):
        self._c = http_client or httpx.Client(base_url=base_url, timeout=timeout)

    def _chiama(self, metodo: str, percorso: str, **kw) -> httpx.Response:
        try:
            return self._c.request(metodo, percorso, **kw)
        except httpx.HTTPError as e:
            raise MotoreIrraggiungibile(type(e).__name__) from e

    def salute(self) -> Salute:
        r = self._chiama("GET", "/v1/salute")
        try:
            return Salute.model_validate(r.json())
        except Exception as e:
            raise MotoreIrraggiungibile("salute non interpretabile") from e

    def invia(self, *, id_lavoro, documento, nome_file, tipo_mime, documento_id, sha256, contesto=None) -> str:
        metadati = {"versione_contratto": VERSIONE_CONTRATTO, "id_lavoro": id_lavoro,
                    "documento": {"id": documento_id, "nome_file": nome_file,
                                  "tipo_mime": tipo_mime or "application/octet-stream", "sha256": sha256}}
        if contesto:
            metadati["contesto"] = contesto
        r = self._chiama("POST", "/v1/analisi",
                         files={"documento": (nome_file, documento, tipo_mime or "application/octet-stream")},
                         data={"metadati": json.dumps(metadati)})
        if r.status_code == 429:
            raise MotoreOccupato(float(r.headers.get("Retry-After", "5")))
        if r.status_code == 202:
            return r.json()["id_lavoro"]
        try:
            raise MotoreRifiuto(Errore.model_validate(r.json()["errore"]))
        except (KeyError, ValueError, TypeError) as e:
            raise MotoreIrraggiungibile(f"risposta {r.status_code}") from e

    def stato(self, id_lavoro: str) -> StatoLavoro:
        """Un corpo StatoLavoro valido vale con qualunque codice HTTP (es. il 404 del motore riavviato, con
        errore_interno ritentabile). Un corpo non valido: con 200 è un risultato fuori contratto; con un altro
        codice (500 testuale, 404 di un URL sbagliato, proxy) è un guasto, ritentabile."""
        r = self._chiama("GET", f"/v1/analisi/{id_lavoro}")
        try:
            dati = r.json()
        except ValueError as e:
            raise MotoreIrraggiungibile(f"risposta {r.status_code} non JSON") from e
        try:
            return StatoLavoro.model_validate(dati)
        except Exception as e:
            if r.status_code != 200:
                raise MotoreIrraggiungibile(f"risposta {r.status_code} non conforme") from e
            # Un risultato che viola il contratto: lo si distingue da un guasto di rete.
            raise RisultatoNonValido(_percorsi_errore(e), dati) from e

    def conferma(self, id_lavoro: str) -> None:
        self._chiama("DELETE", f"/v1/analisi/{id_lavoro}")


class RisultatoNonValido(Exception):
    def __init__(self, percorsi: list[str], grezzo: dict):
        super().__init__("risultato non conforme al contratto")
        self.percorsi = percorsi  # solo i percorsi dei campi, mai i valori
        self.grezzo = grezzo


def _percorsi_errore(e: Exception) -> list[str]:
    try:
        return sorted({".".join(str(x) for x in err["loc"]) for err in e.errors()})  # type: ignore[attr-defined]
    except Exception:
        return ["?"]


def motore_finto_in_processo() -> MotoreHttp:
    """Finto motore nello stesso processo (nessun servizio da avviare): sviluppo e test."""
    from fastapi.testclient import TestClient

    from .finto.app import crea_app
    return MotoreHttp(http_client=TestClient(crea_app(), base_url="http://motore-finto"))
