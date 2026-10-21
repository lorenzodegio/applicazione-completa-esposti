"""Configurazione caricata con le migrazioni: vocabolari del modulo ATS e temi.

Fonte: piano (sezione 3.2) e contratto del motore 1.1 (sezione 4). Se cambia un
elenco, si scrive una nuova migrazione: questo file non si usa per aggiornare
un database già esistente.
"""

VOCABOLARI: dict[str, list[str]] = {
    "tipo_documento": ["esposto", "inoltro_per_competenza", "richiesta_ente", "riscontro_ats",
                       "lettera_avvocato", "integrazione", "altro"],
    "ambito": ["Medicina Veterinaria", "Igiene pubblica", "Disturbo/rumori", "ARPA", "Altro"],
    "problematica": ["Maltrattamento animale", "Abbandono animale", "Condizioni igieniche carenti",
                     "Odori molesti", "Rumori persistenti", "Uccisione",
                     "Condizione di inidonea detenzione", "Altro"],
    "elementi": ["Ferite/sofferenza animale", "Presenza escrementi", "Odori molesti",
                 "Rumori persistenti", "Rischio sanitario", "Foto/allegati", "Precedenti segnalazioni",
                 "Animali liberi o randagi", "Omessa custodia", "Altro"],
    "esito": ["Accolto", "Archiviato", "Da approfondire", "Altro", "Invio Modulo"],
    "urgenza": ["Bassa", "Normale", "Alta", "Immediata"],
    "azione": ["Sopralluogo", "Sopralluogo congiunto", "Contatto segnalante", "Richiesta integrazione",
               "Trasmissione ad altro ente"],
}

# Ambito, elenco storico → elenco attuale (contratto, 4.1)
AMBITO_STORICO: dict[str, str] = {
    "Veterinario": "Medicina Veterinaria",
    "Igiene pubblica": "Igiene pubblica",
    "Disturbo/rumori": "Disturbo/rumori",
    "Colonia felina": "Medicina Veterinaria",
    "Allevamento/detenzione animali": "Medicina Veterinaria",
    "Altro": "Altro",
}

TEMI: list[tuple[str, str]] = [
    ("cani", "Cani"),
    ("gatti_colonie_feline", "Gatti e colonie feline"),
    ("animali_da_reddito", "Animali da reddito"),
    ("avvelenamenti", "Avvelenamenti"),
]
