import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import Canale, OrigineTema, OrigineValutazione, Ruolo, Stato, StatoAttivita, StatoLavoro, StatoTema


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UfficioOut(_Out):
    id: uuid.UUID
    codice: str
    nome: str
    attivo: bool


class UfficioIn(BaseModel):
    codice: str = Field(min_length=1, max_length=32)
    nome: str = Field(min_length=1, max_length=200)


class UfficioPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    attivo: bool | None = None


class UtenteOut(_Out):
    id: uuid.UUID
    username: str
    nome_visualizzato: str
    email: str | None
    ruolo: Ruolo
    ufficio: UfficioOut | None
    attivo: bool


class MeOut(BaseModel):
    utente: UtenteOut
    menu: list[str]


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UtenteIn(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    nome_visualizzato: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    ruolo: Ruolo
    ufficio_id: uuid.UUID | None = None
    password: str = Field(min_length=10, max_length=200)


class UtentePatch(BaseModel):
    nome_visualizzato: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    ruolo: Ruolo | None = None
    ufficio_id: uuid.UUID | None = None
    attivo: bool | None = None


class PasswordIn(BaseModel):
    password: str = Field(min_length=10, max_length=200)


class UfficioRef(_Out):
    id: uuid.UUID
    codice: str
    nome: str


class PraticaOut(_Out):
    id: uuid.UUID
    numero: str
    protocollo: str | None
    data_protocollo: dt.date | None
    tipo: str
    titolo: str
    comune: str | None
    canale: Canale
    stato: Stato
    ufficio: UfficioRef | None
    creata_il: dt.datetime
    aggiornata_il: dt.datetime
    versione: int


class EsitoRiga(BaseModel):
    esito: str | None
    urgenza: str | None
    origine: OrigineValutazione
    compilata: bool


class Differenza(BaseModel):
    """Un campo su cui la valutazione dell'operatore e la proposta dell'IA differiscono."""
    campo: str
    ia: Any = None
    operatore: Any = None


class PropostaRiga(BaseModel):
    """Esito e urgenza proposti dall'IA per il documento principale (un suggerimento)."""
    esito: str | None
    urgenza: str | None


class PraticaRiga(PraticaOut):
    """Riga di elenco (Gestione pratiche, Inbox, Smistamento, Fascicoli)."""
    temi: list[str] = []               # solo temi confermati
    valutazione: EsitoRiga | None = None
    proposta: PropostaRiga | None = None
    lettura_incerta: bool = False
    disaccordo: list[Differenza] = []
    n_collegate: int = 0


class Pagina(BaseModel):
    items: list[PraticaRiga]
    total: int
    page: int
    per_page: int


class PraticaPatch(BaseModel):
    versione: int
    titolo: str | None = Field(default=None, min_length=1, max_length=300)
    protocollo: str | None = Field(default=None, max_length=64)
    comune: str | None = Field(default=None, max_length=200)


class AssegnazioneIn(BaseModel):
    versione: int
    ufficio_id: uuid.UUID
    motivo: str | None = Field(default=None, max_length=2000)
    da_proposta_ia: bool = False


class RestituzioneIn(BaseModel):
    versione: int
    motivo: str = Field(min_length=1, max_length=2000)


class CambioStatoIn(BaseModel):
    versione: int
    a_stato: Stato
    motivo: str | None = Field(default=None, max_length=2000)


class NotaIn(BaseModel):
    testo: str = Field(min_length=1, max_length=10000)


class NotaOut(_Out):
    id: uuid.UUID
    autore_id: uuid.UUID
    testo: str
    creata_il: dt.datetime


class VoceStorico(BaseModel):
    tipo: str  # "assegnazione" | "cambio_stato"
    il: dt.datetime
    utente_id: uuid.UUID | None
    dettagli: dict


class VoceRegistro(BaseModel):
    quando: dt.datetime
    utente_id: uuid.UUID | None
    azione: str
    oggetto_tipo: str
    oggetto_id: str | None
    dettagli: dict | None


# --- documenti e analisi del motore -----------------------------------------------------

class Avviso(BaseModel):
    codice: str  # lettura_incerta | analisi_non_disponibile | valori_non_riconosciuti
    testo: str
    pagine: list[int] | None = None


class StatoAnalisiOut(BaseModel):
    stato: str  # in_corso | completata | non_disponibile
    lavoro_id: uuid.UUID
    stato_lavoro: StatoLavoro
    tentativi: int
    codice_errore: str | None


class AnalisiOut(BaseModel):
    """Il suggerimento del motore: mai un dato della pratica. `scheda`, `proposta` e
    `temi_proposti` hanno la forma del contratto (voci con frase e pagina)."""
    risultato_id: uuid.UUID
    lavoro_id: uuid.UUID
    documento_id: uuid.UUID
    ricevuto_il: dt.datetime
    versione_motore: str
    versione_contratto: str
    tipo_documento: str
    tipo_documento_motivo: str | None
    protocollo_letto: str | None
    data_protocollo_letta: dt.date | None
    lettura_incerta: bool
    pagine_incerte: list[int]
    acquisizione: dict
    scheda: dict
    proposta: dict
    temi_proposti: list
    valori_non_riconosciuti: list[dict]
    avvisi: list[Avviso]


class PraticaDettaglio(PraticaOut):
    stato_analisi: StatoAnalisiOut | None = None
    analisi: AnalisiOut | None = None
    avvisi: list[Avviso] = []
    temi: list["TemaOut"] = []
    valutazione: "ValutazioneVista | None" = None
    disaccordo: list[Differenza] = []
    n_collegate: int = 0


class DocumentoOut(_Out):
    id: uuid.UUID
    nome_file: str
    tipo_mime: str | None
    dimensione: int | None
    sha256: str
    tipo_documento: str | None
    caricato_il: dt.datetime
    principale: bool = False
    analisi: StatoAnalisiOut | None = None


class LavoroOut(_Out):
    id: uuid.UUID
    documento_id: uuid.UUID
    stato: StatoLavoro
    tentativi: int
    richiesto_il: dt.datetime
    iniziato_il: dt.datetime | None
    finito_il: dt.datetime | None
    codice_errore: str | None


class NuovaPraticaOut(BaseModel):
    pratica: PraticaOut
    documenti: list[DocumentoOut]


# --- valutazione, temi, attività --------------------------------------------------------

class ValutazioneIn(BaseModel):
    """Sostituisce l'intera valutazione. `compilata=False` salva una bozza."""
    data_doc: dt.date | None = None
    comune: str | None = Field(default=None, max_length=200)
    ambito: list[str] = []
    problematica: list[str] = []
    elementi: list[str] = []
    ambito_altro: str | None = Field(default=None, max_length=2000)
    problematica_altro: str | None = Field(default=None, max_length=2000)
    elementi_altro: str | None = Field(default=None, max_length=2000)
    esito: str | None = Field(default=None, max_length=100)
    urgenza: str | None = Field(default=None, max_length=100)
    azione: list[str] = []
    note: str | None = Field(default=None, max_length=10000)
    compilata: bool = True
    conferma_sovrascrittura: bool = False  # serve solo per sovrascrivere una valutazione ATS importata


class ValutazioneOut(_Out):
    id: uuid.UUID
    origine: OrigineValutazione
    autore_id: uuid.UUID | None
    autore_nome: str | None
    compilata: bool
    data_compilazione: dt.date | None
    data_doc: dt.date | None
    comune: str | None
    ambito: list[str]
    problematica: list[str]
    elementi: list[str]
    ambito_originale: list[str] | None
    ambito_altro: str | None
    problematica_altro: str | None
    elementi_altro: str | None
    esito: str | None
    urgenza: str | None
    azione: list[str]
    note: str | None
    da_risultato_id: uuid.UUID | None
    creata_il: dt.datetime
    aggiornata_il: dt.datetime


class ValutazioneVista(BaseModel):
    valutazione: ValutazioneOut | None
    precompilazione: dict | None      # dalla proposta dell'IA: NON è salvata finché l'operatore non conferma
    disaccordo: list[Differenza]


class TemaDecisione(BaseModel):
    codice: str = Field(max_length=64)
    stato: StatoTema

    @field_validator("stato")
    @classmethod
    def _decisione(cls, v: StatoTema) -> StatoTema:
        if v == StatoTema.proposto:
            raise ValueError("Un tema si conferma o si scarta")
        return v


class TemiIn(BaseModel):
    temi: list[TemaDecisione]


class TemaOut(BaseModel):
    codice: str
    nome: str
    origine: OrigineTema
    stato: StatoTema
    deciso_da: uuid.UUID | None
    deciso_il: dt.datetime | None
    motivo: str | None = None   # per i temi proposti dall'IA
    frase: str | None = None
    pagina: int | None = None


class ValidazioneIn(BaseModel):
    versione: int
    valutazione: ValutazioneIn
    temi: list[TemaDecisione]


class AttivitaIn(BaseModel):
    tipo: str = Field(max_length=100)
    data_prevista: dt.date | None = None
    descrizione: str | None = Field(default=None, max_length=2000)


class AttivitaPatch(BaseModel):
    stato: StatoAttivita | None = None
    data_prevista: dt.date | None = None
    data_conclusione: dt.date | None = None
    descrizione: str | None = Field(default=None, max_length=2000)


class AttivitaOut(_Out):
    id: uuid.UUID
    pratica_id: uuid.UUID
    tipo: str
    stato: StatoAttivita
    data_prevista: dt.date | None
    data_conclusione: dt.date | None
    descrizione: str | None
    creata_da: uuid.UUID
    creata_il: dt.datetime
    aggiornata_il: dt.datetime


# --- collegamenti, percorso, schermate -----------------------------------------------------

class TipoCollegamentoOut(_Out):
    id: uuid.UUID
    codice: str
    etichetta: str
    etichetta_inversa: str | None
    manuale: bool


class PraticaRef(BaseModel):
    """Pratica collegata. Fuori dal perimetro dell'utente: solo numero, ufficio e stato (`id` nullo)."""
    id: uuid.UUID | None
    numero: str
    ufficio: UfficioRef | None
    stato: Stato
    tipo: str | None = None
    titolo: str | None = None
    protocollo: str | None = None
    comune: str | None = None


class CollegamentoOut(BaseModel):
    id: uuid.UUID | None          # nullo per i collegamenti automatici
    automatico: bool
    tipo: TipoCollegamentoOut
    etichetta: str                # già nel verso giusto rispetto alla pratica che si guarda
    nota: str | None
    pratica: PraticaRef
    creato_il: dt.datetime | None = None


class CollegamentoIn(BaseModel):
    pratica_id: uuid.UUID
    tipo_id: uuid.UUID
    nota: str | None = Field(default=None, max_length=2000)


class RicercaRapidaOut(BaseModel):
    id: uuid.UUID
    numero: str
    protocollo: str | None
    titolo: str
    comune: str | None
    stato: Stato


class PassoPercorso(BaseModel):
    passo: str          # esposto | inoltro | proposta_ia | smistamento | validazione | azione | riscontro
    stato: str          # concluso | in_corso | atteso
    titolo: str
    testo: str | None = None
    data: dt.datetime | None = None
    documento_id: uuid.UUID | None = None
    pagina: int | None = None
    pratica_collegata: PraticaRef | None = None


class TemaCatalogoOut(_Out):
    codice: str
    nome: str


class FascicoloOut(BaseModel):
    codice: str
    nome: str
    pratiche: int


class DisaccordoHome(BaseModel):
    totale: int
    pratiche: list[PraticaRiga]


class HomeOut(BaseModel):
    contatori: dict[str, int]
    ultimi_arrivi: list[PraticaRiga]
    fascicoli_piu_attivi: list[FascicoloOut]
    disaccordo: DisaccordoHome


PraticaDettaglio.model_rebuild()
