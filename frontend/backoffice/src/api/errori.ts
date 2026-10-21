/** Trasforma la risposta d'errore del backend in una frase per l'utente. */
export function messaggioErrore(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const righe = detail.map((e) => {
      const d = e as { loc?: unknown[]; msg?: string };
      const campo = (d.loc ?? []).filter((x) => x !== "body").join(".");
      return campo ? `${campo}: ${d.msg ?? "non valido"}` : (d.msg ?? "non valido");
    });
    if (righe.length) return righe.join("; ");
  }
  if (detail && typeof detail === "object") {
    const d = detail as { messaggio?: string; campi?: { campo: string; valore: string }[]; temi?: string[] };
    if (d.messaggio) {
      const extra = [...(d.campi ?? []).map((c) => `${c.campo}: ${c.valore}`), ...(d.temi ?? [])];
      return extra.length ? `${d.messaggio} (${extra.join(", ")})` : d.messaggio;
    }
  }
  if (status === 401) return "Accesso richiesto";
  if (status === 403) return "Operazione non consentita al tuo ruolo";
  if (status === 404) return "Non trovato";
  if (status === 409) return "Conflitto con lo stato attuale: ricarica e riprova";
  if (status === 413) return "File troppo grande";
  if (status === 429) return "Troppi tentativi: riprova più tardi";
  if (status >= 500) return "Errore del server: riprova tra poco";
  return "Richiesta non riuscita";
}
