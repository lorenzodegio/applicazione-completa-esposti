import type { PraticaDettaglio, ValutazioneIn, Vocabolari } from "../api/tipi";
import { comePrecompilazione } from "../api/tipi";
import { Opzioni } from "./ui";

export interface Modulo {
  esito: string[]; urgenza: string[]; azione: string[];
  ambito: string[]; problematica: string[]; elementi: string[];
  comune: string; dataDoc: string; note: string;
  // testi liberi che il modulo non modifica ma non deve perdere
  altro: { ambito_altro: string | null; problematica_altro: string | null; elementi_altro: string | null };
}

/** Versione della valutazione salvata (null se non c'è ancora): va rimandata a ogni salvataggio. */
export const versioneValutazione = (p: PraticaDettaglio): number | null => p.valutazione?.valutazione?.versione ?? null;

const uno = (v?: string | null) => (v ? [v] : []);

/** Valutazione già salvata → altrimenti proposta dell'IA (precompilazione). Una bozza si completa con la proposta. */
export function moduloIniziale(p: PraticaDettaglio): Modulo {
  const v = p.valutazione?.valutazione ?? null;
  const pre = p.valutazione ? comePrecompilazione(p.valutazione) : null;
  const compilata = !!v?.compilata;
  const lista = (mia?: string[] | null, ia?: string[] | null) => (compilata || (mia && mia.length) ? (mia ?? []) : (ia ?? []));
  const scalare = (mio?: string | null, ia?: string | null) => (compilata || mio ? (mio ?? "") : (ia ?? ""));
  return {
    esito: uno(compilata || v?.esito ? v?.esito : pre?.esito),
    urgenza: uno(compilata || v?.urgenza ? v?.urgenza : pre?.urgenza),
    azione: lista(v?.azione, pre?.azione),
    ambito: lista(v?.ambito, pre?.ambito),
    problematica: lista(v?.problematica, pre?.problematica),
    elementi: lista(v?.elementi, pre?.elementi),
    comune: scalare(v?.comune, pre?.comune),
    dataDoc: scalare(v?.data_doc, pre?.data_doc),
    note: v?.note ?? "",
    altro: {
      ambito_altro: v?.ambito_altro ?? pre?.ambito_altro ?? null,
      problematica_altro: v?.problematica_altro ?? pre?.problematica_altro ?? null,
      elementi_altro: v?.elementi_altro ?? pre?.elementi_altro ?? null,
    },
  };
}

/** Corpo della richiesta. `versione` è quella letta: se nel frattempo è cambiata il server risponde 409. */
export function inValutazione(m: Modulo, compilata: boolean, sostituisciAts: boolean, versione: number | null): ValutazioneIn {
  return {
    data_doc: m.dataDoc || null,
    comune: m.comune.trim() || null,
    ambito: m.ambito, problematica: m.problematica, elementi: m.elementi,
    ...m.altro,
    esito: m.esito[0] ?? null,
    urgenza: m.urgenza[0] ?? null,
    azione: m.azione,
    note: m.note.trim() || null,
    compilata,
    conferma_sovrascrittura: sostituisciAts,
    versione,
  };
}

export const MESSAGGIO_CONFLITTO =
  "Un'altra persona ha salvato questa valutazione mentre la compilavi. Qui sotto c'è la versione aggiornata: controllala e, se serve, rifai le tue modifiche.";

const voci = (voc: Vocabolari | undefined, nome: string) => (voc?.[nome] ?? []).map((x) => x.codice);

export function CampiValutazione({ m, set, voc }: { m: Modulo; set: (m: Modulo) => void; voc?: Vocabolari }) {
  const agg = (parziale: Partial<Modulo>) => set({ ...m, ...parziale });
  return (
    <>
      <Opzioni legenda="Esito" nome="esito" tipo="radio" voci={voci(voc, "esito")} valore={m.esito} onCambia={(esito) => agg({ esito })} />
      <Opzioni legenda="Livello di urgenza" nome="urgenza" tipo="radio" voci={voci(voc, "urgenza")} valore={m.urgenza} onCambia={(urgenza) => agg({ urgenza })} />
      <Opzioni legenda="Azione consigliata" nome="azione" tipo="checkbox" voci={voci(voc, "azione")} valore={m.azione} onCambia={(azione) => agg({ azione })} />
      <details>
        <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 600 }}>Altri dati della scheda</summary>
        <div className="pila">
          <Opzioni legenda="Ambito" nome="ambito" tipo="checkbox" voci={voci(voc, "ambito")} valore={m.ambito} onCambia={(ambito) => agg({ ambito })} />
          <Opzioni legenda="Problematica" nome="problematica" tipo="checkbox" voci={voci(voc, "problematica")} valore={m.problematica} onCambia={(problematica) => agg({ problematica })} />
          <Opzioni legenda="Elementi" nome="elementi" tipo="checkbox" voci={voci(voc, "elementi")} valore={m.elementi} onCambia={(elementi) => agg({ elementi })} />
          <div className="riga">
            <div className="campo" style={{ flex: "1 1 220px" }}>
              <label htmlFor="comune">Comune</label>
              <input id="comune" type="text" value={m.comune} onChange={(e) => agg({ comune: e.target.value })} />
            </div>
            <div className="campo" style={{ flex: "1 1 220px" }}>
              <label htmlFor="data-doc">Data del documento</label>
              <input id="data-doc" type="date" value={m.dataDoc} onChange={(e) => agg({ dataDoc: e.target.value })} />
            </div>
          </div>
        </div>
      </details>
      <div className="campo">
        <label htmlFor="note">Note</label>
        <textarea id="note" rows={3} value={m.note} onChange={(e) => agg({ note: e.target.value })} />
      </div>
    </>
  );
}
