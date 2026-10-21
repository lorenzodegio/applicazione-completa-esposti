import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/endpoints";
import type { PraticaDettaglio } from "../../api/tipi";
import { Caricamento, MessaggioErrore, Vuoto } from "../../componenti/ui";
import { dataOra } from "../../formati";

const AZIONI: Record<string, string> = {
  "pratica.crea": "Pratica creata", "pratica.assegna": "Assegnata a un ufficio", "pratica.riassegna": "Riassegnata",
  "pratica.restituisci": "Restituita allo smistamento", "pratica.valida": "Validata", "pratica.cambia_stato": "Stato cambiato",
  "pratica.modifica": "Dati modificati", "pratica.analisi_conclusa": "Analisi conclusa", "valutazione.salva": "Valutazione salvata",
  "valutazione.conferma": "Valutazione confermata", "temi.proponi": "Temi proposti dall'IA", "temi.decidi": "Temi decisi",
  "nota.crea": "Nota aggiunta", "attivita.crea": "Azione aggiunta", "attivita.modifica": "Azione aggiornata",
  "collegamento.crea": "Pratica collegata", "collegamento.rimuovi": "Collegamento rimosso", "documento.carica": "Documento caricato",
  "documento.apri": "Documento aperto", "documento.testo": "Testo letto", "motore.accoda": "Analisi richiesta",
  "motore.completato": "Analisi completata", "motore.errore": "Analisi non riuscita", "motore.ritenta": "Nuovo tentativo di analisi",
};

export function TabNote({ p }: { p: PraticaDettaglio }) {
  const qc = useQueryClient();
  const note = useQuery({ queryKey: ["note", p.id], queryFn: () => api.note(p.id) });
  const registro = useQuery({ queryKey: ["registro", p.id], queryFn: () => api.registro(p.id) });
  const [testo, setTesto] = useState("");
  const nuova = useMutation({
    mutationFn: () => api.nuovaNota(p.id, testo.trim()),
    onSuccess: async () => { setTesto(""); await qc.invalidateQueries(); },
  });
  return (
    <div className="pila">
      <section className="card pila" aria-label="Note interne">
        <h2>Note interne</h2>
        {note.isLoading && <Caricamento />}
        {note.data?.length === 0 && <Vuoto>Nessuna nota.</Vuoto>}
        <div className="elenco-voci">
          {note.data?.map((n) => (
            <div key={n.id} className="voce"><span className="corpo"><span className="meta">{dataOra(n.creata_il)}</span><span style={{ whiteSpace: "pre-wrap" }}>{n.testo}</span></span></div>
          ))}
        </div>
        <form className="pila" onSubmit={(e) => { e.preventDefault(); if (testo.trim()) nuova.mutate(); }}>
          <div className="campo">
            <label htmlFor="nuova-nota">Aggiungi una nota (non si modifica: una correzione è una nuova nota)</label>
            <textarea id="nuova-nota" value={testo} onChange={(e) => setTesto(e.target.value)} />
          </div>
          <MessaggioErrore errore={nuova.error} />
          <div><button type="submit" className="btn" disabled={!testo.trim() || nuova.isPending}>Aggiungi nota</button></div>
        </form>
      </section>
      <section className="card" aria-label="Registro delle azioni">
        <h2>Registro delle azioni</h2>
        <MessaggioErrore errore={registro.error} />
        <div className="scorrevole">
          <table className="tabella">
            <thead><tr><th scope="col">Quando</th><th scope="col">Azione</th></tr></thead>
            <tbody>
              {registro.data?.map((r, i) => (
                <tr key={i}><td>{dataOra(r.quando)}</td><td>{AZIONI[r.azione] ?? r.azione}{r.utente_id ? "" : " (automatica)"}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
