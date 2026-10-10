// Shared utilities and init

document.addEventListener('DOMContentLoaded', () => {
    console.log("Sportello Esposti — App Initialized");
    seedDemoData();
});

// Helper to generate IDs
function generateId() {
    return 'URP-' + Math.random().toString(36).slice(2, 11).toUpperCase();
}

// Basic HTML-escaping for values typed by the citizen before we drop them
// into innerHTML templates (descriptions, names, attachment filenames...).
function escapeHtml(value) {
    return (value === undefined || value === null ? '' : String(value))
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// LocalStorage helpers for mock DB
const DB_KEY = 'urp_pratiche_db';

function getPratiche() {
    const data = localStorage.getItem(DB_KEY);
    return data ? JSON.parse(data) : [];
}

function savePratica(pratica) {
    const list = getPratiche();
    list.push(pratica);
    localStorage.setItem(DB_KEY, JSON.stringify(list));
}

function updatePratica(updatedInfo) {
    const list = getPratiche();
    const index = list.findIndex(p => p.id === updatedInfo.id);
    if (index !== -1) {
        list[index] = { ...list[index], ...updatedInfo };
        localStorage.setItem(DB_KEY, JSON.stringify(list));
    }
}

// Offices/operators available for assignment in the back-office panel.
// Adding a new office here makes it selectable everywhere. Offices
// suggested by the AI engine that are NOT in this list are added
// dynamically wherever needed (see operator-dashboard.js) so a brand
// new "ambito" never gets stuck without a destination.
const UFFICI_OPERATORI_BASE = [
    'Ufficio Relazioni con il Pubblico (URP)',
    'Dipartimento di Prevenzione Veterinaria',
    'Servizio Igiene degli Alimenti e della Nutrizione (SIAN)',
    'Dipartimento di Igiene e Sanità Pubblica',
    'Ufficio Ambiente ed Ecologia',
    'Ufficio Edilizia Privata e Urbanistica',
    'Ufficio Tributi',
    'Ufficio Anagrafe e Stato Civile',
    'Ufficio Trasparenza e Accesso agli Atti',
    'Comando Polizia Locale'
];

function getUfficiOperatori() {
    return UFFICI_OPERATORI_BASE.slice();
}

// Color palette used to render a consistent color for each "ambito"
// (domain) without a hardcoded CSS class per domain name. A hash of the
// ambito string picks a color from this palette, so a brand new ambito
// returned by the AI engine tomorrow renders correctly today, with zero
// code changes.
const AMBITO_PALETTE = [
    { bg: 'rgba(0, 51, 102, 0.10)', text: '#003366' },   // blu istituzionale
    { bg: 'rgba(0, 166, 90, 0.12)', text: '#00754a' },   // verde
    { bg: 'rgba(243, 156, 18, 0.15)', text: '#b9770e' }, // arancio
    { bg: 'rgba(142, 68, 173, 0.12)', text: '#6c3483' }, // viola
    { bg: 'rgba(23, 162, 184, 0.12)', text: '#117a8b' }, // ciano
    { bg: 'rgba(231, 76, 60, 0.12)', text: '#c0392b' },  // rosso
    { bg: 'rgba(52, 73, 94, 0.12)', text: '#2c3e50' },   // slate
    { bg: 'rgba(211, 84, 0, 0.12)', text: '#a04000' },   // ruggine
    { bg: 'rgba(173, 20, 87, 0.12)', text: '#ad1457' },  // magenta
    { bg: 'rgba(158, 119, 0, 0.14)', text: '#7d6608' },  // ocra
    { bg: 'rgba(40, 53, 147, 0.12)', text: '#283593' }   // indaco
];

function getColorForAmbito(ambito) {
    if (!ambito) return AMBITO_PALETTE[0];
    let hash = 0;
    for (let i = 0; i < ambito.length; i++) {
        hash = ambito.charCodeAt(i) + ((hash << 5) - hash);
    }
    return AMBITO_PALETTE[Math.abs(hash) % AMBITO_PALETTE.length];
}

// ------------------------------------------------------------------
// Codice Fiscale — structural (formal) validation.
// Implements the official check-digit algorithm (odd/even position
// value tables + remainder mod 26), not just a length/regex check.
// This only verifies the code is INTERNALLY CONSISTENT, not that it
// really belongs to the person who typed it.
// ------------------------------------------------------------------
const CF_FORMAT_REGEX = /^[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$/;

const CF_ODD_MAP = {
    '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
    'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
    'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23
};

const CF_EVEN_MAP = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19,
    'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25
};

const CF_CHECK_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

function validaCodiceFiscale(valore) {
    const cf = (valore || '').trim().toUpperCase();
    if (!CF_FORMAT_REGEX.test(cf)) return false;

    let somma = 0;
    for (let i = 0; i < 15; i++) {
        const carattere = cf[i];
        somma += (i % 2 === 0) ? CF_ODD_MAP[carattere] : CF_EVEN_MAP[carattere];
    }
    const letteraControlloAttesa = CF_CHECK_LETTERS[somma % 26];
    return letteraControlloAttesa === cf[15];
}

// ------------------------------------------------------------------
// Operatori (demo): ogni operatore è legato a un ufficio. Il ruolo
// "smistamento" vede e gestisce tutte le pratiche (è l'operatore URP
// che valuta anche la classificazione IA); il ruolo "ufficio" vede
// solo le pratiche assegnate al proprio ufficio. Login simulato via
// sessionStorage: nessuna autenticazione reale.
// ------------------------------------------------------------------
const OPERATORI_DEMO = [
    { id: 'op-urp', nome: 'Elena Colombo', ufficio: 'Ufficio Relazioni con il Pubblico (URP)', ruolo: 'smistamento' },
    { id: 'op-vet', nome: 'Dott. Marco Ferri', ufficio: 'Dipartimento di Prevenzione Veterinaria', ruolo: 'ufficio' },
    { id: 'op-sian', nome: "Dott.ssa Laura Bianchi", ufficio: 'Servizio Igiene degli Alimenti e della Nutrizione (SIAN)', ruolo: 'ufficio' },
    { id: 'op-igiene', nome: 'Dott. Andrea Villa', ufficio: 'Dipartimento di Igiene e Sanità Pubblica', ruolo: 'ufficio' },
    { id: 'op-amb', nome: 'Ing. Francesca Motta', ufficio: 'Ufficio Ambiente ed Ecologia', ruolo: 'ufficio' },
    { id: 'op-edil', nome: 'Arch. Paolo Sala', ufficio: 'Ufficio Edilizia Privata e Urbanistica', ruolo: 'ufficio' },
    { id: 'op-trib', nome: 'Rag. Chiara Longo', ufficio: 'Ufficio Tributi', ruolo: 'ufficio' },
    { id: 'op-anag', nome: 'Simone Riva', ufficio: 'Ufficio Anagrafe e Stato Civile', ruolo: 'ufficio' },
    { id: 'op-trasp', nome: 'Avv. Giulia Esposito', ufficio: 'Ufficio Trasparenza e Accesso agli Atti', ruolo: 'ufficio' },
    { id: 'op-polizia', nome: 'Isp. Davide Conti', ufficio: 'Comando Polizia Locale', ruolo: 'ufficio' }
];

const OPERATORE_SESSION_KEY = 'urp_operatore_corrente';

function getOperatoreCorrente() {
    const id = sessionStorage.getItem(OPERATORE_SESSION_KEY);
    return OPERATORI_DEMO.find(o => o.id === id) || null;
}

function setOperatoreCorrente(id) {
    sessionStorage.setItem(OPERATORE_SESSION_KEY, id);
}

function logoutOperatore() {
    sessionStorage.removeItem(OPERATORE_SESSION_KEY);
}

// ------------------------------------------------------------------
// Classificazione automatica dei DOCUMENTI allegati (MOCK).
// Scopo puramente demo: mostra all'operatore un'ipotetica etichetta
// già individuata dall'IA su ogni allegato. Deterministico (basato su
// un hash del nome file) così la stessa pratica mostra sempre la
// stessa etichetta, invece di cambiare a ogni apertura del dettaglio.
// ------------------------------------------------------------------
const TIPI_DOCUMENTO_MOCK = [
    'Documentazione fotografica',
    'Documento di identità',
    'Delega/Procura',
    'Relazione tecnica/Perizia',
    'Modulo/Istanza compilata',
    'Corrispondenza/PEC',
    'Altro documento'
];

function classificaDocumentoMock(file) {
    const nome = file.name || '';
    const nomeLower = nome.toLowerCase();

    let hash = 0;
    for (let i = 0; i < nome.length; i++) {
        hash = nome.charCodeAt(i) + ((hash << 5) - hash);
    }
    hash = Math.abs(hash);

    let tipo;
    if (nomeLower.includes('delega') || nomeLower.includes('procura')) {
        tipo = 'Delega/Procura';
    } else if (nomeLower.includes('ident') || nomeLower.includes('cie') || nomeLower.includes('carta_id')) {
        tipo = 'Documento di identità';
    } else if (nomeLower.includes('relazione') || nomeLower.includes('perizia') || nomeLower.includes('tecnic')) {
        tipo = 'Relazione tecnica/Perizia';
    } else if (file.type && file.type.startsWith('image/')) {
        tipo = 'Documentazione fotografica';
    } else if (file.type === 'application/pdf') {
        tipo = 'Modulo/Istanza compilata';
    } else {
        tipo = TIPI_DOCUMENTO_MOCK[hash % TIPI_DOCUMENTO_MOCK.length];
    }

    const confidenza = 72 + (hash % 26); // 72%-97%, stabile per lo stesso nome file
    return { tipo, confidenza: confidenza + '%' };
}

// Format a byte count as a human readable file size (e.g. "3.2 MB")
function formatFileSize(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

// Seed a handful of realistic demo records the first time the app runs,
// so the operator dashboard is never empty and already shows several
// different "ambiti" being managed side by side. Safe to delete: just
// clear localStorage (key "urp_pratiche_db") to start from zero.
function seedDemoData() {
    if (getPratiche().length > 0) return;

    const now = Date.now();
    const giorniFa = (n) => new Date(now - n * 24 * 60 * 60 * 1000).toISOString();

    const demo = [
        {
            id: 'URP-DEMO0001',
            date: giorniFa(1),
            requestType: 'esposto',
            requestTypeLabel: 'Esposto',
            citizen: 'Maria Bianchi',
            description: 'Il cane del vicino viene lasciato in cortile senza cibo né acqua da diversi giorni, sembra molto magro.',
            location: 'Via dei Platani 12, Varese (VA)',
            attachments: [{ name: 'foto_cortile.jpg', size: 245000, type: 'image/jpeg' }],
            aiResponse: {
                ambito: 'Veterinario',
                messaggio: "Stai effettuando una segnalazione in ambito veterinario? Per questa tipologia di pratica sono necessari il codice fiscale, i dati di contatto, il luogo della segnalazione e una descrizione dettagliata dell'evento.",
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Dipartimento di Prevenzione Veterinaria',
                richiede_conferma: true,
                confidenza: '94%'
            },
            ambito: 'Veterinario',
            collectedData: { 'Codice fiscale': 'BNCMRA85M41E958Y', 'Nome e cognome': 'Maria Bianchi', 'Recapito': '+39 000 0000001' },
            status: 'IN_LAVORAZIONE',
            assignedTo: 'Dipartimento di Prevenzione Veterinaria',
            internalNotes: 'Sopralluogo fissato per la prossima settimana.',
            internalNotesUpdatedAt: giorniFa(0.5),
            classificazioneIA: { confermata: true, verificatoDa: 'Elena Colombo', verificatoIl: giorniFa(0.8) }
        },
        {
            id: 'URP-DEMO0002',
            date: giorniFa(2),
            requestType: 'segnalazione',
            requestTypeLabel: 'Segnalazione',
            citizen: 'Luca Verdi',
            description: "Cumulo di rifiuti abbandonati vicino all'ingresso del parco pubblico, presente da almeno due settimane.",
            location: 'Parco Nord, Ingresso Via Bixio, Varese (VA)',
            attachments: [],
            aiResponse: {
                ambito: 'Ambiente e Igiene Urbana',
                messaggio: "La tua segnalazione sembra riguardare il decoro urbano o l'ambiente. Ci servono alcuni dati aggiuntivi per indirizzarla all'ufficio corretto.",
                dati_richiesti: ['Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Ambiente ed Ecologia',
                richiede_conferma: true,
                confidenza: '89%'
            },
            ambito: 'Ambiente e Igiene Urbana',
            collectedData: { 'Nome e cognome': 'Luca Verdi', 'Recapito': 'luca.verdi@example.com' },
            status: 'DA_VALUTARE',
            assignedTo: '',
            internalNotes: '',
            internalNotesUpdatedAt: null
        },
        {
            id: 'URP-DEMO0003',
            date: giorniFa(4),
            requestType: 'accesso_atti',
            requestTypeLabel: 'Richiesta di Accesso agli Atti (FOIA)',
            citizen: 'Studio Legale Rossi & Associati',
            description: 'Richiesta di copia della relazione di sopralluogo relativa alla pratica veterinaria n. 2024/331.',
            location: '',
            attachments: [{ name: 'delega_cliente.pdf', size: 88000, type: 'application/pdf' }],
            aiResponse: {
                ambito: 'Accesso agli Atti (FOIA)',
                messaggio: "Stai richiedendo l'accesso a documenti amministrativi. Per procedere è necessario identificarti e specificare con precisione l'atto a cui sei interessato.",
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Riferimento pratica o atto', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Trasparenza e Accesso agli Atti',
                richiede_conferma: true,
                confidenza: '91%'
            },
            ambito: 'Accesso agli Atti (FOIA)',
            collectedData: { 'Codice fiscale': 'RSSMRA75A01H501U', 'Nome e cognome': 'Avv. Marco Rossi', 'Recapito': 'studio.legale.rossi@example.com', 'Riferimento pratica o atto': '2024/331' },
            status: 'ASSEGNATA',
            assignedTo: 'Ufficio Trasparenza e Accesso agli Atti',
            internalNotes: '',
            internalNotesUpdatedAt: null,
            classificazioneIA: { confermata: true, verificatoDa: 'Elena Colombo', verificatoIl: giorniFa(3.5) }
        },
        {
            id: 'URP-DEMO0004',
            date: giorniFa(0.3),
            requestType: 'esposto',
            requestTypeLabel: 'Esposto',
            citizen: 'Giuseppe Neri',
            description: 'Sospetto ampliamento abusivo di un capannone artigianale confinante con la mia proprietà, i lavori sono iniziati la scorsa settimana senza cartelli di cantiere visibili.',
            location: 'Via Industriale 45, Gallarate (VA)',
            attachments: [
                { name: 'foto_cantiere_1.jpg', size: 512000, type: 'image/jpeg' },
                { name: 'foto_cantiere_2.jpg', size: 480000, type: 'image/jpeg' }
            ],
            aiResponse: {
                ambito: 'Edilizia e Urbanistica',
                messaggio: 'Hai segnalato un possibile caso di natura edilizia o urbanistica. Specifica ulteriori dettagli per consentire una verifica.',
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Edilizia Privata e Urbanistica',
                richiede_conferma: true,
                confidenza: '87%'
            },
            ambito: 'Edilizia e Urbanistica',
            collectedData: { 'Codice fiscale': 'NREGPP70A01D869X', 'Nome e cognome': 'Giuseppe Neri', 'Recapito': '+39 000 0000002' },
            status: 'RICEVUTA',
            assignedTo: '',
            internalNotes: '',
            internalNotesUpdatedAt: null
        },
        {
            id: 'URP-DEMO0005',
            date: giorniFa(15),
            requestType: 'segnalazione',
            requestTypeLabel: 'Segnalazione',
            citizen: 'Anna Colombo',
            description: 'Presenza di una colonia felina non censita nel cortile condominiale, chiediamo indicazioni sulla gestione sanitaria.',
            location: 'Via Manzoni 8, Busto Arsizio (VA)',
            attachments: [],
            aiResponse: {
                ambito: 'Veterinario',
                messaggio: "Stai effettuando una segnalazione in ambito veterinario? Per questa tipologia di pratica sono necessari il codice fiscale, i dati di contatto, il luogo della segnalazione e una descrizione dettagliata dell'evento.",
                dati_richiesti: ['Codice fiscale', 'Nome e cognome', 'Recapito', 'Luogo della segnalazione', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Dipartimento di Prevenzione Veterinaria',
                richiede_conferma: true,
                confidenza: '92%'
            },
            ambito: 'Veterinario',
            collectedData: { 'Codice fiscale': 'CLMNNA82T45E958K', 'Nome e cognome': 'Anna Colombo', 'Recapito': 'anna.colombo@example.com' },
            status: 'CHIUSA',
            assignedTo: 'Dipartimento di Prevenzione Veterinaria',
            internalNotes: 'Sopralluogo effettuato: colonia regolarmente censita e sterilizzata. Pratica chiusa senza ulteriori azioni.',
            internalNotesUpdatedAt: giorniFa(10)
        },
        {
            id: 'URP-DEMO0006',
            date: giorniFa(0.05),
            requestType: 'informazioni',
            requestTypeLabel: 'Richiesta di Informazioni',
            citizen: 'Paolo Ferrari',
            description: 'Vorrei sapere a chi rivolgermi per un problema che riguarda più uffici insieme, non saprei come inquadrarlo.',
            location: '',
            attachments: [],
            aiResponse: {
                ambito: 'Da Classificare',
                messaggio: "Non è stato possibile individuare con certezza l'ufficio competente. Un operatore valuterà la richiesta e la smisterà all'ufficio corretto.",
                dati_richiesti: ['Nome e cognome', 'Recapito', 'Descrizione dettagliata'],
                ufficio_destinazione: 'Ufficio Relazioni con il Pubblico (smistamento)',
                richiede_conferma: true,
                confidenza: '68%'
            },
            ambito: 'Da Classificare',
            collectedData: { 'Nome e cognome': 'Paolo Ferrari', 'Recapito': '+39 000 0000003' },
            status: 'DA_VALUTARE',
            assignedTo: 'Ufficio Relazioni con il Pubblico (URP)',
            internalNotes: "Classificazione IA non risolutiva: smistata manualmente all'URP per un primo contatto con il cittadino.",
            internalNotesUpdatedAt: giorniFa(0.02),
            classificazioneIA: { confermata: false, verificatoDa: 'Elena Colombo', verificatoIl: giorniFa(0.02) }
        }
    ];

    localStorage.setItem(DB_KEY, JSON.stringify(demo));
}
