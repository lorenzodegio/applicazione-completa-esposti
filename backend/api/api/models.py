"""Modello dei dati — piano, sezioni 3.1, 3.2, 3.3 e 3.6 (primo passo).

Restano da aggiungere nei passi successivi: risultato_motore / lavoro_motore,
valutazione, pratica_tema, attivita, collegamenti, importazione.
"""
import datetime as dt
import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    MetaData, Table, Column, BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Identity,
    Index, Integer, String, Text, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import (
    Canale, OrigineTema, OrigineValutazione, Provider, Ruolo, Stato, StatoAttivita, StatoLavoro, StatoTema,
    TipoArchivio,
)


def _enum(cls: type[PyEnum], nome: str) -> Enum:
    return Enum(cls, name=nome, native_enum=False, length=32, create_constraint=True,
                values_callable=lambda e: [m.value for m in e])


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _ora() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Base(DeclarativeBase):
    pass


# --- 3.1 Organizzazione e accesso -------------------------------------------

class Ufficio(Base):
    __tablename__ = "ufficio"
    id: Mapped[uuid.UUID] = _pk()
    codice: Mapped[str] = mapped_column(String(32), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_il: Mapped[dt.datetime] = _ora()


class Utente(Base):
    __tablename__ = "utente"
    __table_args__ = (
        CheckConstraint(
            "(ruolo = 'operatore' AND ufficio_id IS NOT NULL)"
            " OR (ruolo <> 'operatore' AND ufficio_id IS NULL)",
            name="ck_utente_ufficio_ruolo",
        ),
    )
    id: Mapped[uuid.UUID] = _pk()
    username: Mapped[str] = mapped_column(String(100), unique=True)
    nome_visualizzato: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    ruolo: Mapped[Ruolo] = mapped_column(_enum(Ruolo, "ruolo"))
    ufficio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ufficio.id"))
    password_hash: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[Provider] = mapped_column(_enum(Provider, "provider"), default=Provider.locale)
    id_esterno: Mapped[str | None] = mapped_column(String(200), unique=True)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_accesso: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ufficio: Mapped[Ufficio | None] = relationship(lazy="joined")


class Sessione(Base):
    __tablename__ = "sessione"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 del token
    utente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utente.id"), index=True)
    creata_il: Mapped[dt.datetime] = _ora()
    scade_il: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    revocata: Mapped[bool] = mapped_column(Boolean, default=False)


# --- 3.2 Vocabolari e temi ---------------------------------------------------

class VoceVocabolario(Base):
    __tablename__ = "voce_vocabolario"
    __table_args__ = (UniqueConstraint("vocabolario", "codice", "elenco"),)
    id: Mapped[uuid.UUID] = _pk()
    vocabolario: Mapped[str] = mapped_column(String(32))
    codice: Mapped[str] = mapped_column(String(100))
    etichetta: Mapped[str] = mapped_column(String(200))
    ordine: Mapped[int] = mapped_column(Integer, default=0)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    elenco: Mapped[str] = mapped_column(String(10), default="attuale")  # attuale | storico
    converte_in: Mapped[str | None] = mapped_column(String(100))  # codice della voce attuale


class Tema(Base):
    __tablename__ = "tema"
    id: Mapped[uuid.UUID] = _pk()
    codice: Mapped[str] = mapped_column(String(64), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    ordine: Mapped[int] = mapped_column(Integer, default=0)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)


# --- 3.3 Pratica e documenti -------------------------------------------------

class Pratica(Base):
    __tablename__ = "pratica"
    id: Mapped[uuid.UUID] = _pk()
    numero: Mapped[str] = mapped_column(String(32), unique=True)
    protocollo: Mapped[str | None] = mapped_column(String(64), index=True)
    data_protocollo: Mapped[dt.date | None] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(64), default="esposto")
    titolo: Mapped[str] = mapped_column(String(300))
    comune: Mapped[str | None] = mapped_column(String(200))
    canale: Mapped[Canale] = mapped_column(_enum(Canale, "canale"))
    stato: Mapped[Stato] = mapped_column(_enum(Stato, "stato_pratica"), index=True)
    ufficio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ufficio.id"), index=True)
    documento_principale_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento.id", use_alter=True, name="fk_pratica_documento_principale"))
    creata_il: Mapped[dt.datetime] = _ora()
    aggiornata_il: Mapped[dt.datetime] = _ora()
    versione: Mapped[int] = mapped_column(Integer, default=1)
    ufficio: Mapped[Ufficio | None] = relationship(lazy="joined")


