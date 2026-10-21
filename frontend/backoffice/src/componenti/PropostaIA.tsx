import type { Analisi } from "../api/tipi";
import { comeProposta, comeScheda } from "../api/tipi";
import { elenco } from "../formati";

/** La proposta dell'IA è un suggerimento: si mostra sempre separata dalla valutazione della persona. */
export function PropostaIA({ analisi }: { analisi: Analisi }) {
  const s = comeScheda(analisi);
  const p = comeProposta(analisi);
  const frase = s.ambito[0]?.frase ?? s.problematica[0]?.frase ?? s.elementi[0]?.frase ?? s.comune?.frase;
  const pagina = s.ambito[0]?.pagina ?? s.problematica[0]?.pagina ?? s.elementi[0]?.pagina ?? s.comune?.pagina;
  return (
    <section className="card" aria-label="Proposta dell'IA">
      <h3>Proposta dell'IA</h3>
      <div className="sottotitolo" style={{ fontSize: 14 }}>Un suggerimento: decide sempre la persona.</div>
      <dl className="dati">
        <dt>Ambito</dt><dd>{elenco(s.ambito.map((v) => v.valore))}</dd>
        <dt>Problematica</dt><dd>{elenco(s.problematica.map((v) => v.valore))}</dd>
        <dt>Elementi</dt><dd>{elenco(s.elementi.map((v) => v.valore))}</dd>
        <dt>Esito</dt><dd>{p.esito}</dd>
        <dt>Urgenza</dt><dd>{p.urgenza}</dd>
        <dt>Azione</dt><dd>{elenco(p.azione)}</dd>
      </dl>
      <h4>Perché</h4>
      <div>{p.motivo}</div>
      {p.domanda_decisiva && (<><h4>Domanda decisiva</h4><div>{p.domanda_decisiva}</div></>)}
      {frase && (<><h4>Frase del documento{pagina ? ` (pagina ${pagina})` : ""}</h4><div className="citazione">“{frase}”</div></>)}
      {p.da_verificare_sull_originale.length > 0 && (
        <>
          <h4>Da verificare sull'originale</h4>
          <ul style={{ margin: 0, paddingLeft: 20 }}>{p.da_verificare_sull_originale.map((x) => <li key={x}>{x}</li>)}</ul>
        </>
      )}
    </section>
  );
}
