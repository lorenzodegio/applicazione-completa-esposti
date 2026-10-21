import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { api } from "./api/endpoints";
import { ApiError, EVENTO_NON_AUTORIZZATO } from "./api/client";
import type { Me, Ruolo } from "./api/tipi";
import { Caricamento } from "./componenti/ui";

export function useSessione() {
  const qc = useQueryClient();
  const q = useQuery<Me | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.me();
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 60_000,
  });
  useEffect(() => {
    const scaduta = () => qc.setQueryData(["me"], null);
    window.addEventListener(EVENTO_NON_AUTORIZZATO, scaduta);
    return () => window.removeEventListener(EVENTO_NON_AUTORIZZATO, scaduta);
  }, [qc]);
  return { me: q.data ?? null, caricamento: q.isLoading, errore: q.error };
}

/** Pagina iniziale di ciascun ruolo: l'amministratore non vede le pratiche. */
export const paginaIniziale = (r: Ruolo) => (r === "amministratore" ? "/uffici" : "/");

export function Protetta({ ruoli }: { ruoli?: Ruolo[] }) {
  const { me, caricamento } = useSessione();
  if (caricamento) return <Caricamento />;
  if (!me) return <Navigate to="/accedi" replace />;
  if (ruoli && !ruoli.includes(me.utente.ruolo)) return <Navigate to={paginaIniziale(me.utente.ruolo)} replace />;
  return <Outlet />;
}
