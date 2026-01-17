from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Vehicle:
    vehicle_id: str
    targa: str
    modello: str
    anno: int
    chilometraggio: int
    stato: str = "disponibile"
    note: str = ""
    aggiornato_il: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "targa": self.targa,
            "modello": self.modello,
            "anno": self.anno,
            "chilometraggio": self.chilometraggio,
            "stato": self.stato,
            "note": self.note,
            "aggiornato_il": self.aggiornato_il,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Vehicle":
        return cls(
            vehicle_id=payload["vehicle_id"],
            targa=payload["targa"],
            modello=payload["modello"],
            anno=int(payload["anno"]),
            chilometraggio=int(payload["chilometraggio"]),
            stato=payload.get("stato", "disponibile"),
            note=payload.get("note", ""),
            aggiornato_il=payload.get("aggiornato_il", date.today().isoformat()),
        )
