"""Valutazione dell'operatore, temi e disaccordo IA–operatore (piano 3.5).

La proposta dell'IA resta nel risultato del motore; la valutazione è un'altra cosa, con
autore, origine e data. La precompilazione si calcola, non si salva.
"""
import datetime as dt
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import OrigineTema, OrigineValutazione, StatoTema
from .models import (
    Pratica, PraticaTema, RisultatoMotore, Tema, Utente, Valutazione, VoceVocabolario,
    vista_analisi_principale, vista_disaccordo,
)
from .registro import registra
from .schemas import Differenza, TemaDecisione, TemaOut, ValutazioneIn, ValutazioneOut, ValutazioneVista

CAMPI_LISTA = {"ambito": "ambito", "problematica": "problematica", "elementi": "elementi", "azione": "azione"}
CAMPI_VALORE = {"esito": "esito", "urgenza": "urgenza"}
CAMPI_TESTO_LIBERO = ("ambito_altro", "problematica_altro", "elementi_altro", "note")  # nel registro: solo "cambiato"
CAMPI = ["data_doc", "comune", "ambito", "problematica", "elementi", "ambito_altro", "problematica_altro",
         "elementi_altro", "esito", "urgenza", "azione", "note"]


def vocabolari_attuali(db: Session) -> dict[str, set[str]]:
    voci: dict[str, set[str]] = {}
    for v in db.execute(select(VoceVocabolario).where(VoceVocabolario.attivo, VoceVocabolario.elenco == "attuale")).scalars():
        voci.setdefault(v.vocabolario, set()).add(v.codice)
    return voci


def valida(db: Session, dati: ValutazioneIn, *, per_conferma: bool) -> None:
    """I valori delle liste e di esito/urgenza devono stare nei vocabolari attuali (altrimenti 422)."""
    ok, errori = vocabolari_attuali(db), []
    for campo, voc in {**CAMPI_LISTA, **CAMPI_VALORE}.items():
        valori = getattr(dati, campo)
        for v in ([valori] if isinstance(valori, str) else valori or []):
            if v not in ok.get(voc, set()):
                errori.append({"campo": campo, "valore": v})
    if errori:
        raise HTTPException(422, {"messaggio": "Valori non presenti nei vocabolari", "campi": errori})
    if per_conferma and (not dati.esito or not dati.urgenza):
        raise HTTPException(422, "Per confermare la valutazione servono esito e urgenza")


def ultimo_risultato_principale(db: Session, pratica_id: uuid.UUID) -> RisultatoMotore | None:
    return db.execute(select(RisultatoMotore).join(
        vista_analisi_principale, vista_analisi_principale.c.risultato_id == RisultatoMotore.id
    ).where(vista_analisi_principale.c.pratica_id == pratica_id)).scalar_one_or_none()


def precompilazione(db: Session, pratica: Pratica) -> dict | None:
    """Proposta del motore nella forma del modulo. Valori fuori vocabolario: scartati e dichiarati."""
    r = ultimo_risultato_principale(db, pratica.id)
    if r is None:
        return None
    ok, scartati = vocabolari_attuali(db), []

    def lista(campo: str) -> list[str]:
        out = []
        for voce in r.scheda.get(campo, []):
            if voce["valore"] in ok.get(campo, set()):
                out.append(voce["valore"])
            else:
                scartati.append({"campo": campo, "valore": voce["valore"]})
        return out

    p = r.proposta
    azione = [a for a in p.get("azione", []) if a in ok.get("azione", set())]
    scartati += [{"campo": "azione", "valore": a} for a in p.get("azione", []) if a not in ok.get("azione", set())]
    esito = p.get("esito") if p.get("esito") in ok.get("esito", set()) else None
    urgenza = p.get("urgenza") if p.get("urgenza") in ok.get("urgenza", set()) else None
    for campo, val in (("esito", p.get("esito")), ("urgenza", p.get("urgenza"))):
        if val and val not in ok.get(campo, set()):
            scartati.append({"campo": campo, "valore": val})
    return {
        "da_risultato_id": str(r.id),
        "data_doc": (r.scheda.get("data_doc") or {}).get("valore"),
        "comune": (r.scheda.get("comune") or {}).get("valore"),
        "ambito": lista("ambito"), "problematica": lista("problematica"), "elementi": lista("elementi"),
        "ambito_altro": r.scheda.get("ambito_altro"), "problematica_altro": r.scheda.get("problematica_altro"),
        "elementi_altro": r.scheda.get("elementi_altro"),
        "esito": esito, "urgenza": urgenza, "azione": azione, "note": None,
        "valori_scartati": scartati,
    }


