import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/endpoints";
import type { PraticaDettaglio } from "../../api/tipi";
import { CampiValutazione, inValutazione, moduloIniziale } from "../../componenti/ModuloValutazione";
import { PropostaIA } from "../../componenti/PropostaIA";
import { decisioniIniziali, inDecisioni, TemiDecisione } from "../../componenti/TemiDecisione";
import { MessaggioErrore } from "../../componenti/ui";
import { data, elenco, etichettaTipo } from "../../formati";

const FORMATTA = (v: unknown) => (Array.isArray(v) ? v.join(", ") : String(v ?? "—"));

export function TabRiepilogo({ p }: { p: PraticaDettaglio }) {
  const qc = useQueryClient();
  const voc = useQuery({ queryKey: ["vocabolari"], queryFn: api.vocabolari, staleTime: Infinity });
  const catalogo = useQuery({ queryKey: ["temi-catalogo"], queryFn: api.temiCatalogo, staleTime: Infinity });
  const v = p.valutazione?.valutazione ?? null;
  const modificabile = p.stato === "DA_VALIDARE" || p.stato === "IN_LAVORAZIONE";
  const [modifica, setModifica] = useState(false);
  const [m, setM] = useState(() => moduloIniziale(p));
  const [decisioni, setDecisioni] = useState(() => decisioniIniziali(p.temi));
  const [sostituisciAts, setSostituisciAts] = useState(false);
  const ats = v?.origine === "import_ats" && v.compilata;
  const aggiorna = () => qc.invalidateQueries();

  const salva = useMutation({
    mutationFn: () => api.salvaValutazione(p.id, inValutazione(m, true, sostituisciAts)),
    onSuccess: async () => { setModifica(false); await aggiorna(); },
  });
  const salvaTemi = useMutation({
    mutationFn: () => api.decidiTemi(p.id, inDecisioni(decisioni)),
    onSuccess: aggiorna,
  });

  return (
    <div className="pila">
      <div className="colonne">
        <section className="card larga" aria-label="Dati della pratica" style={{ flex: "1 1 320px" }}>
          <h2>Dati della pratica</h2>
          <dl className="dati">
            <dt>Numero</dt><dd>{p.numero}</dd>
            <dt>Protocollo</dt><dd>{p.protocollo ?? "—"}</dd>
            <dt>Data protocollo</dt><dd>{data(p.data_protocollo)}</dd>
            <dt>Tipo</dt><dd>{etichettaTipo(p.tipo)}</dd>
            <dt>Comune</dt><dd>{p.comune ?? "—"}</dd>
            <dt>Ufficio</dt><dd>{p.ufficio?.nome ?? "Non ancora assegnata"}</dd>
            <dt>Fascicoli</dt><dd>{elenco(p.temi.filter((t) => t.stato === "confermato").map((t) => t.nome))}</dd>
            <dt>Analisi</dt>
            <dd>
              {!p.stato_analisi ? "—" : p.stato_analisi.stato === "in_corso" ? "In corso"
                : p.stato_analisi.stato === "completata" ? "Completata"
                : `Non disponibile${p.stato_analisi.codice_errore ? ` (${p.stato_analisi.codice_errore})` : ""}`}
            </dd>
          </dl>
        </section>
        <div className="larga" style={{ flex: "1 1 340px" }}>
          {p.analisi && <PropostaIA analisi={p.analisi} />}
        </div>
      </div>

      {p.disaccordo.length > 0 && (
        <section className="avviso" aria-label="Disaccordo IA e operatore">
          <h2 style={{ color: "inherit" }}>IA e operatore in disaccordo</h2>
          <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
            {p.disaccordo.map((d) => (
              <li key={d.campo}><strong>{d.campo}</strong>: IA {FORMATTA(d.ia)} · operatore {FORMATTA(d.operatore)}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="card pila" aria-label="Valutazione dell'operatore">
        <div className="riga spazio">
          <h2>Valutazione dell'operatore</h2>
          {modificabile && !modifica && <button type="button" className="btn secondario piccolo" onClick={() => setModifica(true)}>Modifica</button>}
        </div>
        {!modifica && (v ? (
          <>
            <div className="sottotitolo" style={{ fontSize: 14 }}>
              {v.origine === "import_ats" ? `Valutazione ATS importata${v.autore_nome ? ` (${v.autore_nome})` : ""}` : "Compilata nell'applicazione"}
              {v.data_compilazione ? ` · ${data(v.data_compilazione)}` : ""}{v.compilata ? "" : " · bozza"}
            </div>
            <dl className="dati">
              <dt>Esito</dt><dd>{v.esito ?? "—"}</dd>
              <dt>Urgenza</dt><dd>{v.urgenza ?? "—"}</dd>
              <dt>Azione</dt><dd>{elenco(v.azione)}</dd>
              <dt>Ambito</dt><dd>{elenco(v.ambito)}</dd>
              <dt>Problematica</dt><dd>{elenco(v.problematica)}</dd>
              <dt>Elementi</dt><dd>{elenco(v.elementi)}</dd>
              {v.note && <><dt>Note</dt><dd style={{ fontWeight: 400, whiteSpace: "pre-wrap" }}>{v.note}</dd></>}
            </dl>
          </>
        ) : <div className="vuoto">Nessuna valutazione{p.stato === "DA_VALIDARE" ? ": la compili nella Inbox" : ""}.</div>)}
        {modifica && (
          <form className="pila" onSubmit={(e) => { e.preventDefault(); salva.mutate(); }}>
            {ats && (
              <div className="avviso" role="status">
                <strong>Valutazione ATS già compilata.</strong>
                <label className="opzione"><input type="checkbox" checked={sostituisciAts} onChange={(e) => setSostituisciAts(e.target.checked)} />Sostituisci la valutazione ATS</label>
              </div>
            )}
            <CampiValutazione m={m} set={setM} voc={voc.data} />
            <MessaggioErrore errore={salva.error} />
            <div className="riga">
              <button type="submit" className="btn" disabled={salva.isPending || !m.esito[0] || !m.urgenza[0] || (ats && !sostituisciAts)}>Salva la valutazione</button>
              <button type="button" className="btn secondario" onClick={() => { setModifica(false); setM(moduloIniziale(p)); }}>Annulla</button>
            </div>
          </form>
        )}
      </section>

      {modificabile && (
        <section className="card pila" aria-label="Temi della pratica">
          <TemiDecisione temi={p.temi} catalogo={catalogo.data ?? []} decisioni={decisioni} onCambia={setDecisioni} />
          <MessaggioErrore errore={salvaTemi.error} />
          <div><button type="button" className="btn secondario" disabled={salvaTemi.isPending} onClick={() => salvaTemi.mutate()}>Salva i temi</button></div>
        </section>
      )}
    </div>
  );
}
