/**
 * Prove end-to-end: l'app vera (UI + client) contro un backend vero con dati demo.
 * Si attivano solo con LIVE_API_URL (es. http://localhost:8000, dopo `python -m api.demo`):
 *   LIVE_API_URL=http://localhost:8000 npm test
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";

const BACKEND = process.env.LIVE_API_URL;
const PASSWORD = "password-sintetica-1";
const realFetch = globalThis.fetch;
let cookie = "";

function installaFetch() {
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    if (cookie) headers.set("cookie", cookie);
    const r = await realFetch(BACKEND + String(input), { ...init, headers, credentials: undefined });
    const impostati = r.headers.getSetCookie?.() ?? [];
    if (impostati.length) cookie = impostati.map((c) => c.split(";")[0] ?? "").filter((c) => !c.endsWith("=")).join("; ");
    return r;
  });
}

/** Chiamata diretta all'API con la sessione corrente, per verificare cosa è successo davvero. */
const apiDiretta = async (percorso: string) => (await fetch(`/api/v1${percorso}`)).json();

function avvia(percorso = "/accedi") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[percorso]}><App /></MemoryRouter>
    </QueryClientProvider>,
  );
}

async function accedi(utente: string, percorso = "/accedi") {
  cookie = "";
  const u = userEvent.setup();
  avvia(percorso);
  await u.type(await screen.findByLabelText("Nome utente"), utente);
  await u.type(screen.getByLabelText("Password"), PASSWORD);
  await u.click(screen.getByRole("button", { name: "Accedi" }));
  return u;
}

const attesa = { timeout: 8000 };

