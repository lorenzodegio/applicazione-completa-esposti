import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { eConflittoValutazione } from "../api/client";
import { api } from "../api/endpoints";
import type { PraticaDettaglio, PraticaRiga } from "../api/tipi";
import {
  CampiValutazione, inValutazione, MESSAGGIO_CONFLITTO, moduloIniziale, versioneValutazione, type Modulo,
} from "../componenti/ModuloValutazione";
import { PropostaIA } from "../componenti/PropostaIA";
import { decisioniIniziali, inDecisioni, TemiDecisione, type Decisioni } from "../componenti/TemiDecisione";
import { Avvisi, Caricamento, Dialogo, Intestazione, MessaggioErrore, Vuoto } from "../componenti/ui";
import { data } from "../formati";
import { useSessione } from "../sessione";

export function Inbox() {
  const { id } = useParams();
  const coda = useQuery({ queryKey: ["inbox"], queryFn: () => api.inbox() });
  const righe = coda.data?.items ?? [];

  // senza pratica scelta si apre la prima della coda
  if (!id && righe[0]) return <Navigate to={`/inbox/${righe[0].id}`} replace />;

  return (
    <>
      <Intestazione titolo="Inbox" sotto={coda.data ? `${coda.data.total} ${coda.data.total === 1 ? "esposto" : "esposti"} da validare, uno alla volta` : "Esposti da validare"} />
      <MessaggioErrore errore={coda.error} />
      {coda.isLoading && <Caricamento />}
      {coda.data && righe.length === 0 && <div className="card"><Vuoto>Nessun esposto da validare. Ottimo lavoro.</Vuoto></div>}
      {righe.length > 0 && (
        <div className="inbox">
          <section aria-label="Coda" className="coda">
            {righe.map((r) => <VoceCoda key={r.id} r={r} corrente={r.id === id} />)}
          </section>
          {id ? <Validazione key={id} id={id} coda={righe} /> : null}
        </div>
      )}
    </>
  );
}

function VoceCoda({ r, corrente }: { r: PraticaRiga; corrente: boolean }) {
  const proposta = r.proposta?.esito
    ? `proposta: ${r.proposta.esito}${r.proposta.urgenza && r.proposta.urgenza !== "Normale" ? `, urgenza ${r.proposta.urgenza}` : ""}`
    : "senza proposta";
  return (
    <Link to={`/inbox/${r.id}`} aria-current={corrente ? "true" : undefined}>
      <span className="titolo" style={{ display: "block", fontWeight: 700 }}>{r.titolo}</span>
      <span className="meta" style={{ display: "block", fontSize: 14, color: "var(--testo-secondario)" }}>
        {[r.comune, r.lettura_incerta ? "lettura incerta" : proposta].filter(Boolean).join(" · ")}
      </span>
    </Link>
  );
}

function Validazione({ id, coda }: { id: string; coda: PraticaRiga[] }) {
  const p = useQuery({ queryKey: ["pratica", id], queryFn: () => api.pratica(id) });
  const voc = useQuery({ queryKey: ["vocabolari"], queryFn: api.vocabolari, staleTime: Infinity });
  const catalogo = useQuery({ queryKey: ["temi-catalogo"], queryFn: api.temiCatalogo, staleTime: Infinity });
  if (p.isLoading || voc.isLoading) return <Caricamento />;
  if (p.error) return <MessaggioErrore errore={p.error} />;
  if (!p.data) return null;
  return <Scheda p={p.data} coda={coda} voc={voc.data} catalogo={catalogo.data ?? []} />;
}

