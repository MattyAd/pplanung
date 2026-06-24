"""
Fachlogik: Stichtagsberechnung, Wunsch-Matching, Dashboard-Aggregationen.
"""
from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from typing import Optional
from database import get_connection


# ─────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────

def heute() -> str:
    return date.today().isoformat()


def stichtag_str(d: date) -> str:
    return d.isoformat()


# ─────────────────────────────────────────────
# Stichtagsberechnung
# ─────────────────────────────────────────────

def berechne_besetzung_zum_stichtag(stichtag: date) -> list[dict]:
    """
    Berechnet für jede Dienststelle die Besetzung zum angegebenen Stichtag.
    Berücksichtigt alle Ereignisse bis einschließlich Stichtag.

    Fachlogik:
    - Ruhestand: Person scheidet aus → Planstelle wird frei
    - Elternzeit: Person ist abwesend, aber Planstelle bleibt besetzt (kein Nachbesetzungsanspruch)
    - Wechsel/Abordnung: Person wechselt die Dienststelle
    - Rückkehr: Person kehrt von Abordnung/Elternzeit zurück
    """
    stichtag_s = stichtag_str(stichtag)

    with get_connection() as conn:
        # Aktuelle Stammdaten aller Personen
        personen = {
            row["id"]: {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "laufbahnstatus": row["laufbahnstatus"],
                "aka_faktor": row["aka_faktor"],
                "dienststelle": row["aktuelle_dienststelle"],
                "aktiv": True,
                "in_elternzeit": False,
            }
            for row in conn.execute("SELECT * FROM person").fetchall()
        }

        # Alle Ereignisse bis zum Stichtag, chronologisch
        ereignisse = conn.execute("""
            SELECT e.*, p.name as person_name
            FROM ereignis e
            JOIN person p ON e.person_id = p.id
            WHERE e.datum <= ?
            ORDER BY e.datum ASC, e.id ASC
        """, (stichtag_s,)).fetchall()

        for e in ereignisse:
            pid = e["person_id"]
            if pid not in personen:
                continue
            p = personen[pid]
            typ = e["typ"]

            if typ == "Neueinstellung":
                p["dienststelle"] = e["ziel_dienststelle"]
                p["aktiv"] = True

            elif typ in ("Wechsel", "Abordnung"):
                p["dienststelle"] = e["ziel_dienststelle"]

            elif typ == "Elternzeit":
                p["in_elternzeit"] = True

            elif typ == "Rückkehr":
                p["in_elternzeit"] = False
                if e["ziel_dienststelle"]:
                    p["dienststelle"] = e["ziel_dienststelle"]

            elif typ == "Ruhestand":
                p["aktiv"] = False

        # Dienststellen aggregieren
        dienststellen = {
            row["id"]: {
                "id": row["id"],
                "name": row["name"],
                "typ": row["typ"],
                "region": row["region"],
                "pebby_bedarf": row["pebby_bedarf"],
                "personen": [],
                "aka_summe": 0.0,
            }
            for row in conn.execute("SELECT * FROM dienststelle").fetchall()
        }

        for p in personen.values():
            if not p["aktiv"]:
                continue
            ds_id = p["dienststelle"]
            if ds_id and ds_id in dienststellen:
                dienststellen[ds_id]["personen"].append(p)
                # Elternzeit: halber AKA-Beitrag (bleibt formal besetzt)
                faktor = p["aka_faktor"] * (0.5 if p["in_elternzeit"] else 1.0)
                dienststellen[ds_id]["aka_summe"] += faktor

        result = []
        for ds in dienststellen.values():
            anzahl = len(ds["personen"])
            aka = round(ds["aka_summe"], 2)
            bedarf = ds["pebby_bedarf"]
            deckung = round(aka - bedarf, 2)
            result.append({
                **ds,
                "anzahl_personen": anzahl,
                "aka_summe": aka,
                "deckung": deckung,
            })

        return sorted(result, key=lambda x: x["name"])


