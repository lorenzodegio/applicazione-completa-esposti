import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { ETICHETTA_RUOLO } from "../formati";
import { useSessione } from "../sessione";

const VOCI: Record<string, string> = {
  Home: "/", Inbox: "/inbox", Fascicoli: "/fascicoli", "Gestione pratiche": "/pratiche",
  Smistamento: "/smistamento", Uffici: "/uffici", Utenti: "/utenti",
};

export function Layout() {
  const { me } = useSessione();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const conPratiche = me?.utente.ruolo !== "amministratore";
  const home = useQuery({ queryKey: ["home"], queryFn: api.home, enabled: !!me && conPratiche });
  const esci = useMutation({
    mutationFn: api.logout,
    onSettled: () => { qc.clear(); qc.setQueryData(["me"], null); navigate("/accedi"); },
  });
  if (!me) return null;
  const { utente, menu } = me;
  const daValidare = home.data?.contatori["da_validare"];
  return (
    <div className="app">
      <nav className="menu" aria-label="Menu principale">
        <div className="marchio">Esposti ATS</div>
        <div className="ufficio">{utente.ufficio?.nome ?? ETICHETTA_RUOLO[utente.ruolo]}</div>
        {menu.map((voce) => (
          <NavLink key={voce} to={VOCI[voce] ?? "/"} end={voce === "Home"}>
            <span>{voce}</span>
            {voce === "Inbox" && daValidare ? <span className="pallino" aria-label={`${daValidare} da validare`}>{daValidare}</span> : null}
          </NavLink>
        ))}
        <div className="utente">
          {utente.nome_visualizzato}<br />{ETICHETTA_RUOLO[utente.ruolo]}
          <div><button type="button" onClick={() => esci.mutate()}>Esci</button></div>
        </div>
      </nav>
      <main className="principale"><Outlet /></main>
    </div>
  );
}
