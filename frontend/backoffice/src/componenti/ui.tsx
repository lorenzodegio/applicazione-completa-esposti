import { useEffect, useRef, type ReactNode } from "react";
import { ApiError } from "../api/client";
import type { Avviso, StatoPratica } from "../api/tipi";
import { ETICHETTA_STATO } from "../formati";

export function Caricamento({ testo = "Caricamento…" }: { testo?: string }) {
  return <div role="status" className="vuoto">{testo}</div>;
}

export function MessaggioErrore({ errore }: { errore: unknown }) {
  if (!errore) return null;
  const testo = errore instanceof ApiError || errore instanceof Error ? errore.message : "Errore imprevisto";
  return <div role="alert" className="errore">{testo}</div>;
}

export function Vuoto({ children }: { children: ReactNode }) {
  return <div className="vuoto">{children}</div>;
}

export function Intestazione({ titolo, sotto, azioni, briciole }: {
  titolo: string; sotto?: ReactNode; azioni?: ReactNode; briciole?: ReactNode;
}) {
  useEffect(() => { document.title = `${titolo} · Esposti ATS`; }, [titolo]);
  return (
    <div className="testata">
      <div>
        {briciole && <div className="briciole">{briciole}</div>}
        <h1>{titolo}</h1>
        {sotto && <div className="sottotitolo">{sotto}</div>}
      </div>
      {azioni}
    </div>
  );
}

export function TagStato({ stato }: { stato: StatoPratica }) {
  const classe = stato === "CHIUSA" ? "tag neutro" : stato === "DA_VALIDARE" || stato === "DA_SMISTARE" ? "tag ambra" : "tag";
  return <span className={classe}>{ETICHETTA_STATO[stato]}</span>;
}

/** Avvisi del backend (lettura incerta, analisi non disponibile, valori fuori vocabolario). */
export function Avvisi({ avvisi }: { avvisi: Avviso[] }) {
  if (!avvisi.length) return null;
  return (
    <>
      {avvisi.map((a) => (
        <div key={a.codice} role="status" className="avviso">
          {a.codice === "lettura_incerta" && <strong>Lettura incerta. </strong>}
          {a.codice === "analisi_non_disponibile" && <strong>Analisi non disponibile. </strong>}
          {a.testo.replace(/^Lettura incerta \(/, "(")}
        </div>
      ))}
    </>
  );
}

export function Dialogo({ titolo, children, onChiudi }: { titolo: string; children: ReactNode; onChiudi: () => void }) {
  const rif = useRef<HTMLDivElement>(null);
  const chiudi = useRef(onChiudi);
  chiudi.current = onChiudi; // la funzione cambia a ogni render: l'effetto non deve rigirare
  useEffect(() => {
    const precedente = document.activeElement as HTMLElement | null;
    rif.current?.querySelector<HTMLElement>("textarea, input, select, button")?.focus();
    const tasto = (e: KeyboardEvent) => e.key === "Escape" && chiudi.current();
    window.addEventListener("keydown", tasto);
    return () => { window.removeEventListener("keydown", tasto); precedente?.focus(); };
  }, []);
  return (
    <div className="dialogo">
      <div ref={rif} role="dialog" aria-modal="true" aria-label={titolo}>
        <h2>{titolo}</h2>
        {children}
      </div>
    </div>
  );
}

export function Paginazione({ pagina, totale, perPagina, onCambia }: {
  pagina: number; totale: number; perPagina: number; onCambia: (p: number) => void;
}) {
  const pagine = Math.max(1, Math.ceil(totale / perPagina));
  if (pagine <= 1) return null;
  return (
    <nav className="riga spazio" aria-label="Paginazione">
      <button type="button" className="btn secondario piccolo" disabled={pagina <= 1} onClick={() => onCambia(pagina - 1)}>Precedente</button>
      <span>Pagina {pagina} di {pagine}</span>
      <button type="button" className="btn secondario piccolo" disabled={pagina >= pagine} onClick={() => onCambia(pagina + 1)}>Successiva</button>
    </nav>
  );
}

export function Opzioni({ nome, tipo, voci, valore, onCambia, legenda }: {
  nome: string; tipo: "radio" | "checkbox"; voci: string[]; valore: string[]; onCambia: (v: string[]) => void; legenda: string;
}) {
  return (
    <fieldset>
      <legend>{legenda}</legend>
      <div className="opzioni">
        {voci.map((v) => (
          <label key={v} className="opzione">
            <input
              type={tipo} name={nome} checked={valore.includes(v)}
              onChange={(e) => onCambia(tipo === "radio" ? [v] : e.target.checked ? [...valore, v] : valore.filter((x) => x !== v))}
            />
            {v}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