def berechne_bewegungen(von: date, bis: date) -> list[dict]:
    """Gibt alle Personalereignisse in einem Zeitraum zurück."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT e.*, p.name as person_name, p.status,
                   ds_q.name as quelle_name, ds_z.name as ziel_name
            FROM ereignis e
            JOIN person p ON e.person_id = p.id
            LEFT JOIN dienststelle ds_q ON e.quelle_dienststelle = ds_q.id
            LEFT JOIN dienststelle ds_z ON e.ziel_dienststelle = ds_z.id
            WHERE e.datum BETWEEN ? AND ?
            ORDER BY e.datum ASC
        """, (von.isoformat(), bis.isoformat())).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# Dashboard-Aggregationen
# ─────────────────────────────────────────────

def dashboard_bevorstehende_ereignisse(tage: int = 365) -> dict:
    bis = (date.today() + timedelta(days=tage)).isoformat()
    von = heute()

    with get_connection() as conn:
        def lade(typ):
            return conn.execute("""
                SELECT e.datum, p.name, p.status, p.laufbahnstatus,
                       ds_q.name as quelle, ds_z.name as ziel
                FROM ereignis e
                JOIN person p ON e.person_id = p.id
                LEFT JOIN dienststelle ds_q ON e.quelle_dienststelle = ds_q.id
                LEFT JOIN dienststelle ds_z ON e.ziel_dienststelle = ds_z.id
                WHERE e.typ = ? AND e.datum BETWEEN ? AND ?
                ORDER BY e.datum ASC
            """, (typ, von, bis)).fetchall()

        return {
            "ruhestaende": [dict(r) for r in lade("Ruhestand")],
            "wechsel":     [dict(r) for r in lade("Wechsel")],
            "elternzeiten":[dict(r) for r in lade("Elternzeit")],
        }


def dashboard_unterdeckung(top_n: int = 5) -> list[dict]:
    heute_date = date.today()
    besetzung = berechne_besetzung_zum_stichtag(heute_date)
    unterdeckung = [b for b in besetzung if b["pebby_bedarf"] > 0]
    unterdeckung.sort(key=lambda x: x["deckung"])
    return unterdeckung[:top_n]


# ─────────────────────────────────────────────
# Personenansicht
# ─────────────────────────────────────────────

