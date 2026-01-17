from __future__ import annotations

import argparse
from pathlib import Path

from .models import Vehicle
from .storage import VehicleStorage

DEFAULT_DB = Path("data/vehicles.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestione parco automezzi")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Percorso del file dati JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Aggiungi un nuovo veicolo")
    add_parser.add_argument("vehicle_id", help="ID univoco del veicolo")
    add_parser.add_argument("targa", help="Targa del veicolo")
    add_parser.add_argument("modello", help="Modello del veicolo")
    add_parser.add_argument("anno", type=int, help="Anno di immatricolazione")
    add_parser.add_argument("chilometraggio", type=int, help="Chilometraggio attuale")
    add_parser.add_argument("--stato", default="disponibile", help="Stato (disponibile, in_manutenzione, assegnato)")
    add_parser.add_argument("--note", default="", help="Note aggiuntive")

    list_parser = subparsers.add_parser("list", help="Elenca tutti i veicoli")
    list_parser.add_argument("--stato", help="Filtra per stato")

    update_parser = subparsers.add_parser("update", help="Aggiorna un veicolo")
    update_parser.add_argument("vehicle_id", help="ID del veicolo")
    update_parser.add_argument("--targa")
    update_parser.add_argument("--modello")
    update_parser.add_argument("--anno", type=int)
    update_parser.add_argument("--chilometraggio", type=int)
    update_parser.add_argument("--stato")
    update_parser.add_argument("--note")

    remove_parser = subparsers.add_parser("remove", help="Rimuovi un veicolo")
    remove_parser.add_argument("vehicle_id", help="ID del veicolo")

    return parser


def handle_add(args: argparse.Namespace, storage: VehicleStorage) -> None:
    vehicle = Vehicle(
        vehicle_id=args.vehicle_id,
        targa=args.targa,
        modello=args.modello,
        anno=args.anno,
        chilometraggio=args.chilometraggio,
        stato=args.stato,
        note=args.note,
    )
    storage.add(vehicle)
    print(f"Veicolo {args.vehicle_id} aggiunto con successo.")


def handle_list(args: argparse.Namespace, storage: VehicleStorage) -> None:
    vehicles = storage.load()
    if args.stato:
        vehicles = [vehicle for vehicle in vehicles if vehicle.stato == args.stato]

    if not vehicles:
        print("Nessun veicolo trovato.")
        return

    for vehicle in vehicles:
        print(
            " | ".join(
                [
                    vehicle.vehicle_id,
                    vehicle.targa,
                    vehicle.modello,
                    str(vehicle.anno),
                    str(vehicle.chilometraggio),
                    vehicle.stato,
                    vehicle.aggiornato_il,
                ]
            )
        )


def handle_update(args: argparse.Namespace, storage: VehicleStorage) -> None:
    changes = {
        key: value
        for key, value in {
            "targa": args.targa,
            "modello": args.modello,
            "anno": args.anno,
            "chilometraggio": args.chilometraggio,
            "stato": args.stato,
            "note": args.note,
        }.items()
        if value is not None
    }
    if not changes:
        raise SystemExit("Specifica almeno un campo da aggiornare.")
    storage.update(args.vehicle_id, **changes)
    print(f"Veicolo {args.vehicle_id} aggiornato.")


def handle_remove(args: argparse.Namespace, storage: VehicleStorage) -> None:
    storage.remove(args.vehicle_id)
    print(f"Veicolo {args.vehicle_id} rimosso.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    storage = VehicleStorage(args.db)

    if args.command == "add":
        handle_add(args, storage)
    elif args.command == "list":
        handle_list(args, storage)
    elif args.command == "update":
        handle_update(args, storage)
    elif args.command == "remove":
        handle_remove(args, storage)
    else:
        raise SystemExit("Comando non riconosciuto.")


if __name__ == "__main__":
    main()
