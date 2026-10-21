import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import { RigaPratica } from "../componenti/RigaPratica";
import { Caricamento, Intestazione, MessaggioErrore, Vuoto } from "../componenti/ui";
import { useSessione } from "../sessione";

const CONTATORI: { chiave: string; titolo: string; nota: string; solo?: "smistatore" }[] = [
  { chiave: "da_smistare", titolo: "Da smistare", nota: "in attesa di un ufficio", solo: "smistatore" },
  { chiave: "da_validare", titolo: "Da validare", nota: "in attesa nella inbox" },
  { chiave: "in_lavorazione", titolo: "In lavorazione", nota: "pratiche aperte" },
  { chiave: "lettura_incerta", titolo: "Lettura incerta", nota: "da leggere sull'originale" },
  { chiave: "senza_riscontro", titolo: "Senza riscontro", nota: "esposti accolti ancora senza risposta" },
];

const oggi = () => new Intl.DateTimeFormat("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());

export function Home() {
  const { me } = useSessione();
  const q = useQuery({ queryKey: ["home"], queryFn: api.home });
  const ruolo = me?.utente.ruolo;
  return (
    <>
      <Intestazione
        titolo="Home" sotto={oggi()}
        azioni={<Link className="btn" to="/inbox">Apri la inbox</Link>}
      />
      <MessaggioErrore errore={q.error} />
      {q.isLoading && <Caricamento />}
      {q.data && (
        <>
          <div className="griglia-contatori">
            {CONTATORI.filter((c) => !c.solo || c.solo === ruolo).map((c) => (
              <div className="card contatore" key={c.chiave}>
                <div className="etichetta">{c.titolo}</div>
                <div className="numero">{q.data.contatori[c.chiave] ?? 0}</div>
                <div className="nota">{c.nota}</div>
              </div>
            ))}
          </div>
          <div className="colonne">
            <section className="card larga" aria-labelledby="h-arrivi">
              <div className="riga spazio">
                <h2 id="h-arrivi">Arrivati per la validazione</h2>
                <Link to="/inbox">Vedi tutti</Link>
              </div>
              {q.data.ultimi_arrivi.length === 0 && <Vuoto>Nessun esposto in attesa di validazione.</Vuoto>}
              <div className="elenco-voci">
                {q.data.ultimi_arrivi.map((p) => <RigaPratica key={p.id} p={p} a={`/inbox/${p.id}`} />)}
              </div>
            </section>
            <div className="stretta">
              <section className="card" aria-labelledby="h-fasc">
                <h2 id="h-fasc">Fascicoli più attivi</h2>
                <div className="elenco-voci">
                  {q.data.fascicoli_piu_attivi.map((f) => (
                    <Link key={f.codice} className="voce" to={`/fascicoli/${f.codice}`}>
                      <span className="corpo"><span className="titolo">{f.nome}</span></span>
                      <span className="meta">{f.pratiche} {f.pratiche === 1 ? "pratica" : "pratiche"}</span>
                    </Link>
                  ))}
                </div>
              </section>
              {q.data.disaccordo.totale > 0 && (
                <section className="avviso" aria-labelledby="h-dis">
                  <h2 id="h-dis" style={{ color: "inherit" }}>IA e operatore in disaccordo</h2>
                  <p>
                    {q.data.disaccordo.totale} {q.data.disaccordo.totale === 1 ? "pratica in cui" : "pratiche in cui"} la
                    valutazione dell'operatore è diversa dalla proposta dell'IA.
                  </p>
                  <Link to="/pratiche?disaccordo=1" style={{ color: "inherit", fontWeight: 700 }}>Vedi le pratiche in Gestione pratiche</Link>
                </section>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
