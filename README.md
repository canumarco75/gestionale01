# Gestionale01

Progetto di gestione di un parco automezzi tramite una semplice CLI in Python.

## Requisiti

- Python 3.11+ (solo libreria standard).

## Installazione locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Avvio rapido

```bash
python -m gestionale01 list
```

## Comandi disponibili

### Aggiungere un veicolo

```bash
python -m gestionale01 add V001 AB123CD "Fiat Panda" 2021 35500 --stato disponibile --note "City car"
```

### Elencare veicoli

```bash
python -m gestionale01 list
python -m gestionale01 list --stato disponibile
```

### Aggiornare un veicolo

```bash
python -m gestionale01 update V001 --chilometraggio 36000 --stato in_manutenzione
```

### Rimuovere un veicolo

```bash
python -m gestionale01 remove V001
```

## Dati

I dati vengono salvati in `data/vehicles.json`. Puoi cambiare il percorso con `--db`.

```bash
python -m gestionale01 list --db /percorso/personalizzato/vehicles.json
```