def disaccordo_per(db: Session, pratica_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Differenza]]:
    """Per ogni pratica in disaccordo, i campi che differiscono (la decisione la prende la vista SQL)."""
    if not pratica_ids:
        return {}
    vd, ap = vista_disaccordo, vista_analisi_principale
    righe = db.execute(
        select(vd.c.pratica_id, vd.c.diff_esito, vd.c.diff_urgenza, vd.c.diff_azione,
               Valutazione.esito, Valutazione.urgenza, Valutazione.azione, RisultatoMotore.proposta)
        .join(Valutazione, Valutazione.pratica_id == vd.c.pratica_id)
        .join(ap, ap.c.pratica_id == vd.c.pratica_id)
        .join(RisultatoMotore, RisultatoMotore.id == ap.c.risultato_id)
        .where(vd.c.pratica_id.in_(pratica_ids), vd.c.in_disaccordo)).all()
    out: dict[uuid.UUID, list[Differenza]] = {}
    for r in righe:
        campi = []
        if r.diff_esito:
            campi.append({"campo": "esito", "ia": r.proposta.get("esito"), "operatore": r.esito})
        if r.diff_urgenza:
            campi.append({"campo": "urgenza", "ia": r.proposta.get("urgenza"), "operatore": r.urgenza})
        if r.diff_azione:
            campi.append({"campo": "azione", "ia": sorted(r.proposta.get("azione", [])), "operatore": sorted(r.azione)})
        out[r.pratica_id] = [Differenza(**c) for c in campi]
    return out


def diff(prima: dict, dopo: dict) -> dict:
    """prima/dopo per il registro. I testi liberi (note, *_altro) non vanno nel registro: solo «cambiato»."""
    p, d = {}, {}
    for c in CAMPI:
        if prima.get(c) == dopo.get(c):
            continue
        if c in CAMPI_TESTO_LIBERO:
            p[c], d[c] = "(testo)" if prima.get(c) else None, "(testo)" if dopo.get(c) else None
        else:
            p[c], d[c] = _json(prima.get(c)), _json(dopo.get(c))
    return {"prima": p, "dopo": d}


