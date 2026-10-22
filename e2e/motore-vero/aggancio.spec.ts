/**
 * Aggancio con il motore VERO: backoffice → API → coda → worker → motore (classificatore-esposti-v2)
 * via HTTP sulla rete esposti_interna. Documenti SINTETICI del motore (tests/dati_sintetici, montati in
 * sola lettura). Verifica che ogni documento arrivi all'Inbox con testo, scheda, proposta, temi e
 * avviso di lettura incerta; misura il tempo di analisi per documento.
 * Si lancia con scripts/prova-motore-vero.sh (vedi docs/avvio.md).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "password-sintetica-1";
const UFFICIO = "Medicina Veterinaria";
const DATI = process.env.DATI_SINTETICI ?? "/dati-sintetici";
const TEMI = ["Cani", "Gatti e colonie feline", "Animali da reddito", "Avvelenamenti"];

type Documento = { chiave: string; file: string; nome: string; mime: string; tipo: string; incerta: boolean };

// Stessi documenti e nomi dichiarati della prova del motore (tests/prova_motore_vero.py): tutti inventati.
const DOCUMENTI: Documento[] = [
  { chiave: "digitale", file: "digitali/esposto_digitale.pdf", nome: "esposto_digitale.pdf", mime: "application/pdf", tipo: "digitale", incerta: false },
  { chiave: "word", file: "digitali/riscontro_word.docx", nome: "riscontro_word.docx",
    mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", tipo: "Word", incerta: false },
  { chiave: "scansione", file: "scansioni/email_inoltrata.pdf", nome: "Prot. 12345.08-04-2025.pdf", mime: "application/pdf", tipo: "scansione", incerta: false },
  { chiave: "mano1", file: "scansioni/mano_1.pdf", nome: "mano_1.pdf", mime: "application/pdf", tipo: "manoscritto", incerta: true },
  { chiave: "mano2", file: "scansioni/mano_2.pdf", nome: "12 Esposto 54400.20-07-2025.pdf", mime: "application/pdf", tipo: "manoscritto", incerta: true },
  { chiave: "mano3", file: "scansioni/mano_3.pdf", nome: "esposto.pdf", mime: "application/pdf", tipo: "manoscritto", incerta: true },
];
const titolo = (d: Documento) => `AGGANCIO ${d.chiave}`;
const ids: Record<string, string> = {};
const analisi: Record<string, any> = {};

async function accedi(page: Page, utente: string) {
  await page.goto("/accedi");
  await page.getByLabel("Nome utente").fill(utente);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Accedi" }).click();
  await expect(page.getByRole("navigation", { name: "Menu principale" })).toBeVisible();
}

const json = async (page: Page, url: string) => {
  const r = await page.request.get(url);
  expect(r.ok(), `${url} → ${r.status()}`).toBeTruthy();
  return r.json();
};

test.describe.configure({ mode: "serial" });

test("il motore vero è raggiungibile e pronto", async ({ page }) => {
  await accedi(page, "smistatore");
  const salute = await json(page, "/api/v1/salute");
  expect(salute.motore.stato).toBe("ok");
  expect(salute.motore.versione_motore).not.toMatch(/^finto/);
  expect(salute.motore.versione_contratto).toMatch(/^1\./);
});

test("caricamento dal backoffice dei documenti sintetici", async ({ page }) => {
  await accedi(page, "smistatore");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: "Smistamento" }).click();
  await page.getByText("Carica un nuovo esposto").click();
  for (const d of DOCUMENTI) {
    await page.getByLabel("Documenti (anche più di uno)").setInputFiles({
      name: d.nome, mimeType: d.mime, buffer: readFileSync(join(DATI, d.file)),
    });
    await page.getByLabel("Titolo (facoltativo)").fill(titolo(d));
    await page.getByRole("button", { name: "Carica e analizza" }).click();
    const esito = page.getByRole("status").filter({ hasText: "creata: il motore sta analizzando" });
    await expect(esito).toBeVisible();
    const href = await esito.getByRole("link", { name: "Aprila" }).getAttribute("href");
    ids[d.chiave] = href!.split("/").pop()!;
  }
  expect(Object.keys(ids)).toHaveLength(DOCUMENTI.length);
});

test("il motore vero analizza un documento alla volta; tempi per documento", async ({ page }) => {
  await accedi(page, "smistatore");
  const tempi: string[] = [];
  for (const d of DOCUMENTI) {
    await expect.poll(async () => (await json(page, `/api/v1/pratiche/${ids[d.chiave]}`)).stato,
      { timeout: 30 * 60_000, intervals: [5000] }).toBe("DA_SMISTARE");
    const p = await json(page, `/api/v1/pratiche/${ids[d.chiave]}`);
    expect(p.stato_analisi?.stato, `${d.chiave}: analisi (${p.stato_analisi?.codice_errore ?? ""})`).toBe("completata");
    const lavoro = await json(page, `/api/v1/lavori/${p.stato_analisi.lavoro_id}`);
    const secondi = (Date.parse(lavoro.finito_il) - Date.parse(lavoro.iniziato_il)) / 1000;
    tempi.push(`${d.chiave.padEnd(10)} ${d.tipo.padEnd(12)} ${secondi.toFixed(0).padStart(5)} s  (tentativi ${lavoro.tentativi})`);
    analisi[d.chiave] = p.analisi;
  }
  console.log(`Tempi di analisi (dall'inizio del lavoro al risultato):\n${tempi.join("\n")}`);
});

for (const d of DOCUMENTI) {
  test(`risultato completo dal motore vero: ${d.chiave}`, async ({ page }) => {
    await accedi(page, "smistatore");
    const a = analisi[d.chiave];
    expect(a.versione_motore).not.toMatch(/^finto/);
    expect(a.versione_contratto).toMatch(/^1\./);
    // lettura incerta: sui fogli a mano sì, sulle stampe e sui file digitali no
    expect(a.lettura_incerta, `${d.chiave}: lettura incerta`).toBe(d.incerta);
    // scheda con le voci del contratto, ogni voce valorizzata con frase e pagina
    for (const campo of ["data_doc", "comune", "ambito", "problematica", "elementi"]) expect(a.scheda).toHaveProperty(campo);
    for (const campo of ["ambito", "problematica", "elementi"])
      for (const v of a.scheda[campo]) { expect(v.frase.length).toBeGreaterThan(0); expect(v.pagina).toBeGreaterThan(0); }
    // proposta con motivo e domanda decisiva
    expect(a.proposta.esito).toBeTruthy();
    expect(a.proposta.urgenza).toBeTruthy();
    expect(Array.isArray(a.proposta.azione)).toBe(true);
    expect(a.proposta.motivo.length).toBeGreaterThan(0);
    expect(a.proposta.domanda_decisiva.length).toBeGreaterThan(0);
    // temi: solo dal vocabolario del contratto, con frase
    for (const t of a.temi_proposti) { expect(TEMI).toContain(t.valore); expect(t.frase.length).toBeGreaterThan(0); }
    // testo letto, pagina per pagina, dall'archivio
    const documenti = await json(page, `/api/v1/pratiche/${ids[d.chiave]}/documenti`);
    const testo = await json(page, `/api/v1/documenti/${documenti[0].id}/testo`);
    expect(testo.pagine.length).toBeGreaterThan(0);
    expect(testo.pagine.map((p: { testo: string }) => p.testo).join(" ").trim().length).toBeGreaterThan(50);
  });
}

test("almeno un documento ha temi proposti per il fascicolo", async () => {
  expect(Object.values(analisi).some((a) => a.temi_proposti.length > 0)).toBe(true);
});

test("smistamento: lo smistatore assegna le pratiche all'ufficio", async ({ page }) => {
  await accedi(page, "smistatore");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: "Smistamento" }).click();
  for (const d of DOCUMENTI) {
    const voce = page.locator(".voce").filter({ has: page.getByRole("link", { name: titolo(d), exact: true }) });
    await voce.getByRole("button", { name: "Assegna" }).click();
    const dialogo = page.getByRole("dialog");
    await dialogo.getByLabel("Ufficio").selectOption({ label: UFFICIO });
    await dialogo.getByRole("button", { name: "Assegna" }).click();
    await expect(dialogo).toHaveCount(0);
    await expect(page.getByRole("link", { name: titolo(d), exact: true })).toHaveCount(0);
  }
});

test("Inbox: ogni documento arriva con proposta, valutazione precompilata, temi e avviso", async ({ page }) => {
  await accedi(page, "op.vet");
  await page.getByRole("navigation", { name: "Menu principale" }).getByRole("link", { name: /Inbox/ }).click();
  const coda = page.getByRole("region", { name: "Coda" });
  for (const d of DOCUMENTI) {
    const a = analisi[d.chiave];
    await coda.getByRole("link", { name: new RegExp(titolo(d)) }).click();
    await expect(page.getByRole("heading", { name: titolo(d) })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Lettura incerta." })).toHaveCount(d.incerta ? 1 : 0);
    const proposta = page.getByRole("region", { name: "Proposta dell'IA" });
    await expect(proposta).toContainText("Un suggerimento: decide sempre la persona.");
    await expect(proposta).toContainText(a.proposta.esito);
    await expect(proposta).toContainText("Domanda decisiva");
    const modulo = page.getByRole("form", { name: "La tua valutazione" });
    await expect(modulo.getByRole("radio", { name: a.proposta.esito, exact: true })).toBeChecked();
    await expect(modulo.getByRole("radio", { name: a.proposta.urgenza, exact: true })).toBeChecked();
    for (const t of a.temi_proposti) await expect(modulo.getByRole("group", { name: t.valore })).toContainText("Proposto dall'IA");
  }
});
