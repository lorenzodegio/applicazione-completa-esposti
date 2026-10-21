/** Test veloci: backend simulato con fetch. Verificano ciò che l'app invia e mostra. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { messaggioErrore } from "../api/errori";
import { data, etichettaTipo } from "../formati";

type Gestore = (corpo: any) => unknown | { __stato: number; corpo: unknown };
const risposta = (stato: number, corpo: unknown) => ({ __stato: stato, corpo });

function simula(rotte: Record<string, Gestore>) {
  const chiamate: { chiave: string; corpo: any }[] = [];
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const percorso = String(input).replace("/api/v1", "").split("?")[0];
    const chiave = `${init.method ?? "GET"} ${percorso}`;
    const corpo = typeof init.body === "string" ? JSON.parse(init.body) : undefined;
    chiamate.push({ chiave, corpo });
    const g = rotte[chiave];
    const out = g ? g(corpo) : risposta(404, { detail: `non simulato: ${chiave}` });
    const r = (out && typeof out === "object" && "__stato" in out ? out : { __stato: 200, corpo: out }) as { __stato: number; corpo: unknown };
    return new Response(r.__stato === 204 ? null : JSON.stringify(r.corpo), { status: r.__stato, headers: { "content-type": "application/json" } });
  });
  return chiamate;
}

afterEach(() => vi.unstubAllGlobals());

function avvia(percorso: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[percorso]}><App /></MemoryRouter></QueryClientProvider>);
}

const uff = { id: "u1", codice: "VET", nome: "Medicina Veterinaria", attivo: true };
const me = (ruolo: "operatore" | "smistatore" | "amministratore") => ({
  utente: { id: "x", username: ruolo, nome_visualizzato: `Utente ${ruolo}`, email: null, ruolo, ufficio: ruolo === "operatore" ? uff : null, attivo: true },
  menu: { operatore: ["Home", "Inbox", "Fascicoli", "Gestione pratiche"], smistatore: ["Home", "Inbox", "Fascicoli", "Gestione pratiche", "Smistamento"], amministratore: ["Uffici", "Utenti"] }[ruolo],
});

// --- funzioni pure -------------------------------------------------------------------------------

describe("messaggi d'errore", () => {
  it("testo, errori di validazione, oggetti del backend e ripieghi per stato", () => {
    expect(messaggioErrore(409, "La pratica è stata modificata")).toBe("La pratica è stata modificata");
    expect(messaggioErrore(422, [{ loc: ["body", "esito"], msg: "campo obbligatorio" }])).toBe("esito: campo obbligatorio");
    expect(messaggioErrore(422, { messaggio: "Valori non presenti nei vocabolari", campi: [{ campo: "ambito", valore: "X" }] }))
      .toBe("Valori non presenti nei vocabolari (ambito: X)");
    expect(messaggioErrore(422, { messaggio: "Conferma o scarta tutti i temi proposti", temi: ["Cani"] }))
      .toBe("Conferma o scarta tutti i temi proposti (Cani)");
    expect(messaggioErrore(403, undefined)).toMatch(/non consentita/);
    expect(messaggioErrore(500, undefined)).toMatch(/Errore del server/);
  });
  it("formati di data e tipo", () => {
    expect(data("2026-10-17")).toBe("17 ott 2026");
    expect(data(null)).toBe("—");
    expect(etichettaTipo("riscontro_ats")).toBe("Riscontro ATS");
    expect(etichettaTipo("esposto")).toBe("Esposto");
  });
});

// --- accesso e ruoli -------------------------------------------------------------------------------

describe("accesso e ruoli", () => {
  it("credenziali errate: mostra il messaggio del server", async () => {
    simula({ "GET /auth/me": () => risposta(401, { detail: "Accesso richiesto" }),
             "POST /auth/login": () => risposta(401, { detail: "Credenziali non valide" }) });
    const u = userEvent.setup();
    avvia("/");
    await u.type(await screen.findByLabelText("Nome utente"), "a");
    await u.type(screen.getByLabelText("Password"), "b");
    await u.click(screen.getByRole("button", { name: "Accedi" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Credenziali non valide");
  });

  it("senza sessione ogni pagina rimanda all'accesso", async () => {
    simula({ "GET /auth/me": () => risposta(401, { detail: "Accesso richiesto" }) });
    avvia("/pratiche/abc");
    expect(await screen.findByRole("form", { name: "Accesso" })).toBeInTheDocument();
  });

  it("il menu segue il ruolo e l'amministratore non arriva alle pratiche", async () => {
    simula({ "GET /auth/me": () => me("amministratore"), "GET /uffici": () => [uff] });
    avvia("/inbox");                                          // pagina vietata all'amministratore
    expect(await screen.findByRole("heading", { name: "Uffici" })).toBeInTheDocument();
    const menu = screen.getByRole("navigation", { name: "Menu principale" });
    expect(within(menu).getAllByRole("link").map((l) => l.textContent)).toEqual(["Uffici", "Utenti"]);
  });

  it("l'operatore non raggiunge Smistamento", async () => {
    simula({ "GET /auth/me": () => me("operatore"), "GET /home": () => homeVuota });
    avvia("/smistamento");
    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
  });
});

const homeVuota = { contatori: { da_validare: 0 }, ultimi_arrivi: [], fascicoli_piu_attivi: [], disaccordo: { totale: 0, pratiche: [] } };

// --- Inbox -----------------------------------------------------------------------------------------------

const voc = {
  esito: ["Accolto", "Archiviato", "Da approfondire"].map((c) => ({ codice: c, etichetta: c })),
  urgenza: ["Bassa", "Normale", "Alta", "Immediata"].map((c) => ({ codice: c, etichetta: c })),
  azione: ["Sopralluogo", "Contatto segnalante"].map((c) => ({ codice: c, etichetta: c })),
  ambito: [{ codice: "Medicina Veterinaria", etichetta: "Medicina Veterinaria" }], problematica: [], elementi: [],
};
const riga = { id: "p1", numero: "ESP-1", titolo: "Pollaio a ridosso del confine", comune: "Castelrovo", protocollo: "0005120/2025", data_protocollo: null,
  tipo: "esposto", canale: "caricamento_manuale", stato: "DA_VALIDARE", ufficio: uff, creata_il: "2026-10-01T10:00:00Z", aggiornata_il: "2026-10-01T10:00:00Z",
  versione: 3, temi: [], valutazione: null, proposta: { esito: "Accolto", urgenza: "Normale" }, lettura_incerta: false, disaccordo: [], n_collegate: 0 };
const precompilazione = { da_risultato_id: "r1", data_doc: "2025-04-09", comune: "Castelrovo", ambito: ["Medicina Veterinaria"], problematica: [], elementi: [],
  ambito_altro: null, problematica_altro: null, elementi_altro: null, esito: "Accolto", urgenza: "Normale", azione: ["Sopralluogo"], note: null, valori_scartati: [] };
const analisi = { risultato_id: "r1", lavoro_id: "l1", documento_id: "d1", ricevuto_il: "2026-10-01T10:01:00Z", versione_motore: "finto", versione_contratto: "1.1",
  tipo_documento: "esposto", tipo_documento_motivo: null, protocollo_letto: null, data_protocollo_letta: null, lettura_incerta: false, pagine_incerte: [], acquisizione: {},
  scheda: { data_doc: null, comune: { valore: "Castelrovo", frase: "residente in Castelrovo", pagina: 1 }, ambito: [{ valore: "Medicina Veterinaria", frase: "circa 40 galline", pagina: 1 }], problematica: [], elementi: [] },
  proposta: { esito: "Accolto", urgenza: "Normale", azione: ["Sopralluogo"], motivo: "Istanza completa.", domanda_decisiva: "Chi segnala, dove e cosa?", da_verificare_sull_originale: [] },
  temi_proposti: [], valori_non_riconosciuti: [], avvisi: [] };
const dettaglio = (extra: object = {}) => ({ ...riga, stato_analisi: { stato: "completata", lavoro_id: "l1", stato_lavoro: "completato", tentativi: 1, codice_errore: null },
  analisi, avvisi: [], disaccordo: [],
  temi: [{ codice: "animali_da_reddito", nome: "Animali da reddito", origine: "ia", stato: "proposto", deciso_da: null, deciso_il: null, motivo: "Galline in un cortile privato.", frase: "circa 40 galline", pagina: 1 }],
  valutazione: { valutazione: null, precompilazione, disaccordo: [] }, ...extra });

function inboxBase(extra: Record<string, Gestore> = {}, det = dettaglio()) {
  return simula({
    "GET /auth/me": () => me("operatore"), "GET /home": () => ({ ...homeVuota, contatori: { da_validare: 1 } }),
    "GET /inbox": () => ({ items: [riga], total: 1, page: 1, per_page: 50 }),
    "GET /pratiche/p1": () => det, "GET /vocabolari": () => voc,
    "GET /temi": () => [{ codice: "animali_da_reddito", nome: "Animali da reddito" }, { codice: "cani", nome: "Cani" }],
    ...extra,
  });
}

describe("Inbox", () => {
  it("la valutazione parte dalla proposta e la conferma invia esattamente ciò che si vede", async () => {
    const chiamate = inboxBase({ "POST /pratiche/p1/validazione": () => ({ ...riga, stato: "IN_LAVORAZIONE" }) });
    const u = userEvent.setup();
    avvia("/inbox/p1");
    const modulo = await screen.findByRole("form", { name: "La tua valutazione" });
    expect(within(modulo).getByRole("radio", { name: "Accolto" })).toBeChecked();
    expect(within(modulo).getByRole("checkbox", { name: "Sopralluogo" })).toBeChecked();
    expect(screen.getByRole("region", { name: "Proposta dell'IA" })).toHaveTextContent("Istanza completa.");
    await u.click(within(modulo).getByRole("radio", { name: "Alta" }));                 // correzione della persona
    await u.click(within(modulo).getByRole("checkbox", { name: "Contatto segnalante" }));
    await u.click(within(modulo).getByRole("button", { name: "Conferma e vai al prossimo" }));
    await waitFor(() => expect(chiamate.some((c) => c.chiave === "POST /pratiche/p1/validazione")).toBe(true));
    const corpo = chiamate.find((c) => c.chiave === "POST /pratiche/p1/validazione")!.corpo;
    expect(corpo.versione).toBe(3);
    expect(corpo.valutazione).toMatchObject({ esito: "Accolto", urgenza: "Alta", azione: ["Sopralluogo", "Contatto segnalante"],
      ambito: ["Medicina Veterinaria"], comune: "Castelrovo", compilata: true, conferma_sovrascrittura: false });
    expect(corpo.temi).toEqual([{ codice: "animali_da_reddito", stato: "confermato" }]);
  });

  it("un tema proposto si può scartare e se ne può aggiungere un altro", async () => {
    const chiamate = inboxBase({ "POST /pratiche/p1/validazione": () => ({ ...riga }) });
    const u = userEvent.setup();
    avvia("/inbox/p1");
    const modulo = await screen.findByRole("form", { name: "La tua valutazione" });
    const tema = within(modulo).getByRole("group", { name: "Animali da reddito" });
    expect(tema).toHaveTextContent("Proposto dall'IA: Galline in un cortile privato.");
    await u.click(within(tema).getByRole("radio", { name: "Scarta" }));
    await u.selectOptions(within(modulo).getByLabelText("Aggiungi un tema"), "Cani");
    await u.click(within(modulo).getByRole("button", { name: "Conferma e vai al prossimo" }));
    await waitFor(() => expect(chiamate.some((c) => c.chiave === "POST /pratiche/p1/validazione")).toBe(true));
    expect(chiamate.find((c) => c.chiave === "POST /pratiche/p1/validazione")!.corpo.temi).toEqual(
      [{ codice: "animali_da_reddito", stato: "scartato" }, { codice: "cani", stato: "confermato" }]);
  });

  it("senza esito e urgenza non si può confermare", async () => {
    inboxBase({}, dettaglio({ valutazione: { valutazione: null, precompilazione: { ...precompilazione, esito: null, urgenza: null }, disaccordo: [] } }));
    avvia("/inbox/p1");
    const modulo = await screen.findByRole("form", { name: "La tua valutazione" });
    expect(within(modulo).getByRole("button", { name: "Conferma e vai al prossimo" })).toBeDisabled();
    expect(within(modulo).getByText("Per confermare scegli esito e urgenza.")).toBeInTheDocument();
  });

  it("una valutazione ATS già compilata si sostituisce solo con la conferma esplicita", async () => {
    const ats = { id: "v1", origine: "import_ats", autore_id: null, autore_nome: "ATS", compilata: true, data_compilazione: "2025-05-01", data_doc: null, comune: null,
      ambito: [], problematica: [], elementi: [], ambito_originale: null, ambito_altro: null, problematica_altro: null, elementi_altro: null,
      esito: "Archiviato", urgenza: "Bassa", azione: [], note: null, da_risultato_id: null, creata_il: "", aggiornata_il: "" };
    const chiamate = inboxBase({ "POST /pratiche/p1/validazione": () => ({ ...riga }) },
      dettaglio({ valutazione: { valutazione: ats, precompilazione: null, disaccordo: [] } }));
    const u = userEvent.setup();
    avvia("/inbox/p1");
    const modulo = await screen.findByRole("form", { name: "La tua valutazione" });
    const conferma = within(modulo).getByRole("button", { name: "Conferma e vai al prossimo" });
    expect(conferma).toBeDisabled();
    expect(within(modulo).getByRole("radio", { name: "Archiviato" })).toBeChecked();   // parte dai dati ATS, non dall'IA
    await u.click(within(modulo).getByRole("checkbox", { name: "Sostituisci la valutazione ATS" }));
    await u.click(conferma);
    await waitFor(() => expect(chiamate.some((c) => c.chiave === "POST /pratiche/p1/validazione")).toBe(true));
    expect(chiamate.find((c) => c.chiave === "POST /pratiche/p1/validazione")!.corpo.valutazione.conferma_sovrascrittura).toBe(true);
  });

  it("un conflitto di versione mostra il messaggio e lascia la pratica dov'è", async () => {
    inboxBase({ "POST /pratiche/p1/validazione": () => risposta(409, { detail: "La pratica è stata modificata nel frattempo: ricarica e riprova" }) });
    const u = userEvent.setup();
    avvia("/inbox/p1");
    await u.click(await screen.findByRole("button", { name: "Conferma e vai al prossimo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("modificata nel frattempo");
    expect(screen.getByRole("form", { name: "La tua valutazione" })).toBeInTheDocument();
  });

  it("restituire richiede il motivo e lo invia con la versione", async () => {
    const chiamate = inboxBase({ "POST /pratiche/p1/restituzione": () => ({ ...riga, stato: "DA_SMISTARE" }) });
    const u = userEvent.setup();
    avvia("/inbox/p1");
    await u.click(await screen.findByRole("button", { name: "Restituisci allo smistatore" }));
    const d = await screen.findByRole("dialog");
    const invia = within(d).getByRole("button", { name: "Restituisci" });
    expect(invia).toBeDisabled();
    await u.type(within(d).getByLabelText(/Perché la restituisci/), "Non è di nostra competenza");
    await u.click(invia);
    await waitFor(() => expect(chiamate.some((c) => c.chiave === "POST /pratiche/p1/restituzione")).toBe(true));
    expect(chiamate.find((c) => c.chiave === "POST /pratiche/p1/restituzione")!.corpo).toEqual({ versione: 3, motivo: "Non è di nostra competenza" });
  });

  it("lo smistatore non ha il pulsante «Restituisci» (non è un'azione sua)", async () => {
    inboxBase({ "GET /auth/me": () => me("smistatore") });
    avvia("/inbox/p1");
    await screen.findByRole("form", { name: "La tua valutazione" });
    expect(screen.queryByRole("button", { name: "Restituisci allo smistatore" })).not.toBeInTheDocument();
  });

  it("lettura incerta e analisi non disponibile si vedono come avvisi", async () => {
    inboxBase({}, dettaglio({ avvisi: [
      { codice: "lettura_incerta", pagine: [2], testo: "Lettura incerta (pagine 2): controlla sull'originale." },
      { codice: "analisi_non_disponibile", testo: "L'ultima analisi non è riuscita." }] }));
    avvia("/inbox/p1");
    const incerta = await screen.findByText(/Lettura incerta\./);
    expect(incerta.closest("[role=status]")).toHaveTextContent(/pagine 2/);
    expect((await screen.findByText(/Analisi non disponibile\./)).closest("[role=status]")).toHaveTextContent(/ultima analisi non è riuscita/);
  });

  it("coda vuota: messaggio", async () => {
    simula({ "GET /auth/me": () => me("operatore"), "GET /home": () => homeVuota, "GET /inbox": () => ({ items: [], total: 0, page: 1, per_page: 50 }) });
    avvia("/inbox");
    expect(await screen.findByText(/Nessun esposto da validare/)).toBeInTheDocument();
  });
});

// --- scheda pratica ------------------------------------------------------------------------------------

describe("Scheda pratica", () => {
  const tema = (codice: string, nome: string, stato: string) => ({ codice, nome, origine: "ia", stato, deciso_da: "x", deciso_il: "2026-10-02T10:00:00Z", motivo: null, frase: null, pagina: null });
  const inLavorazione = () => dettaglio({ stato: "IN_LAVORAZIONE", temi: [tema("cani", "Cani", "confermato"), tema("avvelenamenti", "Avvelenamenti", "scartato")],
    valutazione: { valutazione: null, precompilazione: null, disaccordo: [] } });

  it("salvare i temi non riconferma quelli già scartati", async () => {
    const chiamate = simula({
      "GET /auth/me": () => me("operatore"), "GET /home": () => homeVuota, "GET /pratiche/p1": () => inLavorazione(),
      "GET /vocabolari": () => voc, "GET /temi": () => [{ codice: "cani", nome: "Cani" }, { codice: "avvelenamenti", nome: "Avvelenamenti" }],
      "PUT /pratiche/p1/temi": () => [],
    });
    const u = userEvent.setup();
    avvia("/pratiche/p1");
    await u.click(await screen.findByRole("button", { name: "Salva i temi" }));
    await waitFor(() => expect(chiamate.some((c) => c.chiave === "PUT /pratiche/p1/temi")).toBe(true));
    expect(chiamate.find((c) => c.chiave === "PUT /pratiche/p1/temi")!.corpo.temi).toEqual(
      [{ codice: "cani", stato: "confermato" }, { codice: "avvelenamenti", stato: "scartato" }]);
  });

  it("le azioni dipendono da ruolo e stato: chiudi per chi lavora, riapri solo per lo smistatore", async () => {
    const base = { "GET /home": () => homeVuota, "GET /vocabolari": () => voc, "GET /temi": () => [] };
    simula({ ...base, "GET /auth/me": () => me("operatore"), "GET /pratiche/p1": () => inLavorazione() });
    const { unmount } = avvia("/pratiche/p1");
    expect(await screen.findByRole("button", { name: "Chiudi la pratica" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restituisci allo smistatore" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Riapri" })).not.toBeInTheDocument();
    unmount(); vi.unstubAllGlobals();
    simula({ ...base, "GET /auth/me": () => me("operatore"), "GET /pratiche/p1": () => dettaglio({ stato: "CHIUSA" }) });
    const secondo = avvia("/pratiche/p1");
    await screen.findByRole("tablist");
    expect(screen.queryByRole("button", { name: "Riapri" })).not.toBeInTheDocument();       // l'operatore non riapre
    secondo.unmount(); vi.unstubAllGlobals();
    simula({ ...base, "GET /auth/me": () => me("smistatore"), "GET /pratiche/p1": () => dettaglio({ stato: "CHIUSA" }) });
    avvia("/pratiche/p1");
    expect(await screen.findByRole("button", { name: "Riapri" })).toBeInTheDocument();
  });
});

// --- accessibilità (regole strutturali; il contrasto va verificato in un browser) --------------------------

import axe from "axe-core";

async function violazioni(): Promise<string[]> {
  const r = await axe.run(document.body, { rules: { "color-contrast": { enabled: false } } });
  return r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}

describe("accessibilità", () => {
  it("accesso, Home, Inbox e scheda pratica non hanno violazioni strutturali", async () => {
    simula({ "GET /auth/me": () => risposta(401, {}) });
    const accesso = avvia("/accedi");
    await screen.findByRole("form", { name: "Accesso" });
    expect(await violazioni()).toEqual([]);
    accesso.unmount(); vi.unstubAllGlobals();

    inboxBase();
    const inbox = avvia("/inbox/p1");
    await screen.findByRole("form", { name: "La tua valutazione" });
    expect(await violazioni()).toEqual([]);
    inbox.unmount(); vi.unstubAllGlobals();

    simula({ "GET /auth/me": () => me("operatore"), "GET /home": () => ({ ...homeVuota, ultimi_arrivi: [riga] }) });
    const home = avvia("/");
    await screen.findByText("Arrivati per la validazione");
    expect(await violazioni()).toEqual([]);
    home.unmount(); vi.unstubAllGlobals();

    simula({ "GET /auth/me": () => me("operatore"), "GET /home": () => homeVuota, "GET /pratiche/p1": () => dettaglio({ stato: "IN_LAVORAZIONE" }),
             "GET /vocabolari": () => voc, "GET /temi": () => [] });
    avvia("/pratiche/p1");
    await screen.findByRole("tablist");
    expect(await violazioni()).toEqual([]);
  });
});
