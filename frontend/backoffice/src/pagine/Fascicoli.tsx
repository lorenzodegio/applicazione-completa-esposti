import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { Percorso } from "../componenti/Percorso";
import { Caricamento, Intestazione, MessaggioErrore, Paginazione, TagStato, Vuoto } from "../componenti/ui";
import { data } from "../formati";
import { useState } from "react";

export function Fascicoli() {
  const { codice } = useParams();
  const fascicoli = useQuery({ queryKey: ["fascicoli"], queryFn: api.fascicoli });
  if (fascicoli.isLoading) return <Caricamento />;
  if (fascicoli.error) return <MessaggioErrore errore={fascicoli.error} />;
  const elenco = fascicoli.data ?? [];
  if (!codice && elenco[0]) return <Navigate to={`/fascicoli/${elenco[0].codice}`} replace />;
  const corrente = elenco.find((f) => f.codice === codice);
  return (
    <>
      <Intestazione
        titolo={corrente ? `Fascicolo: ${corrente.nome}` : "Fascicoli"}
        briciole={corrente ? <><Link to="/fascicoli">Fascicoli</Link> / {corrente.nome}</> : undefined}
        sotto={corrente ? `${corrente.pratiche} ${corrente.pratiche === 1 ? "pratica collegata" : "pratiche collegate"} per tema · dalla più vecchia alla più recente` : "Le pratiche raccolte per tema"}
      />
      <nav className="riga" aria-label="Fascicoli">
        {elenco.map((f) => (
          <Link key={f.codice} to={`/fascicoli/${f.codice}`} className={f.codice === codice ? "btn piccolo" : "btn secondario piccolo"}
            aria-current={f.codice === codice ? "page" : undefined}>{f.nome} · {f.pratiche}</Link>
        ))}
      </nav>
      {corrente && <Contenuto codice={corrente.codice} />}
    </>
  );
}

function Contenuto({ codice }: { codice: string }) {
  const [sp, setSp] = useSearchParams();
  const navigate = useNavigate();
  const [pagina, setPagina] = useState(1);
  const q = useQuery({ queryKey: ["fascicolo", codice, pagina], queryFn: () => api.praticheFascicolo(codice, pagina) });
  const scelta = sp.get("pratica") ?? q.data?.items[0]?.id;
  const percorso = useQuery({ queryKey: ["percorso", scelta], queryFn: () => api.percorso(scelta!), enabled: !!scelta });
  const attuale = q.data?.items.find((p) => p.id === scelta);
  return (
    <div className="colonne">
      <section className="card larga" aria-label="Percorso del fascicolo" style={{ flex: "1 1 320px" }}>
        <h2 style={{ marginBottom: 12 }}>Percorso del fascicolo</h2>
        {q.isLoading && <Caricamento />}
        <MessaggioErrore errore={q.error} />
        {q.data?.items.length === 0 && <Vuoto>Nessuna pratica in questo fascicolo.</Vuoto>}
        {q.data?.items.map((p) => (
          <div key={p.id} className={`passo ${p.id === scelta ? "concluso" : "atteso"}`}>
            <div className="asse" aria-hidden="true"><div className="punto" /><div className="linea" /></div>
            <div className="contenuto">
              <button type="button" onClick={() => setSp({ pratica: p.id })} aria-pressed={p.id === scelta}
                style={{ all: "unset", cursor: "pointer", display: "block", minHeight: 44 }}>
                <span className="quando" style={{ display: "block" }}>{data(p.data_protocollo ?? p.creata_il)}{p.protocollo ? ` · Prot. ${p.protocollo}` : ""}</span>
                <span style={{ display: "block", fontWeight: 700, color: p.id === scelta ? "var(--blu)" : "inherit" }}>{p.titolo}</span>
                <span style={{ display: "block", fontSize: 14 }}><TagStato stato={p.stato} /></span>
              </button>
            </div>
          </div>
        ))}
        {q.data && <Paginazione pagina={q.data.page} totale={q.data.total} perPagina={q.data.per_page} onCambia={setPagina} />}
      </section>
      <section className="card larga" aria-label="Storico della pratica" style={{ flex: "1 1 360px" }}>
        {attuale ? (
          <>
            <div className="riga spazio">
              <div>
                <div className="sottotitolo" style={{ fontSize: 14 }}>{attuale.protocollo ? `Prot. ${attuale.protocollo}` : attuale.numero}{attuale.comune ? ` · ${attuale.comune}` : ""}</div>
                <h2>{attuale.titolo}</h2>
              </div>
              <button type="button" className="btn secondario piccolo" onClick={() => navigate(`/pratiche/${attuale.id}`)}>Apri la pratica</button>
            </div>
            <div style={{ marginTop: 16 }}>
              {percorso.isLoading && <Caricamento />}
              <MessaggioErrore errore={percorso.error} />
              {percorso.data && <Percorso passi={percorso.data} />}
            </div>
          </>
        ) : <Vuoto>Scegli una pratica per vederne lo storico.</Vuoto>}
      </section>
    </div>
  );
}
