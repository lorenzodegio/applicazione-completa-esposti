import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { MessaggioErrore } from "../componenti/ui";
import { paginaIniziale, useSessione } from "../sessione";

export function Accesso() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { me } = useSessione();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const entra = useMutation({
    mutationFn: () => api.login(username.trim(), password),
    onSuccess: (m) => { qc.setQueryData(["me"], m); navigate(paginaIniziale(m.utente.ruolo), { replace: true }); },
  });
  if (me) return <Navigate to={paginaIniziale(me.utente.ruolo)} replace />;
  const invia = (e: FormEvent) => { e.preventDefault(); entra.mutate(); };
  return (
    <div className="accesso">
      <form className="card" onSubmit={invia} aria-label="Accesso">
        <div>
          <h1>Esposti ATS</h1>
          <div className="sottotitolo">Accedi al backoffice</div>
        </div>
        <div className="campo">
          <label htmlFor="utente">Nome utente</label>
          <input id="utente" type="text" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="campo">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <MessaggioErrore errore={entra.error} />
        <button className="btn" type="submit" disabled={entra.isPending}>{entra.isPending ? "Accesso in corso…" : "Accedi"}</button>
      </form>
    </div>
  );
}
