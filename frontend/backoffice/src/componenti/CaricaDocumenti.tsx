import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import { messaggioErrore } from "../api/errori";
import { ApiError } from "../api/client";

/** Formati accettati dal caricamento (il motore converte Word e RTF in PDF). */
export const ESTENSIONI = [".pdf", ".doc", ".docx", ".rtf"];
const estensione = (nome: string) => (nome.match(/\.[^.]+$/)?.[0] ?? "").toLowerCase();

type Fase = "in_attesa" | "caricamento" | "caricato" | "errore";
type Riga = {
  chiave: string; nome: string; dimensione: number;
  fase: Fase; frazione: number; errore?: string;
  praticaId?: string; numero?: string; lavoroId?: string; nDocumenti?: number;
};

const dimensione = (b: number) => (b < 1024 * 1024 ? `${Math.max(1, Math.round(b / 1024))} kB` : `${(b / 1024 / 1024).toFixed(1)} MB`);

/**
 * Smistamento → «Carica un nuovo esposto»: uno o più file (PDF, Word, RTF), una pratica per file
 * oppure tutti in una sola pratica; avanzamento del caricamento e stato dell'analisi di ogni documento.
 * I file si inviano uno alla volta: il motore comunque li analizza uno alla volta.
 */
export function CaricaDocumenti() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [unica, setUnica] = useState(false);
  const [scelti, setScelti] = useState<File[]>([]);
  const [titolo, setTitolo] = useState("");
  const [protocollo, setProtocollo] = useState("");
  const [comune, setComune] = useState("");
  const [righe, setRighe] = useState<Riga[]>([]);
  const [inCorso, setInCorso] = useState(false);
  const [erroreScelta, setErroreScelta] = useState<string | null>(null);

  const campiUsati = unica || scelti.length <= 1;   // titolo, protocollo e comune valgono per una sola pratica
  const aggiorna = (chiave: string, delta: Partial<Riga>) =>
    setRighe((rr) => rr.map((r) => (r.chiave === chiave ? { ...r, ...delta } : r)));

  function scegli(files: File[]) {
    const non = files.filter((f) => !ESTENSIONI.includes(estensione(f.name)));
    setErroreScelta(non.length ? `Formato non accettato: ${non.map((f) => f.name).join(", ")}. Si caricano solo PDF, Word (.doc, .docx) e RTF.` : null);
    setScelti(non.length ? [] : files);
  }

  async function carica() {
    if (!scelti.length) return;
    const campi = campiUsati ? { titolo: titolo.trim(), protocollo: protocollo.trim(), comune: comune.trim() } : {};
    // gruppi: un invio per pratica
    const gruppi: File[][] = unica ? [scelti] : scelti.map((f) => [f]);
    const iniziali: Riga[] = scelti.map((f, i) => ({ chiave: `${i}-${f.name}`, nome: f.name, dimensione: f.size, fase: "in_attesa", frazione: 0 }));
    setRighe(iniziali);
    setInCorso(true);
    let k = 0;
    for (const gruppo of gruppi) {
      const chiavi = iniziali.slice(k, k + gruppo.length).map((r) => r.chiave);
      k += gruppo.length;
      chiavi.forEach((c) => aggiorna(c, { fase: "caricamento" }));
      try {
        const r = await api.nuovaPratica(gruppo, campi, (fr) => chiavi.forEach((c) => aggiorna(c, { frazione: fr })));
        chiavi.forEach((c, i) => aggiorna(c, {
          fase: "caricato", frazione: 1, praticaId: r.pratica.id, numero: r.pratica.numero,
          lavoroId: r.documenti[i]?.analisi?.lavoro_id ?? undefined, nDocumenti: r.documenti.length,
        }));
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : messaggioErrore(0, undefined);
        chiavi.forEach((c) => aggiorna(c, { fase: "errore", errore: msg }));
      }
    }
    setInCorso(false);
    setScelti([]); setTitolo(""); setProtocollo(""); setComune("");
    if (input.current) input.current.value = "";
    await qc.invalidateQueries();
  }

  return (
    <details className="card" open={righe.length > 0 || undefined}>
      <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 700, fontSize: 18 }}>Carica un nuovo esposto</summary>
      <form className="pila" onSubmit={(e) => { e.preventDefault(); void carica(); }}>
        <div className="campo">
          <label htmlFor="file-esposto">Documenti (anche più di uno)</label>
          <input id="file-esposto" ref={input} type="file" multiple accept={ESTENSIONI.join(",")}
                 aria-describedby="file-esposto-aiuto" onChange={(e) => scegli(Array.from(e.target.files ?? []))} />
          <span id="file-esposto-aiuto" className="meta">PDF, Word (.doc, .docx) o RTF.</span>
        </div>
        {erroreScelta && <div role="alert" className="errore">{erroreScelta}</div>}
        {scelti.length > 1 && (
          <fieldset className="campo">
            <legend>Come creare le pratiche</legend>
            <label><input type="radio" name="raggruppa" checked={!unica} onChange={() => setUnica(false)} /> Una pratica per ogni file ({scelti.length} pratiche)</label>
            <label><input type="radio" name="raggruppa" checked={unica} onChange={() => setUnica(true)} /> Tutti i file in una sola pratica</label>
          </fieldset>
        )}
        <div className="filtri">
          <div className="campo"><label htmlFor="n-titolo">Titolo (facoltativo)</label><input id="n-titolo" type="text" value={titolo} disabled={!campiUsati} onChange={(e) => setTitolo(e.target.value)} /></div>
          <div className="campo"><label htmlFor="n-prot">Protocollo (facoltativo)</label><input id="n-prot" type="text" value={protocollo} disabled={!campiUsati} onChange={(e) => setProtocollo(e.target.value)} /></div>
          <div className="campo"><label htmlFor="n-com">Comune (facoltativo)</label><input id="n-com" type="text" value={comune} disabled={!campiUsati} onChange={(e) => setComune(e.target.value)} /></div>
        </div>
        {!campiUsati && <span className="meta">Con una pratica per file, titolo e protocollo si ricavano da ogni documento: si correggono poi nella pratica.</span>}
        <div><button type="submit" className="btn" disabled={inCorso || !scelti.length}>{inCorso ? "Caricamento…" : "Carica e analizza"}</button></div>
        {righe.length > 0 && (
          <div role="status" aria-live="polite" className="pila" aria-label="Documenti caricati">
            {righe.map((r) => <RigaDocumento key={r.chiave} riga={r} />)}
          </div>
        )}
      </form>
    </details>
  );
}

