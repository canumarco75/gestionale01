from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Iterable, Protocol

from werkzeug.security import check_password_hash, generate_password_hash

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


class StorageProtocol(Protocol):
    def load(self) -> list[Vehicle]:
        ...

    def add(self, vehicle: Vehicle) -> None:
        ...

    def update(self, vehicle_id: str, **changes: str | int) -> Vehicle:
        ...

    def remove(self, vehicle_id: str) -> None:
        ...


def _connect_mysql(url: str, database: str | None = None):
    import mysql.connector
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme != "mysql":
        raise ValueError("URL MySQL non valido. Usa il formato mysql://utente:password@host:porta/database")
    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        if database:
            db_name = database
        else:
            raise ValueError("Specifica il database nell'URL MySQL o usa --mysql-db.")
    return mysql.connector.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        database=db_name,
    )


class MySQLVehicleStorage:
    def __init__(self, url: str, database: str | None = None) -> None:
        self.url = url
        self.database = database

    def load(self) -> list[Vehicle]:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT vehicle_id, targa, modello, anno, chilometraggio, stato, note, aggiornato_il FROM vehicles"
            )
            rows = cursor.fetchall()
        vehicles: list[Vehicle] = []
        for row in rows:
            if row["aggiornato_il"] is not None:
                row["aggiornato_il"] = row["aggiornato_il"].isoformat()
            vehicles.append(Vehicle.from_dict(row))
        return vehicles

    def add(self, vehicle: Vehicle) -> None:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_id = %s", (vehicle.vehicle_id,))
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"Esiste già un veicolo con ID {vehicle.vehicle_id}.")
            cursor.execute(
                """
                INSERT INTO vehicles
                (vehicle_id, targa, modello, anno, chilometraggio, stato, note, aggiornato_il)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vehicle.vehicle_id,
                    vehicle.targa,
                    vehicle.modello,
                    vehicle.anno,
                    vehicle.chilometraggio,
                    vehicle.stato,
                    vehicle.note,
                    vehicle.aggiornato_il,
                ),
            )
            conn.commit()

    def update(self, vehicle_id: str, **changes: str | int) -> Vehicle:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT vehicle_id, targa, modello, anno, chilometraggio, stato, note, aggiornato_il "
                "FROM vehicles WHERE vehicle_id = %s",
                (vehicle_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Nessun veicolo trovato con ID {vehicle_id}.")
            for key, value in changes.items():
                row[key] = value
            row["aggiornato_il"] = date.today().isoformat()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE vehicles
                SET targa = %s,
                    modello = %s,
                    anno = %s,
                    chilometraggio = %s,
                    stato = %s,
                    note = %s,
                    aggiornato_il = %s
                WHERE vehicle_id = %s
                """,
                (
                    row["targa"],
                    row["modello"],
                    row["anno"],
                    row["chilometraggio"],
                    row["stato"],
                    row["note"],
                    row["aggiornato_il"],
                    vehicle_id,
                ),
            )
            conn.commit()
            return Vehicle.from_dict(row)

    def remove(self, vehicle_id: str) -> None:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vehicles WHERE vehicle_id = %s", (vehicle_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Nessun veicolo trovato con ID {vehicle_id}.")
            conn.commit()

    def _connect(self):
        return _connect_mysql(self.url, self.database)

    def _ensure_table(self, conn) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id VARCHAR(50) PRIMARY KEY,
                targa VARCHAR(20) NOT NULL,
                modello VARCHAR(120) NOT NULL,
                anno INT NOT NULL,
                chilometraggio INT NOT NULL,
                stato VARCHAR(40) NOT NULL,
                note TEXT NOT NULL,
                aggiornato_il DATE NOT NULL
            )
            """
        )
        conn.commit()


def get_storage(
    db_type: str,
    db_path: Path,
    mysql_url: str | None,
    mysql_db: str | None = None,
) -> StorageProtocol:
    normalized = db_type.lower()
    if normalized == "json":
        return VehicleStorage(db_path)
    if normalized == "mysql":
        if not mysql_url:
            raise ValueError("Per db_type=mysql devi passare --mysql-url.")
        return MySQLVehicleStorage(mysql_url, mysql_db)
    raise ValueError("Tipo database non supportato. Usa json o mysql.")


class UserStorageProtocol(Protocol):
    def verify_user(self, username: str, password: str) -> bool:
        ...

    def create_user(self, username: str, password: str) -> None:
        ...


class MySQLUserStorage:
    def __init__(self, url: str, database: str | None = None) -> None:
        self.url = url
        self.database = database

    def verify_user(self, username: str, password: str) -> bool:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
        if row is None:
            return False
        return check_password_hash(row["password_hash"], password)

    def create_user(self, username: str, password: str) -> None:
        with self._connect() as conn:
            self._ensure_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"Esiste già un utente con username {username}.")
            password_hash = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, creato_il)
                VALUES (%s, %s, %s)
                """,
                (username, password_hash, date.today().isoformat()),
            )
            conn.commit()

    def _connect(self):
        return _connect_mysql(self.url, self.database)

    def _ensure_table(self, conn) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(80) PRIMARY KEY,
                password_hash VARCHAR(255) NOT NULL,
                creato_il DATE NOT NULL
            )
            """
        )
        conn.commit()
