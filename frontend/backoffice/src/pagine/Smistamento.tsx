import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { PraticaRiga } from "../api/tipi";
import { AssegnaUfficio } from "../componenti/AssegnaUfficio";
import { CaricaDocumenti } from "../componenti/CaricaDocumenti";
import { metaPratica } from "../componenti/RigaPratica";
import { Caricamento, Intestazione, MessaggioErrore, Vuoto } from "../componenti/ui";
import { classeEsito } from "../formati";

export function Smistamento() {
  const q = useQuery({ queryKey: ["smistamento"], queryFn: () => api.smistamento() });
  const [assegna, setAssegna] = useState<PraticaRiga | null>(null);
  return (
    <>
      <Intestazione titolo="Smistamento" sotto={q.data ? `${q.data.total} ${q.data.total === 1 ? "pratica" : "pratiche"} da assegnare a un ufficio` : "Pratiche da assegnare a un ufficio"} />
      <CaricaDocumenti />
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
