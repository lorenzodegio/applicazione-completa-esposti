import { messaggioErrore } from "./errori";

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(messaggioErrore(status, detail));
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;
interface Opzioni { corpo?: unknown; form?: FormData; query?: Query }

/** Codice del 409 «qualcun altro ha salvato la valutazione nel frattempo» (controllo di versione). */
export const CONFLITTO_VALUTAZIONE = "valutazione_modificata";

export function eConflittoValutazione(e: unknown): boolean {
  return e instanceof ApiError && e.status === 409
    && (e.detail as { codice?: string } | undefined)?.codice === CONFLITTO_VALUTAZIONE;
}

export const EVENTO_NON_AUTORIZZATO = "esposti:non-autorizzato";
const BASE = "/api/v1";

export function costruisciUrl(percorso: string, query?: Query): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return `${BASE}${percorso}${s ? `?${s}` : ""}`;
}

export async function richiesta<T>(metodo: string, percorso: string, opz: Opzioni = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (opz.form) body = opz.form;
  else if (opz.corpo !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opz.corpo);
  }
  const r = await fetch(costruisciUrl(percorso, opz.query), { method: metodo, headers, body, credentials: "same-origin" });
  if (r.status === 204) return undefined as T;
  const testo = await r.text();
  let dati: unknown = undefined;
  try { dati = testo ? JSON.parse(testo) : undefined; } catch { dati = testo; }
  if (!r.ok) {
    // 401 su una pagina protetta = sessione scaduta; sul login è semplicemente «credenziali errate»
    if (r.status === 401 && percorso !== "/auth/login") window.dispatchEvent(new Event(EVENTO_NON_AUTORIZZATO));
    throw new ApiError(r.status, (dati as { detail?: unknown } | undefined)?.detail);
  }
  return dati as T;
}

export const get = <T>(p: string, query?: Query) => richiesta<T>("GET", p, { query });
export const post = <T>(p: string, corpo?: unknown) => richiesta<T>("POST", p, { corpo });
export const put = <T>(p: string, corpo?: unknown) => richiesta<T>("PUT", p, { corpo });
export const patch = <T>(p: string, corpo?: unknown) => richiesta<T>("PATCH", p, { corpo });
export const del = <T>(p: string) => richiesta<T>("DELETE", p);
export const invia = <T>(p: string, form: FormData) => richiesta<T>("POST", p, { form });
