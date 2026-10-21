import type { components } from "./schema";

type S = components["schemas"];

export type Me = S["MeOut"];
export type Utente = S["UtenteOut"];
export type Ufficio = S["UfficioOut"];
export type Pratica = S["PraticaOut"];
export type PraticaRiga = S["PraticaRiga"];
export type PraticaDettaglio = S["PraticaDettaglio"];
export type Pagina = S["Pagina"];
export type Home = S["HomeOut"];
export type Fascicolo = S["FascicoloOut"];
export type Analisi = S["AnalisiOut"];
export type Avviso = S["Avviso"];
export type Valutazione = S["ValutazioneOut"];
export type ValutazioneVista = S["ValutazioneVista"];
export type ValutazioneIn = S["ValutazioneIn"];
export type TemaOut = S["TemaOut"];
export type TemaDecisione = S["TemaDecisione"];
export type Attivita = S["AttivitaOut"];
export type Collegamento = S["CollegamentoOut"];
export type TipoCollegamento = S["TipoCollegamentoOut"];
export type Passo = S["PassoPercorso"];
export type Documento = S["DocumentoOut"];
export type Nota = S["NotaOut"];
export type VoceStorico = S["VoceStorico"];
export type VoceRegistro = S["VoceRegistro"];
export type RicercaRapida = S["RicercaRapidaOut"];
export type Lavoro = S["LavoroOut"];
export type NuovaPratica = S["NuovaPraticaOut"];
export type StatoPratica = S["Stato"];
export type Ruolo = S["Ruolo"];
export type Differenza = S["Differenza"];
export type TemaCatalogo = S["TemaCatalogoOut"];

// Il backend espone scheda, proposta e temi come oggetti liberi (hanno la forma del contratto 1.1):
// qui si dà loro un tipo.
export interface VoceScheda { valore: string; frase: string; pagina: number }
export interface Scheda {
  data_doc: VoceScheda | null;
  comune: VoceScheda | null;
  ambito: VoceScheda[];
  problematica: VoceScheda[];
  elementi: VoceScheda[];
  ambito_altro?: string | null;
  problematica_altro?: string | null;
  elementi_altro?: string | null;
}
export interface Proposta {
  esito: string;
  urgenza: string;
  azione: string[];
  motivo: string;
  domanda_decisiva: string;
  da_verificare_sull_originale: string[];
}
export interface Precompilazione {
  da_risultato_id: string;
  data_doc: string | null;
  comune: string | null;
  ambito: string[];
  problematica: string[];
  elementi: string[];
  ambito_altro: string | null;
  problematica_altro: string | null;
  elementi_altro: string | null;
  esito: string | null;
  urgenza: string | null;
  azione: string[];
  note: string | null;
  valori_scartati: { campo: string; valore: string }[];
}
export interface VoceVocabolario { codice: string; etichetta: string }
export type Vocabolari = Record<string, VoceVocabolario[]>;
export interface PaginaTesto { numero: number; acquisizione: string; testo: string; lettura_incerta: boolean; motivo_incertezza: string | null }

export const comeScheda = (a: Analisi) => a.scheda as unknown as Scheda;
export const comeProposta = (a: Analisi) => a.proposta as unknown as Proposta;
export const comePrecompilazione = (v: ValutazioneVista) => v.precompilazione as unknown as Precompilazione | null;
