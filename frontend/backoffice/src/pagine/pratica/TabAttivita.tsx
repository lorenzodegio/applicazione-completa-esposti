import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/endpoints";
import type { PraticaDettaglio } from "../../api/tipi";
import { Caricamento, MessaggioErrore, Vuoto } from "../../componenti/ui";
import { data } from "../../formati";

const ETICHETTA = { prevista: "Prevista", in_corso: "In corso", conclusa: "Conclusa", annullata: "Annullata" } as const;

export function TabAttivita({ p }: { p: PraticaDettaglio }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["attivita", p.id], queryFn: () => api.attivita(p.id) });
  const voc = useQuery({ queryKey: ["vocabolari"], queryFn: api.vocabolari, staleTime: Infinity });
  const [tipo, setTipo] = useState("");
  const [prevista, setPrevista] = useState("");
  const [descrizione, setDescrizione] = useState("");
  const aggiorna = () => qc.invalidateQueries();
  const crea = useMutation({
    mutationFn: () => api.nuovaAttivita(p.id, { tipo, data_prevista: prevista || null, descrizione: descrizione.trim() || null }),
    onSuccess: async () => { setTipo(""); setPrevista(""); setDescrizione(""); await aggiorna(); },
  });
  const cambia = useMutation({
    mutationFn: (v: { id: string; stato: "in_corso" | "conclusa" | "annullata" }) => api.modificaAttivita(v.id, { stato: v.stato }),
    onSuccess: aggiorna,
  });
  const aperta = p.stato === "IN_LAVORAZIONE";

  return (
    <section className="card pila" aria-label="Attività">
      <h2>Azioni dell'ufficio</h2>
      {q.isLoading && <Caricamento />}
      <MessaggioErrore errore={q.error ?? cambia.error} />
      {q.data?.length === 0 && <Vuoto>Nessuna azione registrata.</Vuoto>}
      <div className="elenco-voci">
        {q.data?.map((a) => (
          <div key={a.id} className="voce">
            <span className="corpo">
              <span className="titolo">{a.tipo}</span>
              <span className="meta">
                {ETICHETTA[a.stato]}{a.data_prevista ? ` · prevista il ${data(a.data_prevista)}` : ""}{a.data_conclusione ? ` · conclusa il ${data(a.data_conclusione)}` : ""}
                {a.descrizione ? ` · ${a.descrizione}` : ""}
              </span>
            </span>
            {aperta && a.stato === "prevista" && <button type="button" className="btn secondario piccolo" onClick={() => cambia.mutate({ id: a.id, stato: "in_corso" })}>Avvia</button>}
            {aperta && (a.stato === "prevista" || a.stato === "in_corso") && (
              <>
                <button type="button" className="btn piccolo" onClick={() => cambia.mutate({ id: a.id, stato: "conclusa" })}>Concludi</button>
                <button type="button" className="btn pericolo piccolo" onClick={() => cambia.mutate({ id: a.id, stato: "annullata" })}>Annulla</button>
              </>
            )}
          </div>
        ))}
      </div>
      {aperta ? (
        <form className="pila" aria-label="Nuova azione" onSubmit={(e) => { e.preventDefault(); if (tipo) crea.mutate(); }}>
          <h3>Aggiungi un'azione</h3>
          <div className="filtri">
            <div className="campo">
              <label htmlFor="tipo-att">Tipo</label>
              <select id="tipo-att" value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="">Scegli…</option>
                {voc.data?.["azione"]?.map((v) => <option key={v.codice} value={v.codice}>{v.etichetta}</option>)}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="prevista">Data prevista</label>
              <input id="prevista" type="date" value={prevista} onChange={(e) => setPrevista(e.target.value)} />
            </div>
          </div>
          <div className="campo">
            <label htmlFor="desc-att">Descrizione (facoltativa)</label>
            <input id="desc-att" type="text" value={descrizione} onChange={(e) => setDescrizione(e.target.value)} />
          </div>
          <MessaggioErrore errore={crea.error} />
          <div><button type="submit" className="btn" disabled={!tipo || crea.isPending}>Aggiungi</button></div>
        </form>
      ) : <div className="sottotitolo" style={{ fontSize: 14 }}>Le azioni si aggiungono quando la pratica è in lavorazione.</div>}
    </section>
  );
}
