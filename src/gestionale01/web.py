from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from dataclasses import dataclass

from flask import Flask, redirect, render_template, request, url_for

from .models import Vehicle
from .storage import VehicleStorage


def create_app(db_path: Path) -> Flask:
    app = Flask(__name__)
    storage = VehicleStorage(db_path)

    @app.get("/")
    def index() -> str:
        vehicles = storage.load()
        vehicles.sort(key=lambda vehicle: vehicle.vehicle_id)
        return render_template("index.html", vehicles=vehicles)

    @app.get("/add")
    def add_form() -> str:
        return render_template("form.html", vehicle=None, error=None)

    @app.post("/add")
    def add_vehicle():
        vehicle, error = _vehicle_from_form(request.form)
        if error:
            return render_template("form.html", vehicle=vehicle, error=error), 400
        try:
            storage.add(vehicle)
        except ValueError as exc:
            return render_template("form.html", vehicle=vehicle, error=str(exc)), 400
        return redirect(url_for("index"))

    @app.get("/edit/<vehicle_id>")
    def edit_form(vehicle_id: str) -> str:
        vehicle = _find_vehicle(storage, vehicle_id)
        if vehicle is None:
            return render_template("form.html", vehicle=None, error="Veicolo non trovato."), 404
        return render_template("form.html", vehicle=vehicle, error=None)

    @app.post("/edit/<vehicle_id>")
    def edit_vehicle(vehicle_id: str):
        existing = _find_vehicle(storage, vehicle_id)
        if existing is None:
            return render_template("form.html", vehicle=None, error="Veicolo non trovato."), 404
        updated, error = _vehicle_from_form(request.form, vehicle_id=vehicle_id)
        if error:
            return render_template("form.html", vehicle=updated, error=error), 400
        storage.update(
            vehicle_id,
            targa=updated.targa,
            modello=updated.modello,
            anno=updated.anno,
            chilometraggio=updated.chilometraggio,
            stato=updated.stato,
            note=updated.note,
        )
        return redirect(url_for("index"))

    @app.post("/delete/<vehicle_id>")
    def delete_vehicle(vehicle_id: str):
        try:
            storage.remove(vehicle_id)
        except ValueError:
            pass
        return redirect(url_for("index"))

    return app


def _find_vehicle(storage: VehicleStorage, vehicle_id: str) -> Vehicle | None:
    for vehicle in storage.load():
        if vehicle.vehicle_id == vehicle_id:
            return vehicle
    return None


@dataclass
class VehicleDraft:
    vehicle_id: str
    targa: str
    modello: str
    anno: str
    chilometraggio: str
    stato: str
    note: str
    aggiornato_il: str


def _vehicle_from_form(
    form, vehicle_id: str | None = None
) -> tuple[Vehicle | VehicleDraft, str | None]:
    payload = {
        "vehicle_id": vehicle_id or form.get("vehicle_id", "").strip(),
        "targa": form.get("targa", "").strip(),
        "modello": form.get("modello", "").strip(),
        "anno": form.get("anno", "").strip(),
        "chilometraggio": form.get("chilometraggio", "").strip(),
        "stato": form.get("stato", "disponibile").strip() or "disponibile",
        "note": form.get("note", "").strip(),
        "aggiornato_il": date.today().isoformat(),
    }
    missing = [key for key in ("vehicle_id", "targa", "modello", "anno", "chilometraggio") if not payload[key]]
    if missing:
        return VehicleDraft(**payload), "Completa tutti i campi obbligatori."
    try:
        anno = int(payload["anno"])
        chilometraggio = int(payload["chilometraggio"])
    except ValueError:
        return VehicleDraft(**payload), "Anno e chilometraggio devono essere numeri."
    payload["anno"] = anno
    payload["chilometraggio"] = chilometraggio
    return Vehicle.from_dict(payload), None


def main() -> None:
    parser = argparse.ArgumentParser(description="UI web per il gestionale parco auto")
    parser.add_argument("--db", default="data/vehicles.json", help="Percorso database JSON")
    parser.add_argument("--host", default="127.0.0.1", help="Host di ascolto")
    parser.add_argument("--port", type=int, default=8000, help="Porta di ascolto")
    args = parser.parse_args()

    app = create_app(Path(args.db))
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
