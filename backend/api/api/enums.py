from enum import StrEnum


class Ruolo(StrEnum):
    smistatore = "smistatore"
    operatore = "operatore"
    amministratore = "amministratore"


class Provider(StrEnum):
    locale = "locale"
    microsoft = "microsoft"


class Canale(StrEnum):
    caricamento_manuale = "caricamento_manuale"
    import_cartella = "import_cartella"


class Stato(StrEnum):
    IN_ANALISI = "IN_ANALISI"
    DA_SMISTARE = "DA_SMISTARE"
    DA_VALIDARE = "DA_VALIDARE"
    IN_LAVORAZIONE = "IN_LAVORAZIONE"
    CHIUSA = "CHIUSA"


class TipoArchivio(StrEnum):
    locale = "locale"
    sharepoint = "sharepoint"


class StatoLavoro(StrEnum):
    in_coda = "in_coda"
    in_corso = "in_corso"
    completato = "completato"
    errore = "errore"


class OrigineValutazione(StrEnum):
    applicazione = "applicazione"
    import_ats = "import_ats"


class OrigineTema(StrEnum):
    ia = "ia"
    operatore = "operatore"


class StatoTema(StrEnum):
    proposto = "proposto"
    confermato = "confermato"
    scartato = "scartato"


class StatoAttivita(StrEnum):
    prevista = "prevista"
    in_corso = "in_corso"
    conclusa = "conclusa"
    annullata = "annullata"