describe.skipIf(!BACKEND)("end-to-end contro il backend vero", () => {
  beforeEach(() => { installaFetch(); });
  afterAll(() => { vi.unstubAllGlobals(); });

  it("credenziali errate: messaggio e nessun accesso", async () => {
    cookie = "";
    const u = userEvent.setup();
    avvia();
    await u.type(await screen.findByLabelText("Nome utente"), "op.vet");
    await u.type(screen.getByLabelText("Password"), "sbagliata");
    await u.click(screen.getByRole("button", { name: "Accedi" }));
    expect(await screen.findByRole("alert", undefined, attesa)).toHaveTextContent("Credenziali non valide");
  });

  it("operatore: Home con contatori e menu del suo ruolo (senza Smistamento)", async () => {
    await accedi("op.vet");
    expect(await screen.findByRole("heading", { name: "Home" }, attesa)).toBeInTheDocument();
    const menu = screen.getByRole("navigation", { name: "Menu principale" });
    expect(within(menu).getAllByRole("link").map((l) => l.textContent?.replace(/\d+$/, ""))).toEqual(
      ["Home", "Inbox", "Fascicoli", "Gestione pratiche"]);
    expect(await screen.findByText("Da validare", undefined, attesa)).toBeInTheDocument();
    expect(await screen.findByText("Arrivati per la validazione", undefined, attesa)).toBeInTheDocument();
  });

  it("Inbox: proposta dell'IA, valutazione precompilata, avviso di lettura incerta", async () => {
    await accedi("op.vet", "/accedi");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("link", { name: /Inbox/ }, attesa));
    // la coda contiene il foglio a mano: lettura incerta
    await u.click(await screen.findByRole("link", { name: /Foglio manoscritto pollaio/ }, attesa));
    expect(await screen.findByText(/Lettura incerta\./, undefined, attesa)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Proposta dell'IA" })).toHaveTextContent("Medicina Veterinaria");
    const modulo = screen.getByRole("form", { name: "La tua valutazione" });
    expect(within(modulo).getByRole("radio", { name: "Accolto" })).toBeChecked();      // precompilata con la proposta
    expect(within(modulo).getByRole("radio", { name: "Bassa" })).toBeChecked();
  });

  it("Inbox: confermare porta la pratica in lavorazione e passa alla successiva", async () => {
    const u = await accedi("op.vet");
    await u.click(await screen.findByRole("link", { name: /Inbox/ }, attesa));
    await u.click(await screen.findByRole("link", { name: /Esposto cani via robinie/ }, attesa));
    const modulo = await screen.findByRole("form", { name: "La tua valutazione" }, attesa);
    // correggo l'urgenza rispetto alla proposta: nascerà un disaccordo IA–operatore
    await u.click(within(modulo).getByRole("radio", { name: "Alta" }));
    await u.click(within(modulo).getByRole("button", { name: "Conferma e vai al prossimo" }));
    await waitFor(() => expect(screen.queryByRole("link", { name: /Esposto cani via robinie/ })).not.toBeInTheDocument(), attesa);

    const trovate = await apiDiretta("/pratiche?testo=robinie");
    const p = trovate.items[0];
    expect(p.stato).toBe("IN_LAVORAZIONE");
    expect(p.valutazione).toMatchObject({ esito: "Accolto", urgenza: "Alta", origine: "applicazione", compilata: true });
    expect(p.disaccordo.map((d: { campo: string }) => d.campo)).toEqual(["urgenza"]);
    expect(p.temi).toEqual(["Cani"]);
  });

  it("Gestione pratiche: ricerca, esito con disaccordo e apertura del percorso", async () => {
    const u = await accedi("op.vet");
    await u.click(await screen.findByRole("link", { name: "Gestione pratiche" }, attesa));
    await u.type(await screen.findByLabelText("Protocollo, comune o parole"), "robinie");
    await u.click(screen.getByRole("button", { name: "Cerca" }));
    const riga = (await screen.findByRole("row", { name: /Esposto cani via robinie/ }, attesa));
    expect(riga).toHaveTextContent("In lavorazione");
    expect(riga).toHaveTextContent("Accolto");
    expect(riga).toHaveTextContent(/IA: urgenza Normale, operatore: Alta/);
    expect(riga).toHaveTextContent("Cani");

    await u.click(within(riga).getByRole("link"));
    await u.click(await screen.findByRole("tab", { name: "Percorso" }, attesa));
    const percorso = await screen.findByRole("region", { name: "Percorso della pratica" }, attesa);
    await waitFor(() => expect(percorso).toHaveTextContent("Esposto ricevuto"), attesa);
    expect(percorso).toHaveTextContent("Proposta dell'IA");
    expect(percorso).toHaveTextContent("Validazione");
    expect(percorso).toHaveTextContent("Riscontro");
  });

  it("un operatore non vede le pratiche di un altro ufficio", async () => {
    const u = await accedi("op.igp");
    await u.click(await screen.findByRole("link", { name: "Gestione pratiche" }, attesa));
    expect(await screen.findByText(/rumori laboratorio/i, undefined, attesa)).toBeInTheDocument();
    expect(screen.queryByText(/robinie/i)).not.toBeInTheDocument();
    expect((await apiDiretta("/pratiche?per_page=100")).items.every((p: { ufficio: { codice: string } }) => p.ufficio.codice === "IGP")).toBe(true);
  });

  it("smistatore: assegna a un ufficio una pratica da smistare", async () => {
    const u = await accedi("smistatore");
    await u.click(await screen.findByRole("link", { name: "Smistamento" }, attesa));
    const voce = (await screen.findByRole("link", { name: /cane libero/i }, attesa)).closest(".voce") as HTMLElement;
    await u.click(within(voce).getByRole("button", { name: "Assegna" }));
    const dialogo = await screen.findByRole("dialog", undefined, attesa);
    await within(dialogo).findByRole("option", { name: "Igiene pubblica" }, attesa);   // gli uffici arrivano dal server
    await u.selectOptions(within(dialogo).getByLabelText("Ufficio"), "Igiene pubblica");
    await u.click(within(dialogo).getByRole("button", { name: "Assegna" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument(), attesa);
    const p = (await apiDiretta("/pratiche?testo=Cane+libero")).items[0];
    expect(p).toMatchObject({ stato: "DA_VALIDARE", ufficio: { codice: "IGP" } });
  });

  it("amministratore: atterra su Uffici, non vede le pratiche, crea un utente", async () => {
    const u = await accedi("admin");
    expect(await screen.findByRole("heading", { name: "Uffici" }, attesa)).toBeInTheDocument();
    const menu = screen.getByRole("navigation", { name: "Menu principale" });
    expect(within(menu).getAllByRole("link").map((l) => l.textContent)).toEqual(["Uffici", "Utenti"]);
    await u.click(within(menu).getByRole("link", { name: "Utenti" }));
    const form = await screen.findByRole("form", { name: "Nuovo utente" }, attesa);
    const nome = `prova.${Date.now() % 100000}`;
    await u.type(within(form).getByLabelText("Nome utente"), nome);
    await u.type(within(form).getByLabelText("Nome e cognome"), "Prova Sintetica");
    await within(form).findByRole("option", { name: "Medicina Veterinaria" }, attesa);
    await u.selectOptions(within(form).getByLabelText("Ufficio"), "Medicina Veterinaria");
    await u.type(within(form).getByLabelText(/Password iniziale/), "una-password-lunga-1");
    await u.click(within(form).getByRole("button", { name: "Crea utente" }));
    expect(await screen.findByText(nome, { exact: false }, attesa)).toBeInTheDocument();
  });

  it("Fascicoli: il tema confermato compare con il suo percorso", async () => {
    const u = await accedi("op.vet");
    await u.click(await screen.findByRole("link", { name: "Fascicoli" }, attesa));
    expect(await screen.findByRole("heading", { name: /Fascicolo: Cani/ }, attesa)).toBeInTheDocument();
    const percorso = await screen.findByRole("region", { name: "Percorso del fascicolo" }, attesa);
    await waitFor(() => expect(percorso).toHaveTextContent("Esposto cani via robinie"), attesa);
    const storico = await screen.findByRole("region", { name: "Storico della pratica" }, attesa);
    await waitFor(() => expect(storico).toHaveTextContent("Esposto ricevuto"), attesa);
  });

  it("esci: la sessione si chiude e le pagine protette rimandano all'accesso", async () => {
    const u = await accedi("op.vet");
    await u.click(await screen.findByRole("button", { name: "Esci" }, attesa));
    expect(await screen.findByRole("form", { name: "Accesso" }, attesa)).toBeInTheDocument();
    expect((await fetch("/api/v1/auth/me")).status).toBe(401);
  });
});
