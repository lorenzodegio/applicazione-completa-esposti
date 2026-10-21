from functools import lru_cache

from documenti import ArchivioCartellaLocale, ArchivioDocumenti

from .config import get_settings


@lru_cache
def get_archivio() -> ArchivioDocumenti:
    # Quando ci sarà SharePoint, si cambia solo questa funzione.
    return ArchivioCartellaLocale(get_settings().archivio_radice)
