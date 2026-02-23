from datetime import datetime
from tinydb import Query
from database import DatabaseConnector
import os

_checkpoint_tabelle = DatabaseConnector().get_table("checkpoits")

Q = Query()

# checkpoint eintrag im tinydb anlegen
def checkpoint_eintrag_anlegen(pfad: str, name: str = "Checkpoint", parameter: dict | None = None, info: dict | None = None):
    doc = {
        "name": name,
        "pfad": pfad,
        "zeitpunkt": datetime.now(),
        "parameter": parameter or {},
        "info": info or {}
    }

    doc_id = _checkpoint_tabelle.insert(doc)
    return doc_id

def checkpoints_auflisten():
    alle = _checkpoint_tabelle.all()
    return sorted(alle, key=lambda d: d.get("zeitpunkt"), reverse=True)

def checkpoint_holen(doc_id: int):
    return _checkpoint_tabelle.get(doc_id=doc_id)

# db eintrag und zugehöhrige pickle datei löschen
def checkpoint_loeschen(doc_id: int):

    eintrag = _checkpoint_tabelle.get(doc_id=doc_id)
    if not eintrag:
        return False, "Checkpoint nicht gefunden"
    
    pfad = eintrag.get("pfad")

    # in der db löschen
    _checkpoint_tabelle.remove(doc_ids=[doc_id])

    # pickle datei löschen
    if pfad and os.path.exists(pfad):
        try:
            os.remove(pfad)
            return True, "Checkpoint wurde gelöscht!!"
        except Exception as e:
            return True, f"Aus Datenbank gelöscht, Pickle Datei nicht: {e}"
    return True, "Datenbank Eintrag gelöscht"
