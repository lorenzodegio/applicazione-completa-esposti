"""Interfaccia unica per l'archivio dei documenti (piano, sezione 4)."""
from .interfaccia import ArchivioDocumenti, ErroreArchivio, RiferimentoArchivio
from .locale import ArchivioCartellaLocale

__all__ = ["ArchivioDocumenti", "ArchivioCartellaLocale", "ErroreArchivio", "RiferimentoArchivio"]