class Documento(Base):
    __tablename__ = "documento"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    nome_file: Mapped[str] = mapped_column(String(500))
    tipo_mime: Mapped[str | None] = mapped_column(String(100))
    dimensione: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    archivio: Mapped[TipoArchivio] = mapped_column(_enum(TipoArchivio, "tipo_archivio"))
    id_archivio: Mapped[str] = mapped_column(Text)
    id_archivio_testo: Mapped[str | None] = mapped_column(Text)
    sha256_testo: Mapped[str | None] = mapped_column(String(64))
    tipo_documento: Mapped[str | None] = mapped_column(String(64))
    caricato_da: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))
    caricato_il: Mapped[dt.datetime] = _ora()
    sostituito_da: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documento.id"))


# --- 3.4 Motore ---------------------------------------------------------------

class LavoroMotore(Base):
    """È anche la coda: un lavoro = un documento, elaborato uno alla volta dal worker."""
    __tablename__ = "lavoro_motore"
    __table_args__ = (Index("ix_lavoro_coda", "stato", "richiesto_il"),)
    id: Mapped[uuid.UUID] = _pk()
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documento.id"), index=True)
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    stato: Mapped[StatoLavoro] = mapped_column(_enum(StatoLavoro, "stato_lavoro"), default=StatoLavoro.in_coda)
    tentativi: Mapped[int] = mapped_column(Integer, default=0)
    richiesto_da: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))  # null = automatico
    richiesto_il: Mapped[dt.datetime] = _ora()
    iniziato_il: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finito_il: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    codice_errore: Mapped[str | None] = mapped_column(String(64))


class RisultatoMotore(Base):
    """Uno per lavoro completato; si mostra l'ultimo. Il testo delle pagine NON è qui:
    sta accanto al documento in archivio."""
    __tablename__ = "risultato_motore"
    id: Mapped[uuid.UUID] = _pk()
    lavoro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lavoro_motore.id"), unique=True)
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documento.id"), index=True)
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    versione_motore: Mapped[str] = mapped_column(String(64))
    versione_contratto: Mapped[str] = mapped_column(String(16))
    tipo_documento: Mapped[str] = mapped_column(String(64))
    tipo_documento_motivo: Mapped[str | None] = mapped_column(Text)
    protocollo_letto: Mapped[str | None] = mapped_column(String(64))
    data_protocollo_letta: Mapped[dt.date | None] = mapped_column(Date)
    lettura_incerta: Mapped[bool] = mapped_column(Boolean)
    pagine_incerte: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    acquisizione: Mapped[dict] = mapped_column(JSONB)
    scheda: Mapped[dict] = mapped_column(JSONB)
    proposta: Mapped[dict] = mapped_column(JSONB)
    temi_proposti: Mapped[list] = mapped_column(JSONB)
    ricevuto_il: Mapped[dt.datetime] = _ora()


# --- 3.5 Valutazione e temi della pratica -------------------------------------------

class Valutazione(Base):
    """La valutazione dell'operatore: distinta dalla proposta dell'IA. Una per pratica."""
    __tablename__ = "valutazione"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), unique=True)
    origine: Mapped[OrigineValutazione] = mapped_column(_enum(OrigineValutazione, "origine_valutazione"))
    autore_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))
    autore_nome: Mapped[str | None] = mapped_column(String(200))
    compilata: Mapped[bool] = mapped_column(Boolean, default=False)
    data_compilazione: Mapped[dt.date | None] = mapped_column(Date)
    data_doc: Mapped[dt.date | None] = mapped_column(Date)
    comune: Mapped[str | None] = mapped_column(String(200))
    ambito: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    problematica: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    elementi: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    ambito_originale: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    ambito_altro: Mapped[str | None] = mapped_column(Text)
    problematica_altro: Mapped[str | None] = mapped_column(Text)
    elementi_altro: Mapped[str | None] = mapped_column(Text)
    esito: Mapped[str | None] = mapped_column(String(100))
    urgenza: Mapped[str | None] = mapped_column(String(100))
    azione: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    note: Mapped[str | None] = mapped_column(Text)
    da_risultato_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("risultato_motore.id"))
    # controllo di versione: ogni salvataggio la incrementa; chi salva indica quella che ha letto
    versione: Mapped[int] = mapped_column(Integer, default=1)
    creata_il: Mapped[dt.datetime] = _ora()
    aggiornata_il: Mapped[dt.datetime] = _ora()


class PraticaTema(Base):
    __tablename__ = "pratica_tema"
    __table_args__ = (UniqueConstraint("pratica_id", "tema_id"),)
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    tema_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tema.id"), index=True)
    origine: Mapped[OrigineTema] = mapped_column(_enum(OrigineTema, "origine_tema"))
    stato: Mapped[StatoTema] = mapped_column(_enum(StatoTema, "stato_tema"))
    deciso_da: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))
    deciso_il: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    tema: Mapped[Tema] = relationship(lazy="joined")


