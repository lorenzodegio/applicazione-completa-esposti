import { Link } from "react-router-dom";
import type { Passo } from "../api/tipi";
import { dataOra } from "../formati";
import { api } from "../api/endpoints";

/** Linea del tempo (mockup Fascicolo): passo concluso, in corso, atteso. */
export function Percorso({ passi }: { passi: Passo[] }) {
  return (
    <div>
      {passi.map((s, i) => (
        <div key={`${s.passo}-${i}`} className={`passo ${s.stato}`}>
          <div className="asse" aria-hidden="true"><div className="punto" /><div className="linea" /></div>
          <div className="contenuto">
            <div className="quando">
              {s.data ? dataOra(s.data) : "—"}
              <span className="solo-lettori"> — {s.stato === "concluso" ? "passo concluso" : s.stato === "in_corso" ? "in corso" : "atteso"}</span>
            </div>
            <div className="titolo" style={{ fontWeight: 700 }}>{s.titolo}</div>
            {s.testo && <div>{s.testo}</div>}
            {s.documento_id && (
              <a href={`${api.urlContenuto(s.documento_id)}${s.pagina ? `#page=${s.pagina}` : ""}`} target="_blank" rel="noreferrer">
                Apri il documento{s.pagina ? ` (pagina ${s.pagina})` : ""}
              </a>
            )}
            {s.pratica_collegata && (s.pratica_collegata.id
              ? <div><Link to={`/pratiche/${s.pratica_collegata.id}`}>{s.pratica_collegata.titolo ?? s.pratica_collegata.numero}</Link></div>
              : <div className="sottotitolo">Pratica {s.pratica_collegata.numero}{s.pratica_collegata.ufficio ? ` · ${s.pratica_collegata.ufficio.nome}` : ""}</div>)}
          </div>
        </div>
      ))}
      <div className="legenda" aria-hidden="true">
        <span><span className="punto" style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "var(--blu)", marginRight: 6 }} />Passo concluso</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", border: "3px solid var(--in-corso)", marginRight: 6 }} />In corso</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", border: "3px solid #b8c4cf", background: "var(--sfondo)", marginRight: 6 }} />Atteso</span>
      </div>
    </div>
  );
}
