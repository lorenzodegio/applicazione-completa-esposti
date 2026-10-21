import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/endpoints";
import type { PraticaDettaglio } from "../../api/tipi";
import { Caricamento, MessaggioErrore, Vuoto } from "../../componenti/ui";
import { ETICHETTA_STATO } from "../../formati";

export function TabCollegamenti({ p }: { p: PraticaDettaglio }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["collegamenti", p.id], queryFn: () => api.collegamenti(p.id) });
  const tipi = useQuery({ queryKey: ["tipi-collegamento"], queryFn: api.tipiCollegamento, staleTime: Infinity });
  const [cerca, setCerca] = useState("");
  const [scelta, setScelta] = useState("");
  const [tipo, setTipo] = useState("");
  const [nota, setNota] = useState("");
  const trovate = useQuery({
    queryKey: ["ricerca-rapida", cerca, p.id], queryFn: () => api.ricercaRapida(cerca, p.id),
    enabled: cerca.trim().length >= 2,
  });
  const aggiorna = () => qc.invalidateQueries();
  const collega = useMutation({
    mutationFn: () => api.collega(p.id, { pratica_id: scelta, tipo_id: tipo, nota: nota.trim() || null }),
    onSuccess: async () => { setCerca(""); setScelta(""); setNota(""); await aggiorna(); },
  });
  const scollega = useMutation({ mutationFn: (id: string) => api.scollega(id), onSuccess: aggiorna });
  const manuali = (tipi.data ?? []).filter((t) => t.manuale);

  return (
    <section className="card pila" aria-label="Collegamenti">
      <h2>Pratiche collegate</h2>
      {q.isLoading && <Caricamento />}
      <MessaggioErrore errore={q.error ?? scollega.error} />
      {q.data?.length === 0 && <Vuoto>Nessuna pratica collegata.</Vuoto>}
      <div className="elenco-voci">
        {q.data?.map((c, i) => (
          <div key={c.id ?? `auto-${i}`} className="voce">
            <span className="corpo">
              <span className="titolo">{c.etichetta}{c.automatico ? " (automatico)" : ""}</span>
              {c.pratica.id
                ? <span className="meta"><Link to={`/pratiche/${c.pratica.id}`}>{c.pratica.titolo}</Link> · {c.pratica.protocollo ? `Prot. ${c.pratica.protocollo} · ` : ""}{ETICHETTA_STATO[c.pratica.stato]}</span>
                : <span className="meta">Pratica {c.pratica.numero}{c.pratica.ufficio ? ` · ${c.pratica.ufficio.nome}` : ""} · {ETICHETTA_STATO[c.pratica.stato]} (di un altro ufficio: non consultabile)</span>}
              {c.nota && <span className="meta">{c.nota}</span>}
            </span>
            {c.id && <button type="button" className="btn pericolo piccolo" onClick={() => scollega.mutate(c.id!)}>Rimuovi</button>}
          </div>
        ))}
      </div>

      <form className="pila" aria-label="Nuovo collegamento" onSubmit={(e) => { e.preventDefault(); if (scelta && tipo) collega.mutate(); }}>
        <h3>Collega un'altra pratica</h3>
        <div className="campo">
          <label htmlFor="cerca-pratica">Cerca per protocollo, comune o parole</label>
          <input id="cerca-pratica" type="search" value={cerca} onChange={(e) => { setCerca(e.target.value); setScelta(""); }} />
        </div>
        {cerca.trim().length >= 2 && (
          <fieldset>
            <legend>Risultati</legend>
            {trovate.isLoading && <Caricamento />}
            {trovate.data?.length === 0 && <Vuoto>Nessuna pratica trovata (si cercano solo quelle che puoi vedere).</Vuoto>}
            {trovate.data?.map((r) => (
              <label key={r.id} className="opzione">
                <input type="radio" name="pratica-da-collegare" checked={scelta === r.id} onChange={() => setScelta(r.id)} />
                {r.titolo} — {r.protocollo ?? r.numero}{r.comune ? ` · ${r.comune}` : ""}
              </label>
            ))}
          </fieldset>
        )}
        <div className="campo">
          <label htmlFor="tipo-coll">Tipo di collegamento</label>
          <select id="tipo-coll" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">Scegli…</option>
            {manuali.map((t) => <option key={t.id} value={t.id}>{t.etichetta}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="nota-coll">Nota (facoltativa)</label>
          <input id="nota-coll" type="text" value={nota} onChange={(e) => setNota(e.target.value)} />
        </div>
        <MessaggioErrore errore={collega.error} />
        <div><button type="submit" className="btn" disabled={!scelta || !tipo || collega.isPending}>Collega</button></div>
      </form>
    </section>
  );
}
