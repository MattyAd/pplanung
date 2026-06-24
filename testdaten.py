"""
Erzeugt realistische Testdaten für das Personalplanungssystem.
Bayerische Justizverwaltung als Vorbild.
"""
from __future__ import annotations
import sqlite3
from datetime import date, timedelta
import random
from database import get_connection


def erzeuge_testdaten():
    with get_connection() as conn:
        conn.execute("DELETE FROM wunsch")
        conn.execute("DELETE FROM ereignis")
        conn.execute("DELETE FROM planstelle")
        conn.execute("DELETE FROM person")
        conn.execute("DELETE FROM dienststelle")

        # ── Dienststellen ──────────────────────────────────────────
        dienststellen = [
            # (name, typ, region, pebby_bedarf)
            ("Landgericht Stuttgart",        "Gericht",            "Stuttgart",   18.5),
            ("Amtsgericht Stuttgart",        "Gericht",            "Stuttgart",   12.0),
            ("Amtsgericht Böblingen",        "Gericht",            "Stuttgart",    6.5),
            ("Amtsgericht Ludwigsburg",      "Gericht",            "Stuttgart",    5.0),
            ("Amtsgericht Waiblingen",       "Gericht",            "Stuttgart",    4.5),
            ("Landgericht Karlsruhe",        "Gericht",            "Karlsruhe",   15.0),
            ("Amtsgericht Karlsruhe",        "Gericht",            "Karlsruhe",    9.0),
            ("Amtsgericht Pforzheim",        "Gericht",            "Karlsruhe",    5.5),
            ("Landgericht Mannheim",         "Gericht",            "Mannheim",    14.0),
            ("Amtsgericht Mannheim",         "Gericht",            "Mannheim",     8.0),
            ("Landgericht Freiburg",         "Gericht",            "Freiburg",    10.0),
            ("Amtsgericht Freiburg",         "Gericht",            "Freiburg",     6.0),
            ("Amtsgericht Offenburg",        "Gericht",            "Freiburg",     4.0),
            ("Landgericht Ulm",              "Gericht",            "Ulm",          8.0),
            ("Amtsgericht Ulm",              "Gericht",            "Ulm",          5.0),
            ("Staatsanwaltschaft Stuttgart", "Staatsanwaltschaft", "Stuttgart",   16.0),
            ("Staatsanwaltschaft Karlsruhe", "Staatsanwaltschaft", "Karlsruhe",   11.0),
            ("Staatsanwaltschaft Mannheim",  "Staatsanwaltschaft", "Mannheim",    10.0),
            ("Staatsanwaltschaft Freiburg",  "Staatsanwaltschaft", "Freiburg",     8.0),
            ("Staatsanwaltschaft Ulm",       "Staatsanwaltschaft", "Ulm",          6.0),
        ]

        ds_ids = {}
        for name, typ, region, pebby in dienststellen:
            cur = conn.execute(
                "INSERT INTO dienststelle (name, typ, region, pebby_bedarf) VALUES (?, ?, ?, ?)",
                (name, typ, region, pebby)
            )
            ds_ids[name] = cur.lastrowid

        # ── Personen ───────────────────────────────────────────────
        vornamen_m = ["Thomas", "Michael", "Andreas", "Klaus", "Stefan", "Peter",
                      "Martin", "Wolfgang", "Jürgen", "Markus", "Christian", "Frank",
                      "Tobias", "Sebastian", "Daniel", "Florian", "Alexander", "Matthias"]
        vornamen_w = ["Anna", "Maria", "Sabine", "Christine", "Sandra", "Julia",
                      "Monika", "Kathrin", "Elisabeth", "Laura", "Petra", "Claudia",
                      "Stefanie", "Andrea", "Nicole", "Angelika", "Franziska", "Lena"]
        nachnamen = ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer",
                     "Wagner", "Becker", "Schulz", "Hoffmann", "Schäfer", "Koch",
                     "Bauer", "Richter", "Klein", "Wolf", "Schröder", "Neumann",
                     "Zimmermann", "Braun", "Hartmann", "Lange", "Krause", "Werner",
                     "Schmitt", "Weiß", "Kremer", "Vogel", "Kühn", "Jäger"]

        random.seed(42)

        personen_data = []

        # Richter für Gerichte
        gericht_namen = [k for k in ds_ids if "gericht" in k.lower()]

        heute = date.today()

        def zufalls_einstellung(min_jahre=1, max_jahre=35):
            tage = random.randint(min_jahre * 365, max_jahre * 365)
            return (heute - timedelta(days=tage)).replace(day=1).isoformat()

        def zufalls_ruhestand(min_jahre=1, max_jahre=25):
            tage = random.randint(min_jahre * 365, max_jahre * 365)
            return (heute + timedelta(days=tage)).replace(day=1).isoformat()

        # 60 Richter
        for i in range(60):
            weiblich = random.random() < 0.45
            vname = random.choice(vornamen_w if weiblich else vornamen_m)
            nname = random.choice(nachnamen)
            name = f"{vname} {nname}"

            einst_jahre = random.randint(1, 30)
            einst = (heute - timedelta(days=einst_jahre * 365)).replace(day=1).isoformat()

            # Laufbahnstatus nach Dienstjahren
            if einst_jahre < 2:
                lbstatus = "Assessor"
                aka = round(random.uniform(0.5, 0.75), 2)
            elif einst_jahre < 5:
                lbstatus = "Proberichter"
                aka = round(random.uniform(0.75, 0.9), 2)
            else:
                lbstatus = "Lebenszeit"
                aka = round(random.uniform(0.9, 1.0), 2)

            # Ruhestand in 1–20 Jahren
            ruhe = zufalls_ruhestand(1, 20) if einst_jahre > 10 else None

            ds_name = random.choice(gericht_namen)
            ds_id = ds_ids[ds_name]

            personen_data.append({
                "name": name, "status": "Richter", "laufbahnstatus": lbstatus,
                "aka": aka, "einst": einst, "ruhe": ruhe, "ds_id": ds_id
            })

        # 35 Staatsanwälte
        stawa_namen = [k for k in ds_ids if "Staatsanwaltschaft" in k]
        for i in range(35):
            weiblich = random.random() < 0.40
            vname = random.choice(vornamen_w if weiblich else vornamen_m)
            nname = random.choice(nachnamen)
            name = f"{vname} {nname}"

            einst_jahre = random.randint(1, 28)
            einst = (heute - timedelta(days=einst_jahre * 365)).replace(day=1).isoformat()

            if einst_jahre < 2:
                lbstatus = "Assessor"
                aka = round(random.uniform(0.5, 0.75), 2)
            elif einst_jahre < 5:
                lbstatus = "Proberichter"
                aka = round(random.uniform(0.75, 0.9), 2)
            else:
                lbstatus = "Lebenszeit"
                aka = round(random.uniform(0.9, 1.0), 2)

            ruhe = zufalls_ruhestand(2, 18) if einst_jahre > 10 else None
            ds_name = random.choice(stawa_namen)
            ds_id = ds_ids[ds_name]

            personen_data.append({
                "name": name, "status": "Staatsanwalt", "laufbahnstatus": lbstatus,
                "aka": aka, "einst": einst, "ruhe": ruhe, "ds_id": ds_id
            })

        p_ids = []
        for p in personen_data:
            cur = conn.execute("""
                INSERT INTO person (name, status, laufbahnstatus, aka_faktor,
                                   einstellungsdatum, ruhestandsdatum, aktuelle_dienststelle)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (p["name"], p["status"], p["laufbahnstatus"], p["aka"],
                  p["einst"], p["ruhe"], p["ds_id"]))
            p_ids.append(cur.lastrowid)

        # ── Planstellen ────────────────────────────────────────────
        all_ds = conn.execute("SELECT * FROM dienststelle").fetchall()
        for ds in all_ds:
            anzahl = max(3, int(ds["pebby_bedarf"]))
            for j in range(anzahl):
                bezeichnung = f"{'Ri' if ds['typ'] == 'Gericht' else 'StA'}-Stelle {j+1:02d}"
                conn.execute("""
                    INSERT INTO planstelle (dienststelle_id, bezeichnung, besetzt)
                    VALUES (?, ?, ?)
                """, (ds["id"], bezeichnung, random.choice([0, 1, 1, 1])))

        # ── Ereignisse ─────────────────────────────────────────────
        alle_ds_ids = list(ds_ids.values())
        alle_ds_namen = list(ds_ids.keys())

        def zufalls_datum_zukunft(min_tage=30, max_tage=730):
            return (heute + timedelta(days=random.randint(min_tage, max_tage))).isoformat()

        def zufalls_datum_vergangenheit(min_tage=30, max_tage=365):
            return (heute - timedelta(days=random.randint(min_tage, max_tage))).isoformat()

        # Neueinstellungen in der Vergangenheit
        for pid in random.sample(p_ids, 20):
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            conn.execute("""
                INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                VALUES (?, ?, 'Neueinstellung', NULL, ?, 'Ersteinstellung')
            """, (pid, p_row["einstellungsdatum"], p_row["aktuelle_dienststelle"]))

        # Bevorstehende Ruheständen (15 Personen)
        ruhe_kandidaten = [p_ids[i] for i, p in enumerate(personen_data)
                           if p["ruhe"] and p["ruhe"] > heute.isoformat()][:15]
        for pid in ruhe_kandidaten:
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            if p_row["ruhestandsdatum"]:
                conn.execute("""
                    INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                    VALUES (?, ?, 'Ruhestand', ?, NULL, 'Planmäßiger Eintritt in den Ruhestand')
                """, (pid, p_row["ruhestandsdatum"], p_row["aktuelle_dienststelle"]))

        # Geplante Wechsel (12 Personen)
        wechsel_personen = random.sample(p_ids, 12)
        for pid in wechsel_personen:
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            quelle = p_row["aktuelle_dienststelle"]
            ziel = random.choice([d for d in alle_ds_ids if d != quelle])
            datum = zufalls_datum_zukunft(60, 400)
            conn.execute("""
                INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                VALUES (?, ?, 'Wechsel', ?, ?, 'Versetzung auf Antrag')
            """, (pid, datum, quelle, ziel))

        # Abordnungen (6 Personen)
        for pid in random.sample(p_ids, 6):
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            quelle = p_row["aktuelle_dienststelle"]
            ziel = random.choice([d for d in alle_ds_ids if d != quelle])
            datum = zufalls_datum_zukunft(30, 200)
            conn.execute("""
                INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                VALUES (?, ?, 'Abordnung', ?, ?, 'Abordnung zur Unterstützung')
            """, (pid, datum, quelle, ziel))

        # Elternzeiten (8 Personen)
        eltern_personen = random.sample(p_ids, 8)
        for pid in eltern_personen:
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            datum_beginn = zufalls_datum_zukunft(14, 300)
            conn.execute("""
                INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                VALUES (?, ?, 'Elternzeit', ?, NULL, 'Elternzeit Antrag genehmigt')
            """, (pid, datum_beginn, p_row["aktuelle_dienststelle"]))

            # Rückkehr nach 12–18 Monaten
            beginn_date = date.fromisoformat(datum_beginn)
            rueckkehr = (beginn_date + timedelta(days=random.randint(365, 540))).isoformat()
            conn.execute("""
                INSERT INTO ereignis (person_id, datum, typ, quelle_dienststelle, ziel_dienststelle, bemerkung)
                VALUES (?, ?, 'Rückkehr', NULL, ?, 'Rückkehr aus Elternzeit')
            """, (pid, rueckkehr, p_row["aktuelle_dienststelle"]))

        # ── Wünsche ────────────────────────────────────────────────
        regionen = list(set(ds["region"] for ds in conn.execute("SELECT region FROM dienststelle").fetchall()))
        wunsch_personen = random.sample(p_ids, 25)

        for pid in wunsch_personen:
            p_row = conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
            aktuelle_region = conn.execute(
                "SELECT region FROM dienststelle WHERE id = ?",
                (p_row["aktuelle_dienststelle"],)
            ).fetchone()
            aktuelle_region_name = aktuelle_region[0] if aktuelle_region else None

            # 1–2 Wünsche pro Person
            n_wuensche = random.choice([1, 1, 2])
            prio = 1
            for _ in range(n_wuensche):
                if random.random() < 0.5:
                    # Wunsch nach Region
                    wunsch_region = random.choice(regionen)
                    conn.execute("""
                        INSERT INTO wunsch (person_id, wunsch_region, wunsch_dienststelle, prioritaet, bemerkung)
                        VALUES (?, ?, NULL, ?, ?)
                    """, (pid, wunsch_region, prio, f"Familiäre Gründe, Bevorzugung Region {wunsch_region}"))
                else:
                    # Wunsch nach konkreter Dienststelle
                    wunsch_ds = random.choice(alle_ds_ids)
                    conn.execute("""
                        INSERT INTO wunsch (person_id, wunsch_region, wunsch_dienststelle, prioritaet, bemerkung)
                        VALUES (?, NULL, ?, ?, 'Interesse an Fachgebiet')
                    """, (pid, wunsch_ds, prio))
                prio += 1

    print("✅ Testdaten erfolgreich erzeugt.")
    print(f"   Dienststellen: {len(dienststellen)}")
    print(f"   Personen: {len(personen_data)}")


if __name__ == "__main__":
    from database import init_db
    init_db()
    erzeuge_testdaten()
