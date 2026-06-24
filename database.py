"""
Datenbankschema und Verbindungsmanagement für das Personalplanungssystem.
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "personalplanung.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Erstellt alle Tabellen, falls nicht vorhanden."""
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS dienststelle (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            typ         TEXT NOT NULL CHECK(typ IN ('Gericht','Staatsanwaltschaft')),
            region      TEXT NOT NULL,
            pebby_bedarf REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS person (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL,
            status              TEXT NOT NULL CHECK(status IN ('Richter','Staatsanwalt')),
            laufbahnstatus      TEXT NOT NULL CHECK(laufbahnstatus IN ('Assessor','Proberichter','Lebenszeit')),
            aka_faktor          REAL NOT NULL DEFAULT 1.0,
            einstellungsdatum   TEXT NOT NULL,
            ruhestandsdatum     TEXT,
            aktuelle_dienststelle INTEGER REFERENCES dienststelle(id)
        );

        CREATE TABLE IF NOT EXISTS planstelle (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            dienststelle_id INTEGER NOT NULL REFERENCES dienststelle(id),
            bezeichnung     TEXT NOT NULL,
            besetzt         INTEGER NOT NULL DEFAULT 1 CHECK(besetzt IN (0,1))
        );

        CREATE TABLE IF NOT EXISTS ereignis (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id           INTEGER NOT NULL REFERENCES person(id),
            datum               TEXT NOT NULL,
            typ                 TEXT NOT NULL CHECK(typ IN (
                                    'Neueinstellung','Wechsel','Abordnung',
                                    'Elternzeit','Rückkehr','Ruhestand')),
            quelle_dienststelle INTEGER REFERENCES dienststelle(id),
            ziel_dienststelle   INTEGER REFERENCES dienststelle(id),
            bemerkung           TEXT
        );

        CREATE TABLE IF NOT EXISTS wunsch (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id           INTEGER NOT NULL REFERENCES person(id),
            wunsch_region       TEXT,
            wunsch_dienststelle INTEGER REFERENCES dienststelle(id),
            prioritaet          INTEGER NOT NULL DEFAULT 1 CHECK(prioritaet BETWEEN 1 AND 3),
            bemerkung           TEXT
        );
        """)
    print(f"Datenbank initialisiert: {DB_PATH}")


def db_exists_with_data() -> bool:
    if not DB_PATH.exists():
        return False
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM person").fetchone()
        return row["cnt"] > 0