class Attivita(Base):
    """Le azioni dell'ufficio sulla pratica (vocabolario `azione`)."""
    __tablename__ = "attivita"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(100))
    stato: Mapped[StatoAttivita] = mapped_column(_enum(StatoAttivita, "stato_attivita"))
    data_prevista: Mapped[dt.date | None] = mapped_column(Date)
    data_conclusione: Mapped[dt.date | None] = mapped_column(Date)
    descrizione: Mapped[str | None] = mapped_column(Text)
    creata_da: Mapped[uuid.UUID] = mapped_column(ForeignKey("utente.id"))
    creata_il: Mapped[dt.datetime] = _ora()
    aggiornata_il: Mapped[dt.datetime] = _ora()


# --- 3.7 Collegamenti ------------------------------------------------------------

class TipoCollegamento(Base):
    __tablename__ = "tipo_collegamento"
    id: Mapped[uuid.UUID] = _pk()
    codice: Mapped[str] = mapped_column(String(32), unique=True)
    etichetta: Mapped[str] = mapped_column(String(100))
    etichetta_inversa: Mapped[str | None] = mapped_column(String(100))  # null = simmetrico
    manuale: Mapped[bool] = mapped_column(Boolean, default=True)


class Collegamento(Base):
    """Solo manuali. Quelli per stesso protocollo si calcolano a ogni lettura."""
    __tablename__ = "collegamento"
    __table_args__ = (Index("uq_collegamento_attivo", "pratica_da_id", "pratica_a_id", "tipo_id", unique=True,
                            postgresql_where=text("rimosso_il IS NULL")),)
    id: Mapped[uuid.UUID] = _pk()
    pratica_da_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    pratica_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    tipo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tipo_collegamento.id"))
    nota: Mapped[str | None] = mapped_column(Text)
    creato_da: Mapped[uuid.UUID] = mapped_column(ForeignKey("utente.id"))
    creato_il: Mapped[dt.datetime] = _ora()
    rimosso_da: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))
    rimosso_il: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    tipo: Mapped[TipoCollegamento] = relationship(lazy="joined")


# Viste calcolate (migrazione 0004), fuori da Base.metadata: si leggono, non si creano da qui.
_viste = MetaData()
vista_analisi_principale = Table(
    "pratica_analisi_principale", _viste, Column("pratica_id", Uuid), Column("risultato_id", Uuid),
    Column("lettura_incerta", Boolean), Column("ricevuto_il", DateTime(timezone=True)))
vista_disaccordo = Table(
    "pratica_disaccordo", _viste, Column("pratica_id", Uuid), Column("diff_esito", Boolean),
    Column("diff_urgenza", Boolean), Column("diff_azione", Boolean), Column("in_disaccordo", Boolean))


# --- 3.6 Lavorazione ---------------------------------------------------------

class Assegnazione(Base):
    __tablename__ = "assegnazione"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    ufficio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ufficio.id"))
    ufficio_precedente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ufficio.id"))
    assegnata_da: Mapped[uuid.UUID] = mapped_column(ForeignKey("utente.id"))
    assegnata_il: Mapped[dt.datetime] = _ora()
    motivo: Mapped[str | None] = mapped_column(Text)
    da_proposta_ia: Mapped[bool] = mapped_column(Boolean, default=False)


class CambioStato(Base):
    __tablename__ = "cambio_stato"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    da_stato: Mapped[Stato | None] = mapped_column(_enum(Stato, "stato_pratica_da"))
    a_stato: Mapped[Stato] = mapped_column(_enum(Stato, "stato_pratica_a"))
    utente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))  # null = sistema
    il: Mapped[dt.datetime] = _ora()
    motivo: Mapped[str | None] = mapped_column(Text)


class NotaInterna(Base):
    """Le note non si modificano: una correzione è una nuova nota."""
    __tablename__ = "nota_interna"
    id: Mapped[uuid.UUID] = _pk()
    pratica_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pratica.id"), index=True)
    autore_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utente.id"))
    testo: Mapped[str] = mapped_column(Text)
    creata_il: Mapped[dt.datetime] = _ora()


# --- 3.9 Registro ------------------------------------------------------------

class RegistroAzioni(Base):
    """Solo inserimento: un trigger (migrazione) blocca UPDATE, DELETE e TRUNCATE."""
    __tablename__ = "registro_azioni"
    __table_args__ = (Index("ix_registro_pratica_quando", "pratica_id", "quando"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    quando: Mapped[dt.datetime] = _ora()
    utente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utente.id"))  # null = sistema
    azione: Mapped[str] = mapped_column(String(64))
    oggetto_tipo: Mapped[str] = mapped_column(String(64))
    oggetto_id: Mapped[str | None] = mapped_column(Text)
    pratica_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pratica.id"))
    dettagli: Mapped[dict | None] = mapped_column(JSONB)  # mai testo dei documenti
    id_richiesta: Mapped[str | None] = mapped_column(String(64))
