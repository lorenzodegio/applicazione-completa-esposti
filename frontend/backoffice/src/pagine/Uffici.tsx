import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/endpoints";
import { Caricamento, Intestazione, MessaggioErrore } from "../componenti/ui";

export function Uffici() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["uffici"], queryFn: api.uffici });
  const [codice, setCodice] = useState("");
  const [nome, setNome] = useState("");
  const aggiorna = () => qc.invalidateQueries();
  const crea = useMutation({
    mutationFn: () => api.creaUfficio({ codice: codice.trim(), nome: nome.trim() }),
    onSuccess: async () => { setCodice(""); setNome(""); await aggiorna(); },
  });
  const attiva = useMutation({ mutationFn: (v: { id: string; attivo: boolean }) => api.modificaUfficio(v.id, { attivo: v.attivo }), onSuccess: aggiorna });
  return (
    <>
      <Intestazione titolo="Uffici" sotto="Gli uffici si disattivano, non si cancellano: lo storico resta." />
      <section className="card" aria-label="Elenco uffici">
        {q.isLoading && <Caricamento />}
        <MessaggioErrore errore={q.error ?? attiva.error} />
        <div className="scorrevole">
          <table className="tabella">
            <thead><tr><th scope="col">Codice</th><th scope="col">Nome</th><th scope="col">Stato</th><th scope="col"><span className="solo-lettori">Azioni</span></th></tr></thead>
            <tbody>
              {q.data?.map((u) => (
                <tr key={u.id}>
                  <td>{u.codice}</td><td>{u.nome}</td>
                  <td>{u.attivo ? <span className="tag">Attivo</span> : <span className="tag neutro">Disattivato</span>}</td>
                  <td><button type="button" className="btn secondario piccolo" onClick={() => attiva.mutate({ id: u.id, attivo: !u.attivo })}>{u.attivo ? "Disattiva" : "Riattiva"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <form className="card pila" aria-label="Nuovo ufficio" onSubmit={(e) => { e.preventDefault(); crea.mutate(); }}>
        <h2>Nuovo ufficio</h2>
        <div className="filtri">
          <div className="campo"><label htmlFor="u-cod">Codice</label><input id="u-cod" type="text" value={codice} onChange={(e) => setCodice(e.target.value)} required maxLength={32} /></div>
          <div className="campo" style={{ flex: "2 1 300px" }}><label htmlFor="u-nome">Nome</label><input id="u-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} required /></div>
        </div>
        <MessaggioErrore errore={crea.error} />
        <div><button type="submit" className="btn" disabled={crea.isPending || !codice.trim() || !nome.trim()}>Crea ufficio</button></div>
      </form>
    </>
  );
}
