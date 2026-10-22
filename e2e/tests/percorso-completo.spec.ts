/**
 * Prova end-to-end nel browser contro lo stack vero (backoffice → API → coda → worker → finto motore via HTTP).
 * Solo documenti SINTETICI: il finto motore sceglie lo scenario dal nome del file
 * (backend/motore/finto/app.py). Database pulito a ogni esecuzione (scripts/prove.sh e2e).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";

const PASSWORD = "password-sintetica-1";
const UFFICIO = "Medicina Veterinaria";

type Scenario = {
  chiave: string; file: string;
  errore?: string;          // codice d'errore atteso (analisi non disponibile)
  testo?: RegExp;           // frase del testo letto (pagina 1)
  tipo?: string;            // tipo di documento mostrato nei dati della pratica
  incerta?: boolean;        // avviso di lettura incerta
};

// I 9 scenari del finto motore: lettura pulita, riscontro, lettura incerta, formato non supportato,
// illeggibile, tempo scaduto (3 tentativi), instabile (riesce al secondo), occupato (429), fuori contratto.
const SCENARI: Scenario[] = [
  { chiave: "pulito", file: "esposto_e2e_cani.pdf", testo: /via delle Robinie/, tipo: "Esposto" },
  { chiave: "riscontro", file: "riscontro_e2e_cane.pdf", testo: /sopralluogo/, tipo: "Riscontro ATS" },
  { chiave: "manoscritto", file: "foglio_manoscritto_e2e.pdf", testo: /pollaio/, tipo: "Esposto", incerta: true },
  { chiave: "formato", file: "lettera_e2e.pages", errore: "formato_non_supportato" },
  { chiave: "illeggibile", file: "scansione_illeggibile_e2e.pdf", errore: "documento_illeggibile" },
  { chiave: "scaduto", file: "esposto_scaduto_e2e.pdf", errore: "tempo_scaduto" },
  { chiave: "instabile", file: "esposto_instabile_e2e.pdf", testo: /via delle Robinie/, tipo: "Esposto" },
  { chiave: "occupato", file: "esposto_occupato_e2e.pdf", testo: /via delle Robinie/, tipo: "Esposto" },
  { chiave: "invalido", file: "esposto_invalido_e2e.pdf", errore: "risultato_non_valido" },
];
const titolo = (s: Scenario) => `E2E ${s.chiave}`;
const ids: Record<string, string> = {};

async function accedi(page: Page, utente: string) {
  await page.goto("/accedi");
  await page.getByLabel("Nome utente").fill(utente);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Accedi" }).click();
  await expect(page.getByRole("navigation", { name: "Menu principale" })).toBeVisible();
}

async function nuovaPagina(browser: Browser, utente: string) {
  const page = await (await browser.newContext()).newPage();
  await accedi(page, utente);
  return page;
}

test.describe.configure({ mode: "serial" });

test("caricamento dal backoffice: una pratica per scenario, in coda per il motore", async ({ page }) => {
  await accedi(page, "smistatore");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: "Smistamento" }).click();
  await page.getByText("Carica un nuovo esposto").click();
  for (const s of SCENARI) {
    const documento = {
      name: s.file, mimeType: s.file.endsWith(".pdf") ? "application/pdf" : "application/octet-stream",
      buffer: Buffer.from(`contenuto sintetico di prova (${s.file})`),
    };
    await page.getByLabel("Documenti (anche più di uno)").setInputFiles(documento);
    if (!s.file.endsWith(".pdf")) {
      // il modulo accetta solo PDF, Word e RTF: il formato non supportato si prova direttamente dall'API,
      // per verificare che il motore lo rifiuti e la pratica vada comunque allo smistamento
      await expect(page.getByRole("alert")).toContainText("Formato non accettato");
      await expect(page.getByRole("button", { name: "Carica e analizza" })).toBeDisabled();
      const r = await page.request.post("/api/v1/pratiche", { multipart: { files: documento, titolo: titolo(s) } });
      expect(r.status()).toBe(201);
      ids[s.chiave] = (await r.json()).pratica.id;
      continue;
    }
    await page.getByLabel("Titolo (facoltativo)").fill(titolo(s));
    await page.getByRole("button", { name: "Carica e analizza" }).click();
    const esito = page.getByRole("status").filter({ hasText: "creata: il motore sta analizzando" });
    await expect(esito).toBeVisible();
    const href = await esito.getByRole("link", { name: "Aprila" }).getAttribute("href");
    ids[s.chiave] = href!.split("/").pop()!;
  }
  expect(Object.keys(ids)).toHaveLength(SCENARI.length);
});

test("la coda si svuota: il worker porta ogni pratica fuori da «In analisi»", async ({ page }) => {
  await accedi(page, "smistatore");
  for (const s of SCENARI) {
    await expect.poll(async () => (await (await page.request.get(`/api/v1/pratiche/${ids[s.chiave]}`)).json()).stato,
      { timeout: 180_000, intervals: [1000] }).toBe("DA_SMISTARE");
  }
  const salute = await (await page.request.get("/api/v1/salute")).json();
  expect(salute).toMatchObject({ stato: "ok", coda: { in_coda: 0, in_corso: 0 }, motore: { stato: "ok", versione_motore: "finto-1.0.0" } });
});

for (const s of SCENARI) {
  test(`risultato visibile nel backoffice: ${s.chiave}`, async ({ page }) => {
    await accedi(page, "smistatore");
    await page.goto(`/pratiche/${ids[s.chiave]}`);
    await expect(page.getByRole("heading", { name: titolo(s) })).toBeVisible();
    await expect(page.locator(".tag", { hasText: "Da smistare" })).toBeVisible();
    const incerta = page.getByRole("status").filter({ hasText: "Lettura incerta." });
    const nonDisponibile = page.getByRole("status").filter({ hasText: "Analisi non disponibile." });

    if (s.errore) {
      // errore: avviso, nessuna proposta, codice nel documento; la pratica va comunque allo smistamento
      await expect(nonDisponibile).toBeVisible();
      await expect(page.getByRole("region", { name: "Proposta dell'IA" })).toHaveCount(0);
      await page.getByRole("tab", { name: "Documenti" }).click();
      await expect(page.getByRole("region", { name: "Documenti" })).toContainText(`Analisi non disponibile (${s.errore})`);
      return;
    }
    await expect(nonDisponibile).toHaveCount(0);
    await expect(incerta).toHaveCount(s.incerta ? 1 : 0);
    // scheda e proposta (con motivo e domanda decisiva), separata dalla valutazione
    const dati = page.getByRole("region", { name: "Dati della pratica" });
    await expect(dati).toContainText(s.tipo!);
    const proposta = page.getByRole("region", { name: "Proposta dell'IA" });
    await expect(proposta).toContainText("Un suggerimento: decide sempre la persona.");
    await expect(proposta).toContainText("Perché");
    await expect(proposta).toContainText("Domanda decisiva");
    await expect(proposta).toContainText("Frase del documento");
    // testo letto, pagina per pagina
    await page.getByRole("tab", { name: "Documenti" }).click();
    await expect(page.getByRole("region", { name: "Documenti" })).toContainText("Analizzato");
    await page.getByRole("button", { name: "Testo letto" }).click();
    const dialogo = page.getByRole("dialog", { name: "Testo letto dal motore" });
    await expect(dialogo).toContainText("Pagina 1");
    await expect(dialogo).toContainText(s.testo!);
    if (s.incerta) await expect(dialogo).toContainText("Lettura incerta.");
  });
}

test("smistamento: lo smistatore assegna le pratiche all'ufficio", async ({ page }) => {
  await accedi(page, "smistatore");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: "Smistamento" }).click();
  for (const chiave of ["pulito", "manoscritto", "instabile"]) {
    const voce = page.locator(".voce").filter({ has: page.getByRole("link", { name: `E2E ${chiave}`, exact: true }) });
    await voce.getByRole("button", { name: "Assegna" }).click();
    const dialogo = page.getByRole("dialog");
    await dialogo.getByLabel("Ufficio").selectOption({ label: UFFICIO });
    await dialogo.getByRole("button", { name: "Assegna" }).click();
    await expect(dialogo).toHaveCount(0);
    await expect(page.getByRole("link", { name: `E2E ${chiave}`, exact: true })).toHaveCount(0);
  }
});

test("Inbox: proposta, temi e avviso; la validazione accetta i temi non toccati", async ({ page }) => {
  await accedi(page, "op.vet");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: /Inbox/ }).click();
  const coda = page.getByRole("region", { name: "Coda" });

  // foglio manoscritto: lettura incerta segnalata accanto alla proposta
  await coda.getByRole("link", { name: /E2E manoscritto/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "Lettura incerta." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "E2E manoscritto" })).toBeVisible();

  // esposto pulito: precompilato con la proposta, tema «Cani» proposto dall'IA, nessun avviso
  await coda.getByRole("link", { name: /E2E pulito/ }).click();
  await expect(page.getByRole("heading", { name: "E2E pulito" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Lettura incerta." })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Proposta dell'IA" })).toContainText("Accolto");
  const modulo = page.getByRole("form", { name: "La tua valutazione" });
  await expect(modulo.getByRole("radio", { name: "Accolto" })).toBeChecked();
  await expect(modulo.getByRole("radio", { name: "Normale" })).toBeChecked();
  const tema = modulo.getByRole("group", { name: "Cani" });
  await expect(tema).toContainText("Proposto dall'IA");
  await expect(modulo).toContainText("che non scarti vengono accettati con la conferma");
  await modulo.getByRole("button", { name: "Conferma e vai al prossimo" }).click();
  await expect(coda.getByRole("link", { name: /E2E pulito/ })).toHaveCount(0);

  const p = await (await page.request.get(`/api/v1/pratiche/${ids.pulito}`)).json();
  expect(p.stato).toBe("IN_LAVORAZIONE");
  expect(p.valutazione.valutazione).toMatchObject({ origine: "applicazione", compilata: true, esito: "Accolto" });
  expect(p.temi.map((t: { codice: string; stato: string; origine: string }) => [t.codice, t.stato, t.origine])).toEqual([["cani", "confermato", "ia"]]);
});

test("percorso a pallini della pratica validata", async ({ page }) => {
  await accedi(page, "op.vet");
  await page.goto(`/pratiche/${ids.pulito}?scheda=percorso`);
  const percorso = page.getByRole("region", { name: "Percorso della pratica" });
  await expect(percorso.locator(".passo").first()).toBeVisible();
  const passi = await percorso.locator(".passo").evaluateAll((els) => els.map((e) => [
    e.querySelector(".titolo")?.textContent ?? "", e.classList.contains("concluso") ? "concluso" : e.classList.contains("in_corso") ? "in_corso" : "atteso"]));
  expect(passi).toEqual([
    ["Esposto ricevuto", "concluso"],
    ["Proposta dell'IA", "concluso"],
    [`Assegnata a ${UFFICIO}`, "concluso"],
    ["Validazione", "concluso"],
    ["Riscontro", "atteso"],
  ]);
  await expect(percorso).toContainText("passo concluso");
  await page.getByRole("tab", { name: "Riepilogo" }).click();
  await expect(page.locator(".tag", { hasText: "In lavorazione" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Dati della pratica" })).toContainText("Cani");   // fascicolo
});

test("valutazione salvata da due persone insieme: la seconda riceve il conflitto e la versione aggiornata", async ({ browser }) => {
  const a = await nuovaPagina(browser, "op.vet");
  const b = await nuovaPagina(browser, "op.vet");
  for (const pg of [a, b]) {
    await pg.goto(`/inbox/${ids.instabile}`);
    await expect(pg.getByRole("heading", { name: "E2E instabile" })).toBeVisible();
  }
  const ma = a.getByRole("form", { name: "La tua valutazione" });
  const mb = b.getByRole("form", { name: "La tua valutazione" });
  await ma.getByRole("radio", { name: "Alta" }).check();
  await ma.getByRole("button", { name: "Salva bozza" }).click();
  await expect(ma.getByText("Bozza salvata.")).toBeVisible();

  await mb.getByRole("radio", { name: "Immediata" }).check();
  await mb.getByRole("button", { name: "Salva bozza" }).click();
  await expect(mb.getByRole("alert")).toContainText("Un'altra persona ha salvato questa valutazione");
  await expect(mb.getByRole("radio", { name: "Alta" })).toBeChecked();            // ricaricata la versione di A
  await mb.getByRole("radio", { name: "Immediata" }).check();
  await mb.getByRole("button", { name: "Salva bozza" }).click();
  await expect(mb.getByText("Bozza salvata.")).toBeVisible();

  const v = await (await b.request.get(`/api/v1/pratiche/${ids.instabile}/valutazione`)).json();
  expect(v.valutazione).toMatchObject({ urgenza: "Immediata", versione: 2, compilata: false });
});
