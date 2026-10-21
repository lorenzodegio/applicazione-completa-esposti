import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type FiltriPratiche } from "../api/endpoints";
import type { PraticaRiga } from "../api/tipi";
import { Caricamento, Intestazione, MessaggioErrore, Paginazione, TagStato, Vuoto } from "../componenti/ui";
import { data, etichettaTipo, ETICHETTA_STATO } from "../formati";
import { useSessione } from "../sessione";

const PER_PAGINA = 25;
const bool = (v: string | null) => (v === "1" ? true : undefined);

function leggiFiltri(sp: URLSearchParams): FiltriPratiche {
  return {
    testo: sp.get("q") || undefined, stato: sp.get("stato") || undefined, tema: sp.get("tema") || undefined,
    con_valutazione_ats: bool(sp.get("ats")), disaccordo: bool(sp.get("disaccordo")), lettura_incerta: bool(sp.get("incerta")),
    page: Number(sp.get("p") ?? 1) || 1, per_page: PER_PAGINA,
  };
}

const testoValore = (v: unknown) => (Array.isArray(v) ? v.join(", ") : String(v ?? "—"));

function Esito({ r }: { r: PraticaRiga }) {
  if (r.valutazione?.esito) {
    return (
      <>
        <span>{r.valutazione.esito}</span>
        {r.disaccordo.map((d) => (
          <span key={d.campo} className="secondaria">IA: {d.campo} {testoValore(d.ia)}, operatore: {testoValore(d.operatore)}</span>
        ))}
      </>
    );
  }
  return r.proposta?.esito ? <span>Proposta: {r.proposta.esito}</span> : <span>—</span>;
}

export function GestionePratiche() {
  const { me } = useSessione();
  const [sp, setSp] = useSearchParams();
  const filtri = leggiFiltri(sp);
  const [testo, setTesto] = useState(sp.get("q") ?? "");
  const fascicoli = useQuery({ queryKey: ["fascicoli"], queryFn: api.fascicoli, staleTime: 30_000 });
  const q = useQuery({ queryKey: ["pratiche", filtri], queryFn: () => api.pratiche(filtri) });

  const imposta = (cambi: Record<string, string | null>) => {
    const n = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(cambi)) (v ? n.set(k, v) : n.delete(k));
    if (!("p" in cambi)) n.delete("p");
    setSp(n);
  };
  const cerca = (e: FormEvent) => { e.preventDefault(); imposta({ q: testo.trim() || null }); };
  const sotto = me?.utente.ruolo === "operatore"
    ? "Cerca una singola pratica tra tutte quelle del tuo ufficio" : "Cerca una singola pratica tra tutte quelle in archivio";

  return (
    <>
      <Intestazione titolo="Gestione pratiche" sotto={sotto} />
      <form role="search" className="card pila" onSubmit={cerca} aria-label="Ricerca pratiche">
        <div className="filtri">
          <div className="campo" style={{ flex: "2 1 260px" }}>
            <label htmlFor="q">Protocollo, comune o parole</label>
            <input id="q" type="search" value={testo} onChange={(e) => setTesto(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="stato">Stato</label>
            <select id="stato" value={sp.get("stato") ?? ""} onChange={(e) => imposta({ stato: e.target.value || null })}>
              <option value="">Tutti</option>
              {(["DA_SMISTARE", "DA_VALIDARE", "IN_LAVORAZIONE", "CHIUSA"] as const).map((s) => <option key={s} value={s}>{ETICHETTA_STATO[s]}</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="fasc">Fascicolo</label>
            <select id="fasc" value={sp.get("tema") ?? ""} onChange={(e) => imposta({ tema: e.target.value || null })}>
              <option value="">Tutti</option>
              {fascicoli.data?.map((f) => <option key={f.codice} value={f.codice}>{f.nome}</option>)}
            </select>
          </div>
          <button type="submit" className="btn">Cerca</button>
        </div>
        <div className="opzioni">
          {([["ats", "Con valutazione ATS"], ["disaccordo", "IA e operatore in disaccordo"], ["incerta", "Lettura incerta"]] as const).map(([k, et]) => (
            <label key={k} className="opzione">
              <input type="checkbox" checked={sp.get(k) === "1"} onChange={(e) => imposta({ [k]: e.target.checked ? "1" : null })} />{et}
            </label>
          ))}
        </div>
      </form>

      <MessaggioErrore errore={q.error} />
      {q.isLoading && <Caricamento />}
      {q.data && (
        <section className="card" aria-label="Risultati">
          <div role="status" style={{ marginBottom: 8 }}>{q.data.total} {q.data.total === 1 ? "pratica trovata" : "pratiche trovate"}</div>
          {q.data.items.length === 0 ? <Vuoto>Nessuna pratica con questi filtri.</Vuoto> : (
            <div className="scorrevole">
              <table className="tabella">
                <thead><tr>
                  {["Protocollo", "Pratica", "Tipo", "Fascicolo", "Stato", "Esito", "Collegate"].map((c) => <th key={c} scope="col">{c}</th>)}
                </tr></thead>
                <tbody>
                  {q.data.items.map((r) => (
                    <tr key={r.id}>
                      <td><Link to={`/pratiche/${r.id}`}>{r.protocollo ?? r.numero}</Link></td>
                      <td><strong>{r.titolo}</strong><span className="secondaria">{data(r.data_protocollo ?? r.creata_il)}{r.comune ? ` · ${r.comune}` : ""}</span></td>
                      <td>{etichettaTipo(r.tipo)}</td>
                      <td>{r.temi.length ? r.temi.join(", ") : "—"}</td>
                      <td><TagStato stato={r.stato} /></td>
                      <td><Esito r={r} /></td>
                      <td>{r.n_collegate ? r.n_collegate : "Nessuna"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Paginazione pagina={q.data.page} totale={q.data.total} perPagina={PER_PAGINA} onCambia={(p) => imposta({ p: String(p) })} />
        </section>
      )}
    </>
  );
}
