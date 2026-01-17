from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import Vehicle


class VehicleStorage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[Vehicle]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [Vehicle.from_dict(item) for item in payload]

    def save(self, vehicles: Iterable[Vehicle]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(vehicle) for vehicle in vehicles], handle, indent=2, ensure_ascii=False)

    def add(self, vehicle: Vehicle) -> None:
        vehicles = self.load()
        if any(v.vehicle_id == vehicle.vehicle_id for v in vehicles):
            raise ValueError(f"Esiste già un veicolo con ID {vehicle.vehicle_id}.")
        vehicles.append(vehicle)
        self.save(vehicles)

    def update(self, vehicle_id: str, **changes: str | int) -> Vehicle:
        vehicles = self.load()
        for vehicle in vehicles:
            if vehicle.vehicle_id == vehicle_id:
                for key, value in changes.items():
                    setattr(vehicle, key, value)
                vehicle.aggiornato_il = date.today().isoformat()
                self.save(vehicles)
                return vehicle
        raise ValueError(f"Nessun veicolo trovato con ID {vehicle_id}.")

    def remove(self, vehicle_id: str) -> None:
        vehicles = self.load()
        filtered = [vehicle for vehicle in vehicles if vehicle.vehicle_id != vehicle_id]
        if len(filtered) == len(vehicles):
            raise ValueError(f"Nessun veicolo trovato con ID {vehicle_id}.")
        self.save(filtered)
