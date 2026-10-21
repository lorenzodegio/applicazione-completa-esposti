import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api } from "../../api/endpoints";
import type { Documento, PraticaDettaglio } from "../../api/tipi";
import { Caricamento, Dialogo, MessaggioErrore, Vuoto } from "../../componenti/ui";
import { dataOra, etichettaTipo } from "../../formati";

function StatoAnalisi({ d }: { d: Documento }) {
  const a = d.analisi;
  if (!a) return <span className="tag neutro">Mai analizzato</span>;
  if (a.stato === "in_corso") return <span className="tag ambra">Analisi in corso</span>;
  if (a.stato === "completata") return <span className="tag">Analizzato</span>;
  return <span className="tag ambra">Analisi non disponibile{a.codice_errore ? ` (${a.codice_errore})` : ""}</span>;
}

function TestoDocumento({ id, onChiudi }: { id: string; onChiudi: () => void }) {
  const q = useQuery({ queryKey: ["testo", id], queryFn: () => api.testoDocumento(id) });
  return (
    <Dialogo titolo="Testo letto dal motore" onChiudi={onChiudi}>
      {q.isLoading && <Caricamento />}
      <MessaggioErrore errore={q.error} />
      <div className="pagine-testo" style={{ maxHeight: "60vh", overflow: "auto" }}>
        {q.data?.pagine.map((pg) => (
          <div key={pg.numero} className={`pagina${pg.lettura_incerta ? " incerta" : ""}`}>
            <strong>Pagina {pg.numero}</strong> <span className="sottotitolo">({pg.acquisizione.replace(/_/g, " ")})</span>
            {pg.lettura_incerta && <div role="status"><strong>Lettura incerta.</strong> {pg.motivo_incertezza}</div>}
            <div>{pg.testo}</div>
          </div>
        ))}
      </div>
      <button type="button" className="btn secondario" onClick={onChiudi}>Chiudi</button>
    </Dialogo>
  );
}

export function TabDocumenti({ p }: { p: PraticaDettaglio }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["documenti", p.id], queryFn: () => api.documenti(p.id),
    // finché c'è un'analisi in corso si riascolta il server
    refetchInterval: (query) => (query.state.data?.some((d) => d.analisi?.stato === "in_corso") ? 3000 : false),
  });
  const [testo, setTesto] = useState<string | null>(null);
  const campoFile = useRef<HTMLInputElement>(null);
  const aggiorna = () => qc.invalidateQueries();
  const rilancia = useMutation({ mutationFn: (id: string) => api.rilanciaAnalisi(id), onSuccess: aggiorna });
  const aggiungi = useMutation({
    mutationFn: (files: File[]) => api.aggiungiDocumenti(p.id, files),
    onSuccess: async () => { if (campoFile.current) campoFile.current.value = ""; await aggiorna(); },
  });

  return (
    <section className="card pila" aria-label="Documenti">
      <h2>Documenti</h2>
      {q.isLoading && <Caricamento />}
      <MessaggioErrore errore={q.error ?? rilancia.error} />
      {q.data?.length === 0 && <Vuoto>Nessun documento.</Vuoto>}
      <div className="elenco-voci">
        {q.data?.map((d) => (
          <div key={d.id} className="voce">
            <span className="corpo">
              <span className="titolo">{d.nome_file}{d.principale ? " · principale" : ""}</span>
              <span className="meta">{etichettaTipo(d.tipo_documento)} · caricato il {dataOra(d.caricato_il)} · {Math.max(1, Math.round((d.dimensione ?? 0) / 1024))} KB</span>
            </span>
            <StatoAnalisi d={d} />
            <a className="btn secondario piccolo" href={api.urlContenuto(d.id)} target="_blank" rel="noreferrer">Apri</a>
            <button type="button" className="btn secondario piccolo" onClick={() => setTesto(d.id)}>Testo letto</button>
            <button type="button" className="btn secondario piccolo" disabled={d.analisi?.stato === "in_corso" || rilancia.isPending}
              onClick={() => rilancia.mutate(d.id)}>Rianalizza</button>
          </div>
        ))}
      </div>
      <form className="pila" onSubmit={(e) => { e.preventDefault(); const f = Array.from(campoFile.current?.files ?? []); if (f.length) aggiungi.mutate(f); }}>
        <div className="campo">
          <label htmlFor="nuovi-doc">Aggiungi documenti</label>
          <input id="nuovi-doc" ref={campoFile} type="file" multiple />
        </div>
        <MessaggioErrore errore={aggiungi.error} />
        <div><button type="submit" className="btn" disabled={aggiungi.isPending}>Carica</button></div>
      </form>
      {testo && <TestoDocumento id={testo} onChiudi={() => setTesto(null)} />}
    </section>
  );
}
