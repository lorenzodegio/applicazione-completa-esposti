import type { TemaCatalogo, TemaDecisione, TemaOut } from "../api/tipi";

export type Decisioni = Record<string, "confermato" | "scartato">;

/** I temi proposti dall'IA partono «confermati» come il resto del modulo; la persona li corregge.
 * Regola del server: alla validazione un tema proposto che nessuno ha toccato si considera accettato. */
export function decisioniIniziali(temi: TemaOut[]): Decisioni {
  return Object.fromEntries(temi.map((t) => [t.codice, t.stato === "scartato" ? "scartato" : "confermato"])) as Decisioni;
}

export const inDecisioni = (d: Decisioni): TemaDecisione[] =>
  Object.entries(d).map(([codice, stato]) => ({ codice, stato }));

export function TemiDecisione({ temi, catalogo, decisioni, onCambia }: {
  temi: TemaOut[]; catalogo: TemaCatalogo[]; decisioni: Decisioni; onCambia: (d: Decisioni) => void;
}) {
  const presenti = new Set(temi.map((t) => t.codice));
  const aggiunti = Object.keys(decisioni).filter((c) => !presenti.has(c));
  const disponibili = catalogo.filter((t) => !(t.codice in decisioni));
  const nome = (c: string) => catalogo.find((t) => t.codice === c)?.nome ?? c;
  const riga = (codice: string, titolo: string, nota?: string) => (
    <fieldset key={codice}>
      <legend>{titolo}</legend>
      {nota && <div style={{ fontSize: 14, color: "var(--testo-secondario)" }}>{nota}</div>}
      <div className="opzioni">
        {(["confermato", "scartato"] as const).map((s) => (
          <label key={s} className="opzione">
            <input type="radio" name={`tema-${codice}`} checked={decisioni[codice] === s}
              onChange={() => onCambia({ ...decisioni, [codice]: s })} />
            {s === "confermato" ? "Conferma" : "Scarta"}
          </label>
        ))}
      </div>
    </fieldset>
  );
  return (
    <section className="pila" aria-label="Temi">
      <h3>Temi (fascicoli)</h3>
      {temi.length === 0 && aggiunti.length === 0 && <div className="vuoto">Nessun tema proposto dall'IA.</div>}
      {temi.some((t) => t.stato === "proposto") && (
        <div className="sottotitolo" style={{ fontSize: 14 }}>I temi proposti dall'IA che non scarti vengono accettati con la conferma.</div>
      )}
      {temi.map((t) => riga(t.codice, t.nome,
        t.origine === "ia" && t.motivo ? `Proposto dall'IA: ${t.motivo}${t.frase ? ` — «${t.frase}»` : ""}` : undefined))}
      {aggiunti.map((c) => (
        <fieldset key={c}>
          <legend>{nome(c)}</legend>
          <div className="riga spazio">
            <span style={{ fontSize: 14, color: "var(--testo-secondario)" }}>Aggiunto da te</span>
            <button type="button" className="btn secondario piccolo"
              onClick={() => onCambia(Object.fromEntries(Object.entries(decisioni).filter(([k]) => k !== c)) as Decisioni)}>
              Rimuovi
            </button>
          </div>
        </fieldset>
      ))}
      {disponibili.length > 0 && (
        <div className="campo">
          <label htmlFor="aggiungi-tema">Aggiungi un tema</label>
          <select id="aggiungi-tema" value="" onChange={(e) => e.target.value && onCambia({ ...decisioni, [e.target.value]: "confermato" })}>
            <option value="">Scegli…</option>
            {disponibili.map((t) => <option key={t.codice} value={t.codice}>{t.nome}</option>)}
          </select>
        </div>
      )}
    </section>
  );
}