def lade_person(person_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT p.*, ds.name as dienststelle_name
            FROM person p
            LEFT JOIN dienststelle ds ON p.aktuelle_dienststelle = ds.id
            WHERE p.id = ?
        """, (person_id,)).fetchone()
        if not row:
            return None
        p = dict(row)

        p["ereignisse"] = [dict(e) for e in conn.execute("""
            SELECT e.*, ds_q.name as quelle_name, ds_z.name as ziel_name
            FROM ereignis e
            LEFT JOIN dienststelle ds_q ON e.quelle_dienststelle = ds_q.id
            LEFT JOIN dienststelle ds_z ON e.ziel_dienststelle = ds_z.id
            WHERE e.person_id = ?
            ORDER BY e.datum ASC
        """, (person_id,)).fetchall()]

        p["wuensche"] = [dict(w) for w in conn.execute("""
            SELECT w.*, ds.name as ds_name
            FROM wunsch w
            LEFT JOIN dienststelle ds ON w.wunsch_dienststelle = ds.id
            WHERE w.person_id = ?
            ORDER BY w.prioritaet ASC
        """, (person_id,)).fetchall()]

        return p


# ─────────────────────────────────────────────
# Dienststellenansicht
# ─────────────────────────────────────────────

def lade_dienststelle_detail(ds_id: int, stichtag: Optional[date] = None) -> dict:
    if stichtag is None:
        stichtag = date.today()

    with get_connection() as conn:
        ds = dict(conn.execute("SELECT * FROM dienststelle WHERE id = ?", (ds_id,)).fetchone())

        alle = berechne_besetzung_zum_stichtag(stichtag)
        aktuell_ds = next((x for x in alle if x["id"] == ds_id), None)

        # Zu- und Abgänge in den nächsten 365 Tagen
        bis = stichtag + timedelta(days=365)
        bewegungen = berechne_bewegungen(stichtag, bis)

        zugaenge = [b for b in bewegungen if b["ziel_dienststelle"] == ds_id]
        abgaenge = [b for b in bewegungen if b["quelle_dienststelle"] == ds_id]

        # Planstellen
        planstellen = [dict(p) for p in conn.execute(
            "SELECT * FROM planstelle WHERE dienststelle_id = ?", (ds_id,)
        ).fetchall()]

        return {
            **ds,
            "besetzung_stichtag": aktuell_ds,
            "zugaenge": zugaenge,
            "abgaenge": abgaenge,
            "planstellen": planstellen,
        }


# ─────────────────────────────────────────────
# Wunsch-Matching
# ─────────────────────────────────────────────

def wunsch_matching(ds_id: int) -> list[dict]:
    """
    Findet alle Personen, die Interesse an der angegebenen Dienststelle haben.
    Berücksichtigt sowohl direkten Wunsch nach der Dienststelle als auch
    nach der Region der Dienststelle.
    """
    with get_connection() as conn:
        ds = conn.execute("SELECT * FROM dienststelle WHERE id = ?", (ds_id,)).fetchone()
        if not ds:
            return []

        region = ds["region"]

        matches = conn.execute("""
            SELECT DISTINCT
                p.id, p.name, p.status, p.laufbahnstatus, p.aka_faktor,
                p.aktuelle_dienststelle,
                ds_akt.name as aktuelle_ds_name,
                w.prioritaet,
                w.wunsch_region,
                w.wunsch_dienststelle,
                w.bemerkung,
                CASE
                    WHEN w.wunsch_dienststelle = :ds_id THEN 1
                    WHEN w.wunsch_region = :region THEN 2
                    ELSE 3
                END as match_score
            FROM wunsch w
            JOIN person p ON w.person_id = p.id
            LEFT JOIN dienststelle ds_akt ON p.aktuelle_dienststelle = ds_akt.id
            WHERE w.wunsch_dienststelle = :ds_id
               OR w.wunsch_region = :region
            ORDER BY match_score ASC, w.prioritaet ASC, p.name ASC
        """, {"ds_id": ds_id, "region": region}).fetchall()

        return [dict(m) for m in matches]


# ─────────────────────────────────────────────
# CRUD Ereignisse
# ─────────────────────────────────────────────

def ereignis_anlegen(person_id: int, datum: str, typ: str,
                     quelle_ds: Optional[int], ziel_ds: Optional[int],
                     bemerkung: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (person_id, datum, typ, quelle_ds, ziel_ds, bemerkung))
        eid = cur.lastrowid

        # Aktuelle Dienststelle der Person aktualisieren
        if typ in ("Wechsel", "Abordnung", "Neueinstellung", "Rückkehr") and ziel_ds:
            conn.execute("UPDATE person SET aktuelle_dienststelle = ? WHERE id = ?",
                         (ziel_ds, person_id))
        elif typ == "Ruhestand":
            conn.execute("UPDATE person SET aktuelle_dienststelle = NULL WHERE id = ?",
                         (person_id,))
        return eid


def ereignis_loeschen(ereignis_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM ereignis WHERE id = ?", (ereignis_id,))


def wunsch_anlegen(person_id: int, wunsch_region: Optional[str],
                   wunsch_ds: Optional[int], prioritaet: int, bemerkung: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO wunsch (person_id, wunsch_region, wunsch_dienststelle, prioritaet, bemerkung)
            VALUES (?, ?, ?, ?, ?)
        """, (person_id, wunsch_region, wunsch_ds, prioritaet, bemerkung))
        return cur.lastrowid


def wunsch_loeschen(wunsch_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM wunsch WHERE id = ?", (wunsch_id,))


# ─────────────────────────────────────────────
# Hilfslisten für Dropdowns
# ─────────────────────────────────────────────

def alle_personen() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, name, status, laufbahnstatus FROM person ORDER BY name"
        ).fetchall()]


def alle_dienststellen() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, name, typ, region FROM dienststelle ORDER BY name"
        ).fetchall()]


def alle_regionen() -> list[str]:
    with get_connection() as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT region FROM dienststelle ORDER BY region"
        ).fetchall()]
