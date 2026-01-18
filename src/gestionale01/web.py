from __future__ import annotations

import argparse
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for

from .models import Vehicle
from .storage import StorageProtocol, get_storage


@dataclass(frozen=True)
class AuthConfig:
    username: str | None = None
    password: str | None = None
    secret_key: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.username and self.password)


def create_app(storage: StorageProtocol, auth: AuthConfig) -> Flask:
    app = Flask(__name__)
    if auth.secret_key:
        app.secret_key = auth.secret_key
    else:
        app.secret_key = os.environ.get("GESTIONALE01_SECRET_KEY", secrets.token_hex(16))

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not auth.enabled:
                return view(*args, **kwargs)
            if session.get("logged_in"):
                return view(*args, **kwargs)
            return redirect(url_for("login", next=request.path))

        return wrapped

    @app.context_processor
    def inject_auth():
        return {
            "auth_enabled": auth.enabled,
            "is_authenticated": auth.enabled and session.get("logged_in", False),
        }

    @app.get("/login")
    def login() -> str:
        if not auth.enabled:
            return redirect(url_for("index"))
        return render_template("login.html", error=None, next_url=request.args.get("next", ""))

    @app.post("/login")
    def login_submit():
        if not auth.enabled:
            return redirect(url_for("index"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if hmac.compare_digest(username, auth.username or "") and hmac.compare_digest(password, auth.password or ""):
            session["logged_in"] = True
            next_url = request.form.get("next") or url_for("index")
            return redirect(next_url)
        return render_template(
            "login.html",
            error="Credenziali non valide.",
            next_url=request.form.get("next", ""),
        ), 401

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def index() -> str:
        vehicles = storage.load()
        vehicles.sort(key=lambda vehicle: vehicle.vehicle_id)
        return render_template("index.html", vehicles=vehicles)

    @app.get("/add")
    @login_required
    def add_form() -> str:
        return render_template("form.html", vehicle=None, error=None)

    @app.post("/add")
    @login_required
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
    @login_required
    def edit_form(vehicle_id: str) -> str:
        vehicle = _find_vehicle(storage, vehicle_id)
        if vehicle is None:
            return render_template("form.html", vehicle=None, error="Veicolo non trovato."), 404
        return render_template("form.html", vehicle=vehicle, error=None)

    @app.post("/edit/<vehicle_id>")
    @login_required
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
    @login_required
    def delete_vehicle(vehicle_id: str):
        try:
            storage.remove(vehicle_id)
        except ValueError:
            pass
        return redirect(url_for("index"))

    return app


def _find_vehicle(storage: StorageProtocol, vehicle_id: str) -> Vehicle | None:
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
    parser.add_argument(
        "--db-type",
        choices=["json", "mysql"],
        default="json",
        help="Tipo di database da usare (json o mysql)",
    )
    parser.add_argument("--mysql-url", help="URL di connessione MySQL (es. mysql://user:pass@host:3306/db)")
    parser.add_argument("--ui-user", help="Username per accedere alla UI web (opzionale)")
    parser.add_argument("--ui-password", help="Password per accedere alla UI web (opzionale)")
    parser.add_argument(
        "--secret-key",
        help="Chiave segreta Flask per sessioni (opzionale, consigliata se abiliti il login)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host di ascolto")
    parser.add_argument("--port", type=int, default=8000, help="Porta di ascolto")
    args = parser.parse_args()

    if bool(args.ui_user) ^ bool(args.ui_password):
        parser.error("Specifica sia --ui-user che --ui-password per abilitare il login.")

    storage = get_storage(args.db_type, Path(args.db), args.mysql_url)
    auth = AuthConfig(username=args.ui_user, password=args.ui_password, secret_key=args.secret_key)
    app = create_app(storage, auth)
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
