"""Come si presenta il risultato del motore alle schermate.

Regole (piano sezioni 2, 3.4 e contratto 3.2):
- la proposta dell'IA è un suggerimento: qui si espone sempre come `proposta`, mai come dato della pratica;
- un valore fuori dai vocabolari NON blocca nulla: si mostra e si segnala in `valori_non_riconosciuti`;
- `avvisi` è la lista pronta da mostrare (lettura incerta, analisi non disponibile, valori sconosciuti);
- il testo delle pagine non sta qui: si legge da /documenti/{id}/testo.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import StatoLavoro
from .models import Documento, LavoroMotore, Pratica, RisultatoMotore, Tema, VoceVocabolario
from .schemas import AnalisiOut, Avviso, StatoAnalisiOut


def _attuali(db: Session) -> dict[str, set[str]]:
    voci: dict[str, set[str]] = {}
    for v in db.execute(select(VoceVocabolario).where(VoceVocabolario.attivo, VoceVocabolario.elenco == "attuale")).scalars():
        voci.setdefault(v.vocabolario, set()).add(v.codice)
    voci["tema"] = set(db.execute(select(Tema.nome).where(Tema.attivo)).scalars())
    return voci


def valori_non_riconosciuti(db: Session, r: RisultatoMotore) -> list[dict]:
    ok, fuori = _attuali(db), []

    def controlla(campo: str, vocabolario: str, valore: str) -> None:
        if valore not in ok.get(vocabolario, set()):
            fuori.append({"campo": campo, "valore": valore})

    controlla("tipo_documento", "tipo_documento", r.tipo_documento)
    for campo in ("ambito", "problematica", "elementi"):
        for voce in r.scheda.get(campo, []):
            controlla(f"scheda.{campo}", campo, voce["valore"])
    controlla("proposta.esito", "esito", r.proposta["esito"])
    controlla("proposta.urgenza", "urgenza", r.proposta["urgenza"])
    for a in r.proposta.get("azione", []):
        controlla("proposta.azione", "azione", a)
    for t in r.temi_proposti:
        controlla("temi", "tema", t["valore"])
    return fuori


def _analisi_out(db: Session, r: RisultatoMotore) -> AnalisiOut:
    fuori = valori_non_riconosciuti(db, r)
    avvisi: list[Avviso] = []
    if r.lettura_incerta:
        elenco = ", ".join(str(n) for n in r.pagine_incerte)
        avvisi.append(Avviso(codice="lettura_incerta", pagine=r.pagine_incerte,
                             testo=f"Lettura incerta (pagine {elenco}): controlla sull'originale."))
    if fuori:
        avvisi.append(Avviso(codice="valori_non_riconosciuti",
                             testo="Alcuni valori proposti dal motore non sono nei vocabolari: verifica prima di usarli."))
    return AnalisiOut(
        risultato_id=r.id, lavoro_id=r.lavoro_id, documento_id=r.documento_id, ricevuto_il=r.ricevuto_il,
        versione_motore=r.versione_motore, versione_contratto=r.versione_contratto,
        tipo_documento=r.tipo_documento, tipo_documento_motivo=r.tipo_documento_motivo,
        protocollo_letto=r.protocollo_letto, data_protocollo_letta=r.data_protocollo_letta,
        lettura_incerta=r.lettura_incerta, pagine_incerte=list(r.pagine_incerte), acquisizione=r.acquisizione,
        scheda=r.scheda, proposta=r.proposta, temi_proposti=r.temi_proposti,
        valori_non_riconosciuti=fuori, avvisi=avvisi)


def risultati_documento(db: Session, documento_id: uuid.UUID) -> list[AnalisiOut]:
    righe = db.execute(select(RisultatoMotore).where(RisultatoMotore.documento_id == documento_id)
                       .order_by(RisultatoMotore.ricevuto_il.desc(), RisultatoMotore.id)).scalars().all()
    return [_analisi_out(db, r) for r in righe]


def stato_analisi_documento(db: Session, documento_id: uuid.UUID) -> StatoAnalisiOut | None:
    lavori = db.execute(select(LavoroMotore).where(LavoroMotore.documento_id == documento_id)
                        .order_by(LavoroMotore.richiesto_il.desc(), LavoroMotore.id)).scalars().all()
    if not lavori:
        return None
    ultimo = lavori[0]
    if any(l.stato in (StatoLavoro.in_coda, StatoLavoro.in_corso) for l in lavori):
        stato = "in_corso"
    elif ultimo.stato == StatoLavoro.completato:
        stato = "completata"
    else:
        stato = "non_disponibile"
    return StatoAnalisiOut(stato=stato, lavoro_id=ultimo.id, stato_lavoro=ultimo.stato,
                           tentativi=ultimo.tentativi, codice_errore=ultimo.codice_errore)


def analisi_pratica(db: Session, pratica: Pratica) -> tuple[StatoAnalisiOut | None, AnalisiOut | None, list[Avviso]]:
    """Stato, ultimo risultato e avvisi del documento principale."""
    if pratica.documento_principale_id is None:
        return None, None, []
    stato = stato_analisi_documento(db, pratica.documento_principale_id)
    ris = risultati_documento(db, pratica.documento_principale_id)
    ultimo = ris[0] if ris else None
    avvisi = list(ultimo.avvisi) if ultimo else []
    if stato and stato.stato == "non_disponibile":
        avvisi.insert(0, Avviso(codice="analisi_non_disponibile",
                                testo="Analisi non disponibile: la pratica va trattata senza proposta dell'IA."
                                if ultimo is None else
                                "L'ultima analisi non è riuscita: si mostra il risultato precedente."))
    return stato, ultimo, avvisi
