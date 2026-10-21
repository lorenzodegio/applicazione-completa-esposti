"""Contratto 1.1 eseguibile (docs/contratto_motore.md, sezioni 2, 3 e 5).

Regole del contratto rispettate qui:
- i campi sconosciuti si ignorano (extra="ignore");
- i valori dei vocabolari NON si vincolano: un valore sconosciuto non fa fallire il
  salvataggio, lo segnala l'applicazione (api/analisi.py);
- `frase` al massimo 300 caratteri; date ISO; pagine in ordine.
"""
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSIONE_CONTRATTO = "1.1"

Acquisizione = Literal["testo_nativo", "ocr", "ocr_manoscritto", "nessuna"]


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Voce(_M):
    valore: str
    frase: str = Field(max_length=300)
    pagina: int = Field(ge=1)


class VoceData(_M):
    valore: dt.date
    frase: str = Field(max_length=300)
    pagina: int = Field(ge=1)


class TipoDocumento(_M):
    valore: str
    motivo: str


class Protocollo(_M):
    numero: str
    data: dt.date | None = None
    frase: str = Field(max_length=300)
    pagina: int = Field(ge=1)


class Pagina(_M):
    numero: int = Field(ge=1)
    acquisizione: Acquisizione
    testo: str
    lettura_incerta: bool
    motivo_incertezza: str | None = None


class Scheda(_M):
    data_doc: VoceData | None
    comune: Voce | None
    ambito: list[Voce]
    ambito_altro: str | None = None
    problematica: list[Voce]
    problematica_altro: str | None = None
    elementi: list[Voce]
    elementi_altro: str | None = None


class Proposta(_M):
    esito: str
    urgenza: str
    azione: list[str]
    motivo: str
    domanda_decisiva: str
    da_verificare_sull_originale: list[str]


class TemaProposto(_M):
    valore: str
    motivo: str
    frase: str = Field(max_length=300)
    pagina: int = Field(ge=1)


class DocumentoRef(_M):
    id: str
    sha256: str


class Risultato(_M):
    versione_contratto: str
    versione_motore: str
    documento: DocumentoRef
    tipo_documento: TipoDocumento
    protocollo: Protocollo | None = None
    pagine: list[Pagina]
    lettura_incerta: bool
    scheda: Scheda
    proposta: Proposta
    temi: list[TemaProposto]

    @model_validator(mode="after")
    def _coerenza(self) -> "Risultato":
        numeri = [p.numero for p in self.pagine]
        if numeri != sorted(numeri) or len(set(numeri)) != len(numeri):
            raise ValueError("pagine non in ordine o duplicate")
        if self.lettura_incerta != any(p.lettura_incerta for p in self.pagine):
            raise ValueError("lettura_incerta non coerente con le pagine")
        return self

    @property
    def pagine_incerte(self) -> list[int]:
        return [p.numero for p in self.pagine if p.lettura_incerta]


class Avanzamento(_M):
    pagine_lette: int
    pagine_totali: int


class Errore(_M):
    codice: str
    messaggio: str
    ritentabile: bool


class StatoLavoro(_M):
    id_lavoro: str
    stato: Literal["in_coda", "in_corso", "completato", "errore"]
    avanzamento: Avanzamento | None = None
    risultato: Risultato | None = None
    errore: Errore | None = None

    @model_validator(mode="after")
    def _coerenza(self) -> "StatoLavoro":
        if self.stato == "completato" and self.risultato is None:
            raise ValueError("stato completato senza risultato")
        if self.stato == "errore" and self.errore is None:
            raise ValueError("stato errore senza errore")
        return self


class Salute(_M):
    stato: str
    versione_motore: str
    versione_contratto: str
    occupato: bool
