/**
 * Sportello Esposti — AI Classification Service (MOCK)
 * ============================================================
 * This module is the ONLY place in the whole frontend that is allowed to
 * "know" anything about how a request gets classified. citizen-flow.js
 * never looks at the description text itself: it just calls
 * classificaPratica() and renders whatever structured object comes back.
 *
 * This is exactly what lets us swap the mock for a real AI engine later
 * WITHOUT touching any UI code, as long as the returned object keeps this
 * shape (as specified in the functional brief):
 *
 * {
 *   "ambito": "Veterinario",
 *   "messaggio": "Stai effettuando una segnalazione in ambito veterinario?",
 *   "dati_richiesti": ["Codice fiscale", "Nome e cognome", ...],
 *   "ufficio_destinazione": "Dipartimento di Prevenzione Veterinaria",
 *   "richiede_conferma": true,
 *   "confidenza": "94%"   // extra field, not in the original spec, optional
 * }
 */

class URPAIService {

    /**
     * Main entry point used by the frontend. Today it resolves locally with
     * a simulated delay; tomorrow it should become a real network call,
     * e.g.:
     *
     *   static classificaPratica(testo, tipoPratica) {
     *       return fetch('/api/ai/classifica', {
     *           method: 'POST',
     *           headers: { 'Content-Type': 'application/json' },
     *           body: JSON.stringify({ testo, tipoPratica })
     *       }).then(res => res.json());
     *   }
     *
     * @param {string} testo - free text description written by the citizen
     * @param {string} tipoPratica - broad request type chosen in step 1
     *        ("segnalazione" | "esposto" | "accesso_atti" | "informazioni")
     * @returns {Promise<Object>} resolves with the structured response above
     */
    static classificaPratica(testo, tipoPratica) {
        const LATENZA_MIN_MS = 900;
        const LATENZA_MAX_MS = 1700;
        // Small chance of a simulated network failure, purely so the
        // error/retry UI in citizen-flow.js is a real, reachable code path
        // and not just decoration. Remove once a real endpoint is wired up.
        const PROBABILITA_ERRORE_SIMULATO = 0.08;

        const latenza = Math.floor(Math.random() * (LATENZA_MAX_MS - LATENZA_MIN_MS + 1)) + LATENZA_MIN_MS;

        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (Math.random() < PROBABILITA_ERRORE_SIMULATO) {
                    reject(new Error('Errore simulato di rete (demo): riprovare.'));
                    return;
                }
                resolve(URPAIService._simulaClassificazione(testo, tipoPratica));
            }, latenza);
        });
    }

    // ============================================================
    // MOCK SECTION — everything below this line will be entirely replaced
    // by a real AI engine. The keyword matching here only exists to make
    // the demo credible across several different "ambiti" at once; it is
    // NOT meant to be a serious classifier. The public method above
    // (classificaPratica) and its Promise-based contract are the only
    // parts that must survive the swap.
    // ============================================================

    static _simulaClassificazione(testo, tipoPratica) {
        const t = (testo || '').toLowerCase();

        // A FOIA / access-to-documents request is defined by its
        // administrative nature, not by its subject matter, so it is
        // classified directly from the request type chosen in step 1.
        if (tipoPratica === 'accesso_atti') {
            return {
                ambito: 'Accesso agli Atti (FOIA)',
                messaggio: "Stai richiedendo l'accesso a documenti amministrativi. Per procedere è necessario identificarti e specificare con precisione l'atto o il procedimento a cui sei interessato.",
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Riferimento pratica o atto', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Trasparenza e Accesso agli Atti',
                richiede_conferma: true,
                confidenza: URPAIService._confidenzaCasuale()
            };
        }

        if (URPAIService._contieneAlcuna(t, ['cane', 'gatto', 'animal', 'veterinari', 'randag', 'maltrattament', 'zoonosi'])) {
            return {
                ambito: 'Veterinario',
                messaggio: "Stai effettuando una segnalazione in ambito veterinario? Per questa tipologia di pratica sono necessari il codice fiscale, i dati di contatto, il luogo della segnalazione e una descrizione dettagliata dell'evento.",
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Dipartimento di Prevenzione Veterinaria',
                richiede_conferma: true,
                confidenza: URPAIService._confidenzaCasuale()
            };
        }

        if (URPAIService._contieneAlcuna(t, ['rifiut', 'cassonett', 'discarica', 'degrado', 'inquinament', 'sporcizia', 'abbandon'])) {
            return {
                ambito: 'Ambiente e Igiene Urbana',
                messaggio: "La tua segnalazione sembra riguardare il decoro urbano o l'ambiente. Ci servono alcuni dati aggiuntivi per indirizzarla all'ufficio corretto.",
                dati_richiesti: ['Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Ambiente ed Ecologia',
                richiede_conferma: true,
                confidenza: URPAIService._confidenzaCasuale()
            };
        }

        if (URPAIService._contieneAlcuna(t, ['abusiv', 'edilizi', 'costruzion', 'cantiere', 'ampliamento'])) {
            return {
                ambito: 'Edilizia e Urbanistica',
                messaggio: 'Hai segnalato un possibile caso di natura edilizia o urbanistica. Specifica ulteriori dettagli per consentire una verifica.',
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Edilizia Privata e Urbanistica',
                richiede_conferma: true,
                confidenza: URPAIService._confidenzaCasuale()
            };
        }

        if (URPAIService._contieneAlcuna(t, ['tribut', 'imu ', 'tari', 'tassa', 'cartella esattoriale', 'imposta'])) {
            return {
                ambito: 'Tributi',
                messaggio: 'La tua richiesta sembra riguardare un tributo locale. Per una verifica puntuale sono necessari alcuni dati identificativi.',
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Tributi',
                richiede_conferma: true,
                confidenza: URPAIService._confidenzaCasuale()
            };
        }

        // Fallback: the mock could not confidently match a domain.
        // A human operator will triage it manually from the dashboard —
        // this is the honest behaviour we want even from a real model.
        return {
            ambito: 'Da Classificare',
            messaggio: "Non è stato possibile individuare con certezza l'ufficio competente. Un operatore dell'URP valuterà la tua richiesta e la smisterà all'ufficio corretto.",
            dati_richiesti: ['Nome e cognome', 'Recapito', 'Descrizione dettagliata'],
            ufficio_destinazione: 'Ufficio Relazioni con il Pubblico (smistamento)',
            richiede_conferma: true,
            confidenza: URPAIService._confidenzaCasuale(60, 79)
        };
    }

    static _contieneAlcuna(testo, parole) {
        return parole.some(p => testo.includes(p));
    }

    static _confidenzaCasuale(min, max) {
        min = min || 85;
        max = max || 99;
        return Math.floor(Math.random() * (max - min + 1) + min) + '%';
    }
}
