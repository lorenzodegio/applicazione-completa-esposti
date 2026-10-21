import hashlib
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from .interfaccia import ErroreArchivio, RiferimentoArchivio

_SUFFISSO = re.compile(r"^[a-z0-9]+(\.[a-z0-9]+)*$")


class ArchivioCartellaLocale:
    """Sviluppo e prima fase. La radice viene dalla configurazione, fuori dal repository."""

    def __init__(self, radice: str | Path):
        self.radice = Path(radice).expanduser().resolve()
        self.radice.mkdir(parents=True, exist_ok=True)

    def _percorso(self, chiave: str) -> Path:
        p = (self.radice / chiave).resolve()
        if self.radice not in p.parents:
            raise ErroreArchivio("Chiave fuori dall'archivio")
        return p

    @staticmethod
    def _estensione(nome_file: str) -> str:
        ext = Path(os.path.basename(nome_file.replace("\\", "/"))).suffix.lower()
        return ext if re.fullmatch(r"\.[a-z0-9]{1,8}", ext) else ""

    def _scrivi(self, chiave: str, contenuto: BinaryIO | bytes) -> RiferimentoArchivio:
        dest = self._percorso(chiave)
        dest.parent.mkdir(parents=True, exist_ok=True)
        h, n = hashlib.sha256(), 0
        tmp = dest.with_name(dest.name + ".parziale")
        try:
            with open(tmp, "xb") as f:
                if isinstance(contenuto, bytes):
                    contenuto = _Bytes(contenuto)
                while blocco := contenuto.read(1024 * 1024):
                    h.update(blocco); n += len(blocco); f.write(blocco)
            os.replace(tmp, dest)
        finally:
            tmp.unlink(missing_ok=True)
        return RiferimentoArchivio("locale", chiave, h.hexdigest(), n)

    def salva(self, pratica_id: uuid.UUID, nome_file: str, contenuto: BinaryIO,
              id_documento: uuid.UUID | None = None) -> RiferimentoArchivio:
        # Il nome originale non entra nel percorso: resta solo nel database.
        return self._scrivi(f"{pratica_id}/{id_documento or uuid.uuid4()}{self._estensione(nome_file)}", contenuto)

    def salva_accanto(self, rif: RiferimentoArchivio, suffisso: str, contenuto: bytes) -> RiferimentoArchivio:
        if not _SUFFISSO.match(suffisso):
            raise ErroreArchivio("Suffisso non valido")
        base = Path(rif.id_archivio)
        return self._scrivi(f"{base.parent}/{base.stem}.{suffisso}", contenuto)

    def apri(self, rif_id: str) -> BinaryIO:
        p = self._percorso(rif_id)
        if not p.is_file():
            raise ErroreArchivio("Documento non trovato in archivio")
        return open(p, "rb")

    def impronta(self, rif_id: str) -> str:
        h = hashlib.sha256()
        with self.apri(rif_id) as f:
            while blocco := f.read(1024 * 1024):
                h.update(blocco)
        return h.hexdigest()

    def elimina(self, rif_id: str) -> None:  # solo per i test e le migrazioni verificate
        self._percorso(rif_id).unlink(missing_ok=True)


class _Bytes:
    def __init__(self, dati: bytes):
        self._dati, self._pos = dati, 0

    def read(self, n: int) -> bytes:
        blocco = self._dati[self._pos:self._pos + n]
        self._pos += len(blocco)
        return blocco
