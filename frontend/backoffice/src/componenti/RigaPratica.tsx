import { Link } from "react-router-dom";
import type { PraticaRiga } from "../api/tipi";
import { classeEsito, data } from "../formati";

/** Meta-riga «Comune · protocollo · data» comune a Home, coda Inbox ed elenchi. */
export function metaPratica(p: PraticaRiga): string {
  return [p.comune, p.protocollo ? `Prot. ${p.protocollo}` : null, data(p.data_protocollo ?? p.creata_il)]
    .filter(Boolean).join(" · ");
}

export function RigaPratica({ p, a }: { p: PraticaRiga; a?: string }) {
  const esito = p.proposta?.esito;
  return (
    <Link className="voce" to={a ?? `/pratiche/${p.id}`}>
      <span className="corpo">
        <span className="titolo">{p.titolo}</span>
        <span className="meta">{metaPratica(p)}{p.lettura_incerta ? " · lettura incerta" : ""}</span>
      </span>
      {esito && <span className={p.lettura_incerta ? "tag ambra" : classeEsito(esito)}>{p.lettura_incerta ? "Da verificare" : esito}</span>}
    </Link>
  );
}
