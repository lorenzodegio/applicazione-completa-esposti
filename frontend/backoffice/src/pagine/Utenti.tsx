import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/endpoints";
import type { Ruolo, Utente } from "../api/tipi";
import { Caricamento, Dialogo, Intestazione, MessaggioErrore } from "../componenti/ui";
import { ETICHETTA_RUOLO } from "../formati";
import { useSessione } from "../sessione";

const RUOLI: Ruolo[] = ["smistatore", "operatore", "amministratore"];

export function Utenti() {
  const { me } = useSessione();
  const qc = useQueryClient();
  const utenti = useQuery({ queryKey: ["utenti"], queryFn: api.utenti });
  const uffici = useQuery({ queryKey: ["uffici"], queryFn: api.uffici });
  const aggiorna = () => qc.invalidateQueries();
  const [password, setPassword] = useState<Utente | null>(null);
  const [nuovaPassword, setNuovaPassword] = useState("");
  const [f, setF] = useState({ username: "", nome: "", email: "", ruolo: "operatore" as Ruolo, ufficio: "", password: "" });

  const crea = useMutation({
    mutationFn: () => api.creaUtente({
      username: f.username.trim(), nome_visualizzato: f.nome.trim(), email: f.email.trim() || null,
      ruolo: f.ruolo, ufficio_id: f.ruolo === "operatore" ? f.ufficio : null, password: f.password,
    }),
    onSuccess: async () => { setF({ ...f, username: "", nome: "", email: "", password: "" }); await aggiorna(); },
  });
  const attiva = useMutation({ mutationFn: (v: { id: string; attivo: boolean }) => api.modificaUtente(v.id, { attivo: v.attivo }), onSuccess: aggiorna });
  const reimposta = useMutation({
    mutationFn: () => api.reimpostaPassword(password!.id, nuovaPassword),
    onSuccess: async () => { setPassword(null); setNuovaPassword(""); await aggiorna(); },
  });
  const sceltaUffici = (uffici.data ?? []).filter((u) => u.attivo);

  return (
    <>
      <Intestazione titolo="Utenti" sotto="Chi accede e con quale ruolo. L'amministratore non vede le pratiche." />
      <section className="card" aria-label="Elenco utenti">
        {utenti.isLoading && <Caricamento />}
        <MessaggioErrore errore={utenti.error ?? attiva.error} />
        <div className="scorrevole">
          <table className="tabella">
            <thead><tr><th scope="col">Utente</th><th scope="col">Ruolo</th><th scope="col">Ufficio</th><th scope="col">Stato</th><th scope="col"><span className="solo-lettori">Azioni</span></th></tr></thead>
            <tbody>
              {utenti.data?.map((u) => (
                <tr key={u.id}>
                  <td><strong>{u.nome_visualizzato}</strong><span className="secondaria">{u.username}{u.email ? ` · ${u.email}` : ""}</span></td>
                  <td>{ETICHETTA_RUOLO[u.ruolo]}</td>
                  <td>{u.ufficio?.nome ?? "—"}</td>
                  <td>{u.attivo ? <span className="tag">Attivo</span> : <span className="tag neutro">Disattivato</span>}</td>
                  <td>
                    <div className="riga">
                      <button type="button" className="btn secondario piccolo" onClick={() => setPassword(u)}>Reimposta password</button>
                      {u.id !== me?.utente.id && (
                        <button type="button" className="btn secondario piccolo" onClick={() => attiva.mutate({ id: u.id, attivo: !u.attivo })}>{u.attivo ? "Disattiva" : "Riattiva"}</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <form className="card pila" aria-label="Nuovo utente" onSubmit={(e) => { e.preventDefault(); crea.mutate(); }}>
        <h2>Nuovo utente</h2>
        <div className="filtri">
          <div className="campo"><label htmlFor="n-user">Nome utente</label><input id="n-user" type="text" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} required minLength={3} /></div>
          <div className="campo"><label htmlFor="n-nome">Nome e cognome</label><input id="n-nome" type="text" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} required /></div>
          <div className="campo"><label htmlFor="n-email">Email (facoltativa)</label><input id="n-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
        </div>
        <div className="filtri">
          <div className="campo">
            <label htmlFor="n-ruolo">Ruolo</label>
            <select id="n-ruolo" value={f.ruolo} onChange={(e) => setF({ ...f, ruolo: e.target.value as Ruolo })}>
              {RUOLI.map((r) => <option key={r} value={r}>{ETICHETTA_RUOLO[r]}</option>)}
            </select>
          </div>
          {f.ruolo === "operatore" && (
            <div className="campo">
              <label htmlFor="n-uff">Ufficio</label>
              <select id="n-uff" value={f.ufficio} onChange={(e) => setF({ ...f, ufficio: e.target.value })} required>
                <option value="">Scegli…</option>
                {sceltaUffici.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
            </div>
          )}
          <div className="campo"><label htmlFor="n-pw">Password iniziale (almeno 10 caratteri)</label><input id="n-pw" type="password" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required minLength={10} /></div>
        </div>
        <MessaggioErrore errore={crea.error} />
        <div><button type="submit" className="btn" disabled={crea.isPending}>Crea utente</button></div>
      </form>

      {password && (
        <Dialogo titolo={`Reimposta la password di ${password.nome_visualizzato}`} onChiudi={() => setPassword(null)}>
          <form className="pila" onSubmit={(e) => { e.preventDefault(); reimposta.mutate(); }}>
            <div className="campo">
              <label htmlFor="pw-nuova">Nuova password (almeno 10 caratteri)</label>
              <input id="pw-nuova" type="password" autoComplete="new-password" value={nuovaPassword} onChange={(e) => setNuovaPassword(e.target.value)} minLength={10} required />
            </div>
            <div className="sottotitolo" style={{ fontSize: 14 }}>Le sessioni aperte dell'utente vengono chiuse.</div>
            <MessaggioErrore errore={reimposta.error} />
            <div className="riga">
              <button type="submit" className="btn" disabled={reimposta.isPending || nuovaPassword.length < 10}>Reimposta</button>
              <button type="button" className="btn secondario" onClick={() => setPassword(null)}>Annulla</button>
            </div>
          </form>
        </Dialogo>
      )}
    </>
  );
}
