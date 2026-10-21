import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { NuovaPratica, PraticaRiga } from "../api/tipi";
import { AssegnaUfficio } from "../componenti/AssegnaUfficio";
import { metaPratica } from "../componenti/RigaPratica";
import { Caricamento, Intestazione, MessaggioErrore, Vuoto } from "../componenti/ui";
import { classeEsito } from "../formati";

export function Smistamento() {
  const q = useQuery({ queryKey: ["smistamento"], queryFn: () => api.smistamento() });
  const [assegna, setAssegna] = useState<PraticaRiga | null>(null);
  return (
    <>
      <Intestazione titolo="Smistamento" sotto={q.data ? `${q.data.total} ${q.data.total === 1 ? "pratica" : "pratiche"} da assegnare a un ufficio` : "Pratiche da assegnare a un ufficio"} />
      <NuovoEsposto />
      <section className="card" aria-label="Da smistare">
        <h2>Da smistare</h2>
        {q.isLoading && <Caricamento />}
        <MessaggioErrore errore={q.error} />
        {q.data?.items.length === 0 && <Vuoto>Nessuna pratica in attesa di smistamento.</Vuoto>}
        <div className="elenco-voci">
          {q.data?.items.map((r) => (
            <div key={r.id} className="voce">
              <span className="corpo">
                <Link className="titolo" to={`/pratiche/${r.id}`}>{r.titolo}</Link>
                <span className="meta">{metaPratica(r)}{r.lettura_incerta ? " · lettura incerta" : ""}</span>
              </span>
              {r.proposta?.esito && <span className={classeEsito(r.proposta.esito)}>Proposta: {r.proposta.esito}</span>}
              <button type="button" className="btn piccolo" onClick={() => setAssegna(r)}>Assegna</button>
            </div>
          ))}
        </div>
      </section>
      {assegna && <AssegnaUfficio pratica={assegna} onChiudi={() => setAssegna(null)} />}
    </>
  );
}

function NuovoEsposto() {
  const qc = useQueryClient();
  const file = useRef<HTMLInputElement>(null);
  const [titolo, setTitolo] = useState("");
  const [protocollo, setProtocollo] = useState("");
  const [comune, setComune] = useState("");
  const [creata, setCreata] = useState<NuovaPratica | null>(null);
  const carica = useMutation({
    mutationFn: (files: File[]) => api.nuovaPratica(files, { titolo: titolo.trim(), protocollo: protocollo.trim(), comune: comune.trim() }),
    onSuccess: async (r) => {
      setCreata(r); setTitolo(""); setProtocollo(""); setComune("");
      if (file.current) file.current.value = "";
      await qc.invalidateQueries();
    },
  });
  return (
    <details className="card">
      <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 700, fontSize: 18 }}>Carica un nuovo esposto</summary>
      <form className="pila" onSubmit={(e) => { e.preventDefault(); const f = Array.from(file.current?.files ?? []); if (f.length) { setCreata(null); carica.mutate(f); } }}>
        <div className="campo">
          <label htmlFor="file-esposto">Documenti (anche più di uno)</label>
          <input id="file-esposto" ref={file} type="file" multiple required />
        </div>
        <div className="filtri">
          <div className="campo"><label htmlFor="n-titolo">Titolo (facoltativo)</label><input id="n-titolo" type="text" value={titolo} onChange={(e) => setTitolo(e.target.value)} /></div>
          <div className="campo"><label htmlFor="n-prot">Protocollo (facoltativo)</label><input id="n-prot" type="text" value={protocollo} onChange={(e) => setProtocollo(e.target.value)} /></div>
          <div className="campo"><label htmlFor="n-com">Comune (facoltativo)</label><input id="n-com" type="text" value={comune} onChange={(e) => setComune(e.target.value)} /></div>
        </div>
        <MessaggioErrore errore={carica.error} />
        {creata && <div role="status" className="ok">Pratica {creata.pratica.numero} creata: il motore sta analizzando {creata.documenti.length === 1 ? "il documento" : "i documenti"}. <Link to={`/pratiche/${creata.pratica.id}`}>Aprila</Link></div>}
        <div><button type="submit" className="btn" disabled={carica.isPending}>{carica.isPending ? "Caricamento…" : "Carica e analizza"}</button></div>
      </form>
    </details>
  );
}
