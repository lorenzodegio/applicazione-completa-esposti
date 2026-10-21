import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/endpoints";
import type { Pratica } from "../api/tipi";
import { Dialogo, MessaggioErrore } from "./ui";

/** Assegnazione (da DA_SMISTARE) o riassegnazione (da DA_VALIDARE, con motivo obbligatorio). */
export function AssegnaUfficio({ pratica, onChiudi }: { pratica: Pick<Pratica, "id" | "versione" | "stato" | "ufficio">; onChiudi: () => void }) {
  const qc = useQueryClient();
  const uffici = useQuery({ queryKey: ["uffici"], queryFn: api.uffici });
  const [ufficio, setUfficio] = useState("");
  const [motivo, setMotivo] = useState("");
  const riassegna = pratica.stato === "DA_VALIDARE";
  const assegna = useMutation({
    mutationFn: () => api.assegna(pratica.id, { versione: pratica.versione, ufficio_id: ufficio, motivo: motivo.trim() || null, da_proposta_ia: false }),
    onSuccess: async () => { await qc.invalidateQueries(); onChiudi(); },
  });
  const scelte = (uffici.data ?? []).filter((u) => u.attivo && u.id !== pratica.ufficio?.id);
  return (
    <Dialogo titolo={riassegna ? "Riassegna a un altro ufficio" : "Assegna a un ufficio"} onChiudi={onChiudi}>
      <form className="pila" onSubmit={(e) => { e.preventDefault(); if (ufficio && (!riassegna || motivo.trim())) assegna.mutate(); }}>
        <div className="campo">
          <label htmlFor="ufficio">Ufficio</label>
          <select id="ufficio" value={ufficio} onChange={(e) => setUfficio(e.target.value)}>
            <option value="">Scegli…</option>
            {scelte.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="motivo-ass">{riassegna ? "Motivo (obbligatorio)" : "Motivo (facoltativo)"}</label>
          <textarea id="motivo-ass" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </div>
        <MessaggioErrore errore={assegna.error} />
        <div className="riga">
          <button type="submit" className="btn" disabled={!ufficio || (riassegna && !motivo.trim()) || assegna.isPending}>{riassegna ? "Riassegna" : "Assegna"}</button>
          <button type="button" className="btn secondario" onClick={onChiudi}>Annulla</button>
        </div>
      </form>
    </Dialogo>
  );
}
