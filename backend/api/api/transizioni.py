"""Transizioni di stato ammesse (piano, sezione 2). Sono dati, e sono testate."""
from dataclasses import dataclass

from .enums import Ruolo, Stato

S, O = Ruolo.smistatore, Ruolo.operatore


@dataclass(frozen=True)
class Regola:
    ruoli: frozenset[Ruolo]          # chi può farla; vuoto = solo il sistema
    motivo_obbligatorio: bool = False
    generica: bool = False           # ammessa da POST /pratiche/{id}/stato


TRANSIZIONI: dict[tuple[Stato, Stato], Regola] = {
    # il worker del motore (sistema), a fine analisi o dopo tre tentativi falliti
    (Stato.IN_ANALISI, Stato.DA_SMISTARE): Regola(frozenset()),
    # azione dedicata: assegnazione
    (Stato.DA_SMISTARE, Stato.DA_VALIDARE): Regola(frozenset({S})),
    # azione dedicata: validazione (richiede valutazione e temi: fase 3)
    (Stato.DA_VALIDARE, Stato.IN_LAVORAZIONE): Regola(frozenset({S, O})),
    # azione dedicata: restituzione all'ufficio smistamento
    (Stato.DA_VALIDARE, Stato.DA_SMISTARE): Regola(frozenset({O}), motivo_obbligatorio=True),
    (Stato.IN_LAVORAZIONE, Stato.DA_SMISTARE): Regola(frozenset({O}), motivo_obbligatorio=True),
    # chiusura e riapertura
    (Stato.IN_LAVORAZIONE, Stato.CHIUSA): Regola(frozenset({S, O}), generica=True),
    (Stato.CHIUSA, Stato.IN_LAVORAZIONE): Regola(frozenset({S}), motivo_obbligatorio=True, generica=True),
}


def regola(da: Stato, a: Stato) -> Regola | None:
    return TRANSIZIONI.get((da, a))