function RigaDocumento({ riga: r }: { riga: Riga }) {
  return (
    <div className="voce">
      <span className="corpo">
        <span className="titolo">{r.nome}</span>
        <span className="meta">{dimensione(r.dimensione)}</span>
        {r.fase === "caricamento" && <progress max={1} value={r.frazione} aria-label={`Caricamento di ${r.nome}`} style={{ width: "100%" }} />}
        {r.fase === "caricato" && r.praticaId && (
          <span>Pratica {r.numero} creata: il motore sta analizzando {r.nDocumenti === 1 ? "il documento" : "i documenti"}. <Link to={`/pratiche/${r.praticaId}`}>Aprila</Link></span>
        )}
        {r.fase === "errore" && <span className="errore">Caricamento non riuscito: {r.errore}</span>}
      </span>
      <StatoDocumento riga={r} />
    </div>
  );
}

/** Stato dell'analisi del documento, aggiornato finché il motore non ha finito. */
function StatoDocumento({ riga: r }: { riga: Riga }) {
  const q = useQuery({
    queryKey: ["lavoro", r.lavoroId],
    queryFn: () => api.lavoro(r.lavoroId!),
    enabled: r.fase === "caricato" && !!r.lavoroId,
    refetchInterval: (query) => (["completato", "errore"].includes(query.state.data?.stato ?? "") ? false : 3000),
  });
  if (r.fase === "in_attesa") return <span className="tag neutro">In attesa</span>;
  if (r.fase === "caricamento") return <span className="tag neutro">Caricamento {Math.round(r.frazione * 100)}%</span>;
  if (r.fase === "errore") return <span className="tag ambra">Non caricato</span>;
  const l = q.data;
  if (!l) return <span className="tag neutro">Caricato</span>;
  if (l.stato === "completato") return <span className="tag">Analizzato</span>;
  if (l.stato === "errore") return <span className="tag ambra">Analisi non disponibile{l.codice_errore ? ` (${l.codice_errore})` : ""}</span>;
  if (l.stato === "in_corso") return <span className="tag neutro">In analisi{l.tentativi > 1 ? ` (tentativo ${l.tentativi})` : ""}</span>;
  return <span className="tag neutro">In coda per il motore{l.tentativi > 0 ? ` (tentativo ${l.tentativi + 1})` : ""}</span>;
}
