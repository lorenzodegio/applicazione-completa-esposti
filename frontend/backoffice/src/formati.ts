import type { Ruolo, StatoPratica } from "./api/tipi";

export const ETICHETTA_STATO: Record<StatoPratica, string> = {
  IN_ANALISI: "In analisi",
  DA_SMISTARE: "Da smistare",
  DA_VALIDARE: "Da validare",
  IN_LAVORAZIONE: "In lavorazione",
  CHIUSA: "Chiusa",
};

export const ETICHETTA_RUOLO: Record<Ruolo, string> = {
  smistatore: "Smistatore",
  operatore: "Operatore di ufficio",
  amministratore: "Amministratore",
};

const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

export function data(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? "—" : `${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()}`;
}

export function dataOra(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${data(iso)} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export const elenco = (v: string[] | undefined | null) => (v && v.length ? v.join(", ") : "—");

/** Tag blu per «Accolto», ambra per gli esiti che chiedono attenzione (come nei mockup). */
export const classeEsito = (esito?: string | null) => (esito === "Accolto" ? "tag" : "tag ambra");

export const etichettaTipo = (t?: string | null) =>
  t ? t.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()).replace("Riscontro ats", "Riscontro ATS") : "—";
