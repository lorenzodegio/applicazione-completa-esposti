import { del, get, invia, patch, post, put } from "./client";
import type * as T from "./tipi";
import type { components } from "./schema";

type S = components["schemas"];
export type FiltriPratiche = {
  testo?: string; stato?: string; tema?: string; tipo?: string;
  con_valutazione_ats?: boolean; disaccordo?: boolean; lettura_incerta?: boolean;
  dal?: string; al?: string; page?: number; per_page?: number;
};

export const api = {
  // accesso
  login: (username: string, password: string) => post<T.Me>("/auth/login", { username, password }),
  logout: () => post<void>("/auth/logout"),
  me: () => get<T.Me>("/auth/me"),
  // schermate
  home: () => get<T.Home>("/home"),
  inbox: (page = 1) => get<T.Pagina>("/inbox", { page, per_page: 50 }),
  smistamento: (page = 1) => get<T.Pagina>("/smistamento", { page, per_page: 50 }),
  pratiche: (f: FiltriPratiche) => get<T.Pagina>("/pratiche", f),
  fascicoli: () => get<T.Fascicolo[]>("/fascicoli"),
  praticheFascicolo: (codice: string, page = 1) => get<T.Pagina>(`/fascicoli/${codice}/pratiche`, { page, per_page: 50 }),
  ricercaRapida: (q: string, escludi?: string) => get<T.RicercaRapida[]>("/pratiche/ricerca-rapida", { q, escludi }),
  // configurazione
  vocabolari: () => get<T.Vocabolari>("/vocabolari"),
  temiCatalogo: () => get<T.TemaCatalogo[]>("/temi"),
  tipiCollegamento: () => get<T.TipoCollegamento[]>("/tipi-collegamento"),
  uffici: () => get<T.Ufficio[]>("/uffici"),
  // pratica
  pratica: (id: string) => get<T.PraticaDettaglio>(`/pratiche/${id}`),
  valutazione: (id: string) => get<T.ValutazioneVista>(`/pratiche/${id}/valutazione`),
  salvaValutazione: (id: string, v: T.ValutazioneIn) => put<T.Valutazione>(`/pratiche/${id}/valutazione`, v),
  valida: (id: string, corpo: S["ValidazioneIn"]) => post<T.Pratica>(`/pratiche/${id}/validazione`, corpo),
  restituisci: (id: string, versione: number, motivo: string) => post<T.Pratica>(`/pratiche/${id}/restituzione`, { versione, motivo }),
  assegna: (id: string, corpo: S["AssegnazioneIn"]) => post<T.Pratica>(`/pratiche/${id}/assegnazione`, corpo),
  cambiaStato: (id: string, versione: number, a_stato: T.StatoPratica, motivo?: string) =>
    post<T.Pratica>(`/pratiche/${id}/stato`, { versione, a_stato, motivo }),
  modificaPratica: (id: string, corpo: S["PraticaPatch"]) => patch<T.Pratica>(`/pratiche/${id}`, corpo),
  temi: (id: string) => get<T.TemaOut[]>(`/pratiche/${id}/temi`),
  decidiTemi: (id: string, temi: T.TemaDecisione[]) => put<T.TemaOut[]>(`/pratiche/${id}/temi`, { temi }),
  percorso: (id: string) => get<T.Passo[]>(`/pratiche/${id}/percorso`),
  storico: (id: string) => get<T.VoceStorico[]>(`/pratiche/${id}/storico`),
  registro: (id: string) => get<T.VoceRegistro[]>(`/pratiche/${id}/registro`),
  note: (id: string) => get<T.Nota[]>(`/pratiche/${id}/note`),
  nuovaNota: (id: string, testo: string) => post<T.Nota>(`/pratiche/${id}/note`, { testo }),
  attivita: (id: string) => get<T.Attivita[]>(`/pratiche/${id}/attivita`),
  nuovaAttivita: (id: string, corpo: S["AttivitaIn"]) => post<T.Attivita>(`/pratiche/${id}/attivita`, corpo),
  modificaAttivita: (aid: string, corpo: S["AttivitaPatch"]) => patch<T.Attivita>(`/attivita/${aid}`, corpo),
  collegamenti: (id: string) => get<T.Collegamento[]>(`/pratiche/${id}/collegamenti`),
  collega: (id: string, corpo: S["CollegamentoIn"]) => post<T.Collegamento>(`/pratiche/${id}/collegamenti`, corpo),
  scollega: (cid: string) => del<void>(`/collegamenti/${cid}`),
  // documenti e motore
  documenti: (id: string) => get<T.Documento[]>(`/pratiche/${id}/documenti`),
  analisiDocumento: (did: string) => get<T.Analisi[]>(`/documenti/${did}/analisi`),
  rilanciaAnalisi: (did: string) => post<T.Lavoro>(`/documenti/${did}/analisi`),
  testoDocumento: (did: string) => get<{ documento_id: string; pagine: T.PaginaTesto[] }>(`/documenti/${did}/testo`),
  urlContenuto: (did: string) => `/api/v1/documenti/${did}/contenuto`,
  nuovaPratica: (files: File[], campi: { titolo?: string; protocollo?: string; comune?: string }) => {
    const f = new FormData();
    files.forEach((x) => f.append("files", x));
    Object.entries(campi).forEach(([k, v]) => v && f.append(k, v));
    return invia<T.NuovaPratica>("/pratiche", f);
  },
  aggiungiDocumenti: (id: string, files: File[]) => {
    const f = new FormData();
    files.forEach((x) => f.append("files", x));
    return invia<T.Documento[]>(`/pratiche/${id}/documenti`, f);
  },
  // amministrazione
  utenti: () => get<T.Utente[]>("/utenti"),
  creaUtente: (corpo: S["UtenteIn"]) => post<T.Utente>("/utenti", corpo),
  modificaUtente: (id: string, corpo: S["UtentePatch"]) => patch<T.Utente>(`/utenti/${id}`, corpo),
  reimpostaPassword: (id: string, password: string) => post<void>(`/utenti/${id}/password`, { password }),
  creaUfficio: (corpo: S["UfficioIn"]) => post<T.Ufficio>("/uffici", corpo),
  modificaUfficio: (id: string, corpo: S["UfficioPatch"]) => patch<T.Ufficio>(`/uffici/${id}`, corpo),
};
