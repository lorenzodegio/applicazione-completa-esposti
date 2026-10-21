import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type { PraticaDettaglio } from "../api/tipi";
import { AssegnaUfficio } from "../componenti/AssegnaUfficio";
import { Percorso } from "../componenti/Percorso";
import { Avvisi, Caricamento, Dialogo, Intestazione, MessaggioErrore, TagStato } from "../componenti/ui";
import { useSessione } from "../sessione";
import { TabAttivita } from "./pratica/TabAttivita";
import { TabCollegamenti } from "./pratica/TabCollegamenti";
import { TabDocumenti } from "./pratica/TabDocumenti";
import { TabNote } from "./pratica/TabNote";
import { TabRiepilogo } from "./pratica/TabRiepilogo";

const SCHEDE = [
  ["riepilogo", "Riepilogo"], ["documenti", "Documenti"], ["percorso", "Percorso"],
  ["collegamenti", "Collegamenti"], ["attivita", "Azioni"], ["note", "Note e registro"],
] as const;

export function SchedaPratica() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["pratica", id], queryFn: () => api.pratica(id) });
  if (q.isLoading) return <Caricamento />;
  if (q.error || !q.data) return <><Intestazione titolo="Pratica" /><MessaggioErrore errore={q.error} /><Link to="/pratiche">Torna a Gestione pratiche</Link></>;
  return <Contenuto p={q.data} />;
}

type Dialogo_ = null | "assegna" | "restituisci" | "chiudi" | "riapri";

function Contenuto({ p }: { p: PraticaDettaglio }) {
  const { me } = useSessione();
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const scheda = SCHEDE.find(([k]) => k === sp.get("scheda"))?.[0] ?? "riepilogo";
  const [dialogo, setDialogo] = useState<Dialogo_>(null);
  const [motivo, setMotivo] = useState("");
  const ruolo = me?.utente.ruolo;
  const percorso = useQuery({ queryKey: ["percorso", p.id], queryFn: () => api.percorso(p.id), enabled: scheda === "percorso" });

  const chiudi = () => { setDialogo(null); setMotivo(""); };
  const azione = useMutation({
    mutationFn: async () => {
      if (dialogo === "restituisci") return api.restituisci(p.id, p.versione, motivo.trim());
      if (dialogo === "chiudi") return api.cambiaStato(p.id, p.versione, "CHIUSA", motivo.trim() || undefined);
      return api.cambiaStato(p.id, p.versione, "IN_LAVORAZIONE", motivo.trim());
    },
    onSuccess: async () => { chiudi(); await qc.invalidateQueries(); },
  });
  const titoloDialogo = { restituisci: "Restituisci allo smistatore", chiudi: "Chiudi la pratica", riapri: "Riapri la pratica" } as const;
  const motivoObbligatorio = dialogo === "restituisci" || dialogo === "riapri";

  return (
    <>
      <Intestazione
        titolo={p.titolo}
        briciole={<><Link to="/pratiche">Gestione pratiche</Link> / {p.protocollo ?? p.numero}{p.comune ? ` · ${p.comune}` : ""}</>}
        sotto={<span className="riga"><TagStato stato={p.stato} /><span>{p.ufficio ? `Ufficio: ${p.ufficio.nome}` : "Non ancora assegnata a un ufficio"}</span></span>}
        azioni={
          <div className="riga">
            {p.stato === "DA_VALIDARE" && <Link className="btn" to={`/inbox/${p.id}`}>Valida nella Inbox</Link>}
            {ruolo === "smistatore" && (p.stato === "DA_SMISTARE" || p.stato === "DA_VALIDARE") && (
              <button type="button" className="btn secondario" onClick={() => setDialogo("assegna")}>{p.stato === "DA_SMISTARE" ? "Assegna a un ufficio" : "Riassegna"}</button>
            )}
            {ruolo === "operatore" && (p.stato === "DA_VALIDARE" || p.stato === "IN_LAVORAZIONE") && (
              <button type="button" className="btn pericolo" onClick={() => setDialogo("restituisci")}>Restituisci allo smistatore</button>
            )}
            {p.stato === "IN_LAVORAZIONE" && <button type="button" className="btn secondario" onClick={() => setDialogo("chiudi")}>Chiudi la pratica</button>}
            {p.stato === "CHIUSA" && ruolo === "smistatore" && <button type="button" className="btn secondario" onClick={() => setDialogo("riapri")}>Riapri</button>}
          </div>
        }
      />
      <Avvisi avvisi={p.avvisi} />

      <div role="tablist" aria-label="Sezioni della pratica" className="schede">
        {SCHEDE.map(([k, et]) => (
          <button key={k} id={`tab-${k}`} type="button" role="tab" aria-selected={scheda === k} aria-controls="pannello"
            onClick={() => setSp(k === "riepilogo" ? {} : { scheda: k })}>{et}</button>
        ))}
      </div>
      <div id="pannello" role="tabpanel" aria-labelledby={`tab-${scheda}`} className="pila">
        {scheda === "riepilogo" && <TabRiepilogo key={p.versione} p={p} />}
        {scheda === "documenti" && <TabDocumenti p={p} />}
        {scheda === "percorso" && (
          <section className="card" aria-label="Percorso della pratica">
            <h2 style={{ marginBottom: 12 }}>Percorso della pratica</h2>
            {percorso.isLoading && <Caricamento />}
            <MessaggioErrore errore={percorso.error} />
            {percorso.data && <Percorso passi={percorso.data} />}
          </section>
        )}
        {scheda === "collegamenti" && <TabCollegamenti p={p} />}
        {scheda === "attivita" && <TabAttivita p={p} />}
        {scheda === "note" && <TabNote p={p} />}
      </div>

      {dialogo === "assegna" && <AssegnaUfficio pratica={p} onChiudi={chiudi} />}
      {(dialogo === "restituisci" || dialogo === "chiudi" || dialogo === "riapri") && (
        <Dialogo titolo={titoloDialogo[dialogo]} onChiudi={chiudi}>
          <form className="pila" onSubmit={(e) => { e.preventDefault(); if (!motivoObbligatorio || motivo.trim()) azione.mutate(); }}>
            <div className="campo">
              <label htmlFor="motivo-az">{motivoObbligatorio ? "Motivo (obbligatorio)" : "Nota (facoltativa)"}</label>
              <textarea id="motivo-az" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </div>
            <MessaggioErrore errore={azione.error} />
            <div className="riga">
              <button type="submit" className="btn" disabled={(motivoObbligatorio && !motivo.trim()) || azione.isPending}>Conferma</button>
              <button type="button" className="btn secondario" onClick={chiudi}>Annulla</button>
            </div>
          </form>
        </Dialogo>
      )}
    </>
  );
}
