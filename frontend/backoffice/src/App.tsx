import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./componenti/Layout";
import { Accesso } from "./pagine/Accesso";
import { Protetta, useSessione, paginaIniziale } from "./sessione";
import { Home } from "./pagine/Home";
import { Inbox } from "./pagine/Inbox";
import { GestionePratiche } from "./pagine/GestionePratiche";
import { SchedaPratica } from "./pagine/SchedaPratica";
import { Fascicoli } from "./pagine/Fascicoli";
import { Smistamento } from "./pagine/Smistamento";
import { Uffici } from "./pagine/Uffici";
import { Utenti } from "./pagine/Utenti";

function Radice() {
  const { me } = useSessione();
  return me?.utente.ruolo === "amministratore" ? <Navigate to={paginaIniziale("amministratore")} replace /> : <Home />;
}

export function App() {
  return (
    <Routes>
      <Route path="/accedi" element={<Accesso />} />
      <Route element={<Protetta />}>
        <Route element={<Layout />}>
          <Route index element={<Radice />} />
          <Route element={<Protetta ruoli={["smistatore", "operatore"]} />}>
            <Route path="inbox/:id?" element={<Inbox />} />
            <Route path="pratiche" element={<GestionePratiche />} />
            <Route path="pratiche/:id" element={<SchedaPratica />} />
            <Route path="fascicoli/:codice?" element={<Fascicoli />} />
          </Route>
          <Route element={<Protetta ruoli={["smistatore"]} />}>
            <Route path="smistamento" element={<Smistamento />} />
          </Route>
          <Route element={<Protetta ruoli={["amministratore"]} />}>
            <Route path="uffici" element={<Uffici />} />
            <Route path="utenti" element={<Utenti />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