def _json(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def stato_valutazione(v: Valutazione | None) -> dict:
    return {c: getattr(v, c) for c in CAMPI} if v else {}


def salva_valutazione(db: Session, pratica: Pratica, utente: Utente, dati: ValutazioneIn,
                      *, azione_registro: str) -> Valutazione:
    """Crea o sostituisce la valutazione dell'applicazione. Regole:
    una valutazione ATS compilata si sovrascrive solo con conferma esplicita."""
    esistente = db.execute(select(Valutazione).where(Valutazione.pratica_id == pratica.id)
                           .with_for_update()).scalar_one_or_none()
    if (esistente and esistente.origine == OrigineValutazione.import_ats and esistente.compilata
            and not dati.conferma_sovrascrittura):
        raise HTTPException(409, "Esiste una valutazione ATS già compilata: per sostituirla serve la conferma esplicita")
    prima = stato_valutazione(esistente)
    r = ultimo_risultato_principale(db, pratica.id)
    campi = {c: getattr(dati, c) for c in CAMPI}
    adesso = dt.datetime.now(dt.timezone.utc)
    if esistente is None:
        esistente = Valutazione(pratica_id=pratica.id, origine=OrigineValutazione.applicazione)
        db.add(esistente)
    for c, v in campi.items():
        setattr(esistente, c, v)
    esistente.origine = OrigineValutazione.applicazione
    esistente.autore_id, esistente.autore_nome = utente.id, None
    esistente.ambito_originale = None
    esistente.compilata = dati.compilata
    esistente.data_compilazione = adesso.date() if dati.compilata else None
    esistente.aggiornata_il = adesso
    if r is not None and esistente.da_risultato_id is None:
        esistente.da_risultato_id = r.id  # da quale proposta è partita la precompilazione
    db.flush()
    registra(db, utente_id=utente.id, azione=azione_registro, oggetto_tipo="valutazione", oggetto_id=esistente.id,
             pratica_id=pratica.id, dettagli={**diff(prima, campi), "compilata": dati.compilata})
    return esistente


# --- temi -------------------------------------------------------------------------------------------

def temi_pratica(db: Session, pratica_id: uuid.UUID) -> list[TemaOut]:
    righe = db.execute(select(PraticaTema).join(Tema).where(PraticaTema.pratica_id == pratica_id)
                       .order_by(Tema.ordine, Tema.codice)).scalars().all()
    r = ultimo_risultato_principale(db, pratica_id)
    proposti = {t["valore"]: t for t in (r.temi_proposti if r else [])}
    out = []
    for pt in righe:
        t = proposti.get(pt.tema.nome) if pt.origine == OrigineTema.ia else None
        out.append(TemaOut(codice=pt.tema.codice, nome=pt.tema.nome, origine=pt.origine, stato=pt.stato,
                           deciso_da=pt.deciso_da, deciso_il=pt.deciso_il,
                           motivo=t["motivo"] if t else None, frase=t["frase"] if t else None,
                           pagina=t["pagina"] if t else None))
    return out


def proponi_temi(db: Session, pratica_id: uuid.UUID, risultato: RisultatoMotore) -> list[str]:
    """Dal risultato del documento principale: ogni tema noto e non ancora presente diventa «proposto».
    Non tocca mai una decisione già presa. Temi sconosciuti: restano solo nel risultato."""
    esistenti = set(db.execute(select(PraticaTema.tema_id).where(PraticaTema.pratica_id == pratica_id)).scalars())
    nuovi = []
    for t in risultato.temi_proposti:
        tema = db.execute(select(Tema).where(Tema.nome == t["valore"], Tema.attivo)).scalar_one_or_none()
        if tema and tema.id not in esistenti:
            db.add(PraticaTema(pratica_id=pratica_id, tema_id=tema.id, origine=OrigineTema.ia, stato=StatoTema.proposto))
            esistenti.add(tema.id)
            nuovi.append(tema.codice)
    return nuovi


def applica_temi(db: Session, pratica: Pratica, utente: Utente, decisioni: list[TemaDecisione]) -> dict:
    """Conferma/scarta temi. Un tema non ancora presente si può solo aggiungere (confermato, origine operatore)."""
    adesso = dt.datetime.now(dt.timezone.utc)
    esistenti = {pt.tema.codice: pt for pt in db.execute(select(PraticaTema).join(Tema)
                 .where(PraticaTema.pratica_id == pratica.id)).scalars()}
    visti, cambi = set(), {}
    for d in decisioni:
        if d.codice in visti:
            raise HTTPException(422, f"Tema «{d.codice}» indicato due volte")
        visti.add(d.codice)
        pt = esistenti.get(d.codice)
        if pt is None:
            tema = db.execute(select(Tema).where(Tema.codice == d.codice, Tema.attivo)).scalar_one_or_none()
            if tema is None:
                raise HTTPException(422, f"Tema «{d.codice}» sconosciuto")
            if d.stato != StatoTema.confermato:
                raise HTTPException(422, f"Il tema «{d.codice}» non è proposto: si può solo aggiungere")
            db.add(PraticaTema(pratica_id=pratica.id, tema_id=tema.id, origine=OrigineTema.operatore,
                               stato=StatoTema.confermato, deciso_da=utente.id, deciso_il=adesso))
            cambi[d.codice] = {"prima": None, "dopo": "confermato", "origine": "operatore"}
        elif pt.stato != d.stato:
            cambi[d.codice] = {"prima": pt.stato.value, "dopo": d.stato.value, "origine": pt.origine.value}
            pt.stato, pt.deciso_da, pt.deciso_il = d.stato, utente.id, adesso
    return cambi


def leggi_valutazione_vista(db: Session, pratica: Pratica) -> ValutazioneVista:
    v = db.execute(select(Valutazione).where(Valutazione.pratica_id == pratica.id)).scalar_one_or_none()
    return ValutazioneVista(
        valutazione=ValutazioneOut.model_validate(v) if v else None,
        # la proposta dell'IA precompila il modulo solo finché non c'è una valutazione compilata
        precompilazione=None if (v and v.compilata) else precompilazione(db, pratica),
        disaccordo=disaccordo_per(db, [pratica.id]).get(pratica.id, []))
