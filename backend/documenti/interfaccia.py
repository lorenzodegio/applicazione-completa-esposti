import uuid
from dataclasses import dataclass
from typing import BinaryIO, Protocol


class ErroreArchivio(Exception):
    pass


@dataclass(frozen=True)
class RiferimentoArchivio:
    archivio: str       # "locale" | "sharepoint"
    id_archivio: str    # identificativo SharePoint, o chiave relativa nell'archivio locale
    sha256: str         # impronta del contenuto
    dimensione: int


class ArchivioDocumenti(Protocol):
    """Il resto del backend usa solo questa interfaccia, mai l'implementazione."""

    def salva(self, pratica_id: uuid.UUID, nome_file: str, contenuto: BinaryIO,
              id_documento: uuid.UUID | None = None) -> RiferimentoArchivio: ...

    def salva_accanto(self, rif: RiferimentoArchivio, suffisso: str, contenuto: bytes) -> RiferimentoArchivio: ...

    def apri(self, rif_id: str) -> BinaryIO: ...

    def impronta(self, rif_id: str) -> str: ...

    def elimina(self, rif_id: str) -> None: ...

    def verifica(self) -> None:
        """Controllo di salute: solleva ErroreArchivio se l'archivio non è raggiungibile o scrivibile."""
        ...