function Scheda({ p, coda, voc, catalogo }: {
  p: PraticaDettaglio; coda: PraticaRiga[]; voc?: Awaited<ReturnType<typeof api.vocabolari>>;
  catalogo: Awaited<ReturnType<typeof api.temiCatalogo>>;
}) {
  const { me } = useSessione();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [m, setM] = useState<Modulo>(() => moduloIniziale(p));
  const [decisioni, setDecisioni] = useState<Decisioni>(() => decisioniIniziali(p.temi));
  const [sostituisciAts, setSostituisciAts] = useState(false);
  const [restituisci, setRestituisci] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [salvata, setSalvata] = useState(false);
  const [versione, setVersione] = useState(() => versioneValutazione(p));
  const [conflitto, setConflitto] = useState(false);

  // la pratica si ricarica dopo una modifica: il modulo riparte dai dati nuovi solo al cambio di pratica (key)
  useEffect(() => setSalvata(false), [m, decisioni]);

  const ats = p.valutazione?.valutazione?.origine === "import_ats" && p.valutazione.valutazione.compilata;
  const prossimo = () => {
    const i = coda.findIndex((r) => r.id === p.id);
    const altro = coda[i + 1] ?? coda[i - 1];
    navigate(altro ? `/inbox/${altro.id}` : "/inbox", { replace: true });
  };
  const aggiorna = () => qc.invalidateQueries();
  // 409 «valutazione_modificata»: si ricarica la valutazione salvata da altri e si riparte da quella
  const dopoErrore = async (e: unknown) => {
    if (!eConflittoValutazione(e)) return;
    const nuova = await qc.fetchQuery({ queryKey: ["pratica", p.id], queryFn: () => api.pratica(p.id), staleTime: 0 });
    setM(moduloIniziale(nuova));
    setVersione(versioneValutazione(nuova));
    setConflitto(true);
  };

  const valida = useMutation({
    mutationFn: () => api.valida(p.id, { versione: p.versione, valutazione: inValutazione(m, true, sostituisciAts, versione), temi: inDecisioni(decisioni) }),
    onMutate: () => setConflitto(false),
    onSuccess: async () => { prossimo(); await aggiorna(); },
    onError: dopoErrore,
  });
  const bozza = useMutation({
    mutationFn: () => api.salvaValutazione(p.id, inValutazione(m, false, sostituisciAts, versione)),
    onMutate: () => setConflitto(false),
    onSuccess: async (v) => { setVersione(v.versione); setSalvata(true); await aggiorna(); },
    onError: dopoErrore,
  });
  const restituzione = useMutation({
    mutationFn: () => api.restituisci(p.id, p.versione, motivo.trim()),
    onSuccess: async () => { setRestituisci(false); prossimo(); await aggiorna(); },
  });
  const errore = valida.error ?? bozza.error;
  const occupato = valida.isPending || bozza.isPending;
  const manca = !m.esito[0] || !m.urgenza[0];
  const collegate = p.n_collegate;

  return (
    <div className="pila">
      <section className="card pila" aria-label="Pratica">
        <div className="riga spazio">
          <div>
            <div className="sottotitolo" style={{ fontSize: 14 }}>
              {[p.protocollo ? `Prot. ${p.protocollo}` : null, p.comune, `arrivata il ${data(p.creata_il)}`].filter(Boolean).join(" · ")}
            </div>
            <h2>{p.titolo}</h2>
            <div className="sottotitolo">
              {p.tipo === "esposto" ? "Esposto" : p.tipo}
              {p.temi.some((t) => t.stato === "confermato") && <> · fascicolo {p.temi.filter((t) => t.stato === "confermato").map((t) => t.nome).join(", ")}</>}
              {` · ${collegate === 0 ? "nessuna pratica collegata" : `${collegate} ${collegate === 1 ? "pratica collegata" : "pratiche collegate"}`}`}
            </div>
          </div>
          <Link className="btn secondario" to={`/pratiche/${p.id}`}>Apri il PDF e lo storico</Link>
        </div>
        <Avvisi avvisi={p.avvisi} />
      </section>

      <div className="colonne">
        <div className="larga" style={{ flex: "1 1 340px" }}>
          {p.analisi
            ? <PropostaIA analisi={p.analisi} />
            : <section className="card"><h3>Proposta dell'IA</h3><Vuoto>Nessuna proposta disponibile: compila la valutazione a mano.</Vuoto></section>}
        </div>
        <form className="card pila larga" aria-label="La tua valutazione" style={{ flex: "1 1 380px" }}
          onSubmit={(e) => { e.preventDefault(); if (!manca) valida.mutate(); }}>
          <div>
            <h3>La tua valutazione</h3>
            <div className="sottotitolo" style={{ fontSize: 14 }}>
              {p.valutazione?.valutazione?.compilata ? "Valutazione già compilata." : "Precompilata con la proposta dell'IA. Correggi ciò che non torna."}
            </div>
          </div>
          {ats && (
            <div className="avviso" role="status">
              <strong>Esiste già una valutazione ATS.</strong> Confermando la sostituisci con la tua.
              <label className="opzione"><input type="checkbox" checked={sostituisciAts} onChange={(e) => setSostituisciAts(e.target.checked)} />Sostituisci la valutazione ATS</label>
            </div>
          )}
          <CampiValutazione m={m} set={setM} voc={voc} />
          <TemiDecisione temi={p.temi} catalogo={catalogo} decisioni={decisioni} onCambia={setDecisioni} />
          {conflitto ? <div role="alert" className="avviso">{MESSAGGIO_CONFLITTO}</div> : <MessaggioErrore errore={errore} />}
          {salvata && <div role="status" className="ok">Bozza salvata.</div>}
          <div className="riga">
            <button type="submit" className="btn" disabled={occupato || manca || (ats && !sostituisciAts)}>
              {valida.isPending ? "Conferma in corso…" : "Conferma e vai al prossimo"}
            </button>
            <button type="button" className="btn secondario" disabled={occupato} onClick={() => bozza.mutate()}>Salva bozza</button>
            {me?.utente.ruolo === "operatore" && (
              <button type="button" className="btn pericolo" onClick={() => setRestituisci(true)}>Restituisci allo smistatore</button>
            )}
          </div>
          {manca && <div className="sottotitolo" style={{ fontSize: 14 }}>Per confermare scegli esito e urgenza.</div>}
        </form>
      </div>

      {restituisci && (
        <Dialogo titolo="Restituisci allo smistatore" onChiudi={() => setRestituisci(false)}>
          <div className="campo">
            <label htmlFor="motivo">Perché la restituisci? (obbligatorio)</label>
            <textarea id="motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </div>
          <MessaggioErrore errore={restituzione.error} />
          <div className="riga">
            <button type="button" className="btn" disabled={!motivo.trim() || restituzione.isPending} onClick={() => restituzione.mutate()}>Restituisci</button>
            <button type="button" className="btn secondario" onClick={() => setRestituisci(false)}>Annulla</button>
          </div>
        </Dialogo>
      )}
    </div>
  );
}
