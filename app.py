"""
Personalplanungssystem Justizverwaltung – Streamlit Proof of Concept
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

import database as db
import logik
import testdaten


# ─────────────────────────────────────────────
# Initialisierung
# ─────────────────────────────────────────────

def initialisiere():
    db.init_db()
    if not db.db_exists_with_data():
        with st.spinner("Erzeuge Testdaten …"):
            testdaten.erzeuge_testdaten()
        st.success("Testdaten wurden geladen.")
        st.rerun()


# ─────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────

STYLE = """
<style>
/* Grundfarben – klares behördliches Blau mit moderner Präzision */
:root {
    --blau:    #1A3A5C;
    --blau-l:  #2563A8;
    --akzent:  #E8A020;
    --ok:      #2E7D52;
    --warn:    #C0392B;
    --grau-1:  #F5F6F8;
    --grau-2:  #E8EAF0;
    --grau-3:  #9AA3B0;
    --text:    #1C2330;
}

/* Header */
.pp-header {
    background: linear-gradient(135deg, var(--blau) 0%, var(--blau-l) 100%);
    color: #fff;
    padding: 1.4rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.pp-header h1 { font-size: 1.5rem; margin: 0; font-weight: 700; letter-spacing: 0.02em; }
.pp-header p  { margin: 0; opacity: 0.75; font-size: 0.85rem; }

/* Karten */
.karte {
    background: #fff;
    border: 1px solid var(--grau-2);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.karte-titel {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--grau-3);
    margin-bottom: 0.2rem;
}
.karte-wert {
    font-size: 2rem;
    font-weight: 700;
    color: var(--blau);
    line-height: 1.1;
}
.karte-wert.warn { color: var(--warn); }
.karte-wert.ok   { color: var(--ok); }

/* Badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-richter   { background: #DBEAFE; color: #1E40AF; }
.badge-stawa     { background: #FEF3C7; color: #92400E; }
.badge-assessor  { background: #FCE7F3; color: #9D174D; border: 1px solid #F9A8D4; }
.badge-probe     { background: #EDE9FE; color: #5B21B6; border: 1px solid #C4B5FD; }
.badge-lzt       { background: #D1FAE5; color: #065F46; }

/* Ereignis-Typen */
.evt { display: inline-block; padding: 0.1rem 0.45rem; border-radius: 3px; font-size: 0.72rem; font-weight: 600; }
.evt-ruhestand  { background: #FEE2E2; color: #991B1B; }
.evt-wechsel    { background: #DBEAFE; color: #1E3A8A; }
.evt-abordnung  { background: #FEF9C3; color: #854D0E; }
.evt-elternzeit { background: #FCE7F3; color: #831843; }
.evt-rueckkehr  { background: #D1FAE5; color: #064E3B; }
.evt-einst      { background: #E0E7FF; color: #3730A3; }

/* Deckungsbalken */
.deckbar-wrap { background: var(--grau-2); border-radius: 4px; height: 8px; overflow: hidden; }
.deckbar-fill { height: 100%; border-radius: 4px; }

/* Abschnitt-Titel */
.abschnitt {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--blau);
    font-weight: 700;
    border-left: 3px solid var(--akzent);
    padding-left: 0.6rem;
    margin: 1.2rem 0 0.6rem;
}

/* Zeitleiste */
.zeitpunkt {
    border-left: 2px solid var(--grau-2);
    padding-left: 1rem;
    margin-left: 0.3rem;
    margin-bottom: 0.5rem;
    position: relative;
}
.zeitpunkt::before {
    content: '';
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--blau-l);
    position: absolute;
    left: -5px; top: 4px;
}

/* Wunsch-Match */
.match-card {
    border: 1px solid var(--grau-2);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    background: #fff;
}
.match-card.top { border-left: 4px solid var(--akzent); }
</style>
"""


# ─────────────────────────────────────────────
# Hilfsrenderer
# ─────────────────────────────────────────────

def badge_status(status: str) -> str:
    cls = "badge-richter" if status == "Richter" else "badge-stawa"
    return f'<span class="badge {cls}">{status}</span>'


def badge_laufbahn(lb: str) -> str:
    mapping = {"Assessor": "badge-assessor", "Proberichter": "badge-probe", "Lebenszeit": "badge-lzt"}
    cls = mapping.get(lb, "")
    return f'<span class="badge {cls}">{lb}</span>'


def badge_ereignis(typ: str) -> str:
    mapping = {
        "Ruhestand": "evt-ruhestand", "Wechsel": "evt-wechsel",
        "Abordnung": "evt-abordnung", "Elternzeit": "evt-elternzeit",
        "Rückkehr": "evt-rueckkehr", "Neueinstellung": "evt-einst",
    }
    cls = mapping.get(typ, "")
    return f'<span class="evt {cls}">{typ}</span>'


def deckungsfarbe(deckung: float) -> str:
    if deckung >= 0:
        return "#2E7D52"
    elif deckung >= -2:
        return "#E8A020"
    else:
        return "#C0392B"


def deckbar(aka: float, bedarf: float) -> str:
    if bedarf <= 0:
        return ""
    pct = min(100, round(aka / bedarf * 100))
    farbe = deckungsfarbe(aka - bedarf)
    return (f'<div class="deckbar-wrap"><div class="deckbar-fill" '
            f'style="width:{pct}%;background:{farbe}"></div></div>')


def metric_karte(titel: str, wert, modus: str = "normal") -> str:
    cls = f"karte-wert {modus}" if modus in ("warn", "ok") else "karte-wert"
    return (f'<div class="karte">'
            f'<div class="karte-titel">{titel}</div>'
            f'<div class="{cls}">{wert}</div>'
            f'</div>')


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

def seite_dashboard():
    st.markdown('<div class="abschnitt">Überblick – nächste 12 Monate</div>', unsafe_allow_html=True)

    ereignisse = logik.dashboard_bevorstehende_ereignisse(365)
    unterdeckung = logik.dashboard_unterdeckung(5)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n = len(ereignisse["ruhestaende"])
        modus = "warn" if n >= 5 else "normal"
        st.markdown(metric_karte("Bevorstehende Ruheständen", n, modus), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_karte("Geplante Wechsel", len(ereignisse["wechsel"])), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_karte("Elternzeiten", len(ereignisse["elternzeiten"])), unsafe_allow_html=True)
    with c4:
        worst = unterdeckung[0]["deckung"] if unterdeckung else 0
        modus = "warn" if worst < -2 else "normal"
        st.markdown(metric_karte("Größte Unterdeckung", f"{worst:+.1f} AKA"), unsafe_allow_html=True)

    # Zwei Spalten: Ereignislisten + Unterdeckung
    col_links, col_rechts = st.columns([3, 2])

    with col_links:
        # Ruheständer
        if ereignisse["ruhestaende"]:
            st.markdown('<div class="abschnitt">Bevorstehende Ruheständen</div>', unsafe_allow_html=True)
            rows = []
            for e in ereignisse["ruhestaende"]:
                rows.append({
                    "Datum": e["datum"],
                    "Name": e["name"],
                    "Status": e["status"],
                    "Laufbahn": e["laufbahnstatus"],
                    "Dienststelle": e.get("quelle") or "–",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Datum": st.column_config.DateColumn(format="DD.MM.YYYY")})

        # Wechsel
        if ereignisse["wechsel"]:
            st.markdown('<div class="abschnitt">Geplante Wechsel</div>', unsafe_allow_html=True)
            rows = []
            for e in ereignisse["wechsel"]:
                rows.append({
                    "Datum": e["datum"],
                    "Name": e["name"],
                    "Von": e.get("quelle") or "–",
                    "Nach": e.get("ziel") or "–",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Datum": st.column_config.DateColumn(format="DD.MM.YYYY")})

        # Elternzeiten
        if ereignisse["elternzeiten"]:
            st.markdown('<div class="abschnitt">Bevorstehende Elternzeiten</div>', unsafe_allow_html=True)
            rows = []
            for e in ereignisse["elternzeiten"]:
                rows.append({
                    "Datum": e["datum"],
                    "Name": e["name"],
                    "Status": e["status"],
                    "Dienststelle": e.get("quelle") or "–",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Datum": st.column_config.DateColumn(format="DD.MM.YYYY")})

    with col_rechts:
        st.markdown('<div class="abschnitt">Dienststellen mit größter Unterdeckung</div>', unsafe_allow_html=True)
        for ds in unterdeckung:
            farbe = deckungsfarbe(ds["deckung"])
            st.markdown(f"""
            <div class="karte">
                <div style="font-weight:600;font-size:0.9rem">{ds['name']}</div>
                <div style="font-size:0.78rem;color:#666;margin-bottom:0.4rem">{ds['region']} · {ds['typ']}</div>
                {deckbar(ds['aka_summe'], ds['pebby_bedarf'])}
                <div style="display:flex;justify-content:space-between;margin-top:0.3rem;font-size:0.8rem">
                    <span>{ds['aka_summe']:.1f} / {ds['pebby_bedarf']:.1f} AKA</span>
                    <span style="color:{farbe};font-weight:700">{ds['deckung']:+.1f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Mini-Chart: Deckung aller Dienststellen
        st.markdown('<div class="abschnitt">Deckungsquote gesamt</div>', unsafe_allow_html=True)
        alle = logik.berechne_besetzung_zum_stichtag(date.today())
        mit_bedarf = [a for a in alle if a["pebby_bedarf"] > 0]
        if mit_bedarf:
            namen = [a["name"].replace("Staatsanwaltschaft", "StA").replace("Landgericht", "LG")
                    .replace("Amtsgericht", "AG") for a in mit_bedarf]
            deckungen = [a["deckung"] for a in mit_bedarf]
            farben = [deckungsfarbe(d) for d in deckungen]
            fig = go.Figure(go.Bar(
                x=deckungen, y=namen, orientation="h",
                marker_color=farben,
                text=[f"{d:+.1f}" for d in deckungen],
                textposition="outside",
            ))
            fig.update_layout(
                height=max(300, len(namen) * 22),
                margin=dict(l=0, r=40, t=10, b=10),
                xaxis_title="AKA-Deckung",
                xaxis=dict(zeroline=True, zerolinecolor="#333"),
                plot_bgcolor="#fff", paper_bgcolor="#fff",
                font=dict(size=11),
            )
            st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# Personenansicht
# ─────────────────────────────────────────────

def seite_personen():
    personen = logik.alle_personen()
    if not personen:
        st.info("Keine Personen vorhanden.")
        return

    optionen = {f"{p['name']} ({p['status']})": p["id"] for p in personen}
    auswahl = st.selectbox("Person auswählen", list(optionen.keys()))
    person_id = optionen[auswahl]
    p = logik.lade_person(person_id)
    if not p:
        st.error("Person nicht gefunden.")
        return

    # Stammdaten
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        <div class="karte">
            <div style="font-size:1.3rem;font-weight:700;margin-bottom:0.4rem">{p['name']}</div>
            <div style="margin-bottom:0.3rem">
                {badge_status(p['status'])} {badge_laufbahn(p['laufbahnstatus'])}
            </div>
            <div style="font-size:0.85rem;color:#555;margin-top:0.4rem">
                <b>Dienststelle:</b> {p.get('dienststelle_name') or '—'}<br>
                <b>AKA-Faktor:</b> {p['aka_faktor']:.2f}<br>
                <b>Einstellung:</b> {p['einstellungsdatum']}<br>
                <b>Ruhestand:</b> {p.get('ruhestandsdatum') or '—'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        n_ereignisse = len(p["ereignisse"])
        n_wuensche = len(p["wuensche"])
        st.markdown(metric_karte("Geplante Ereignisse", n_ereignisse), unsafe_allow_html=True)
        st.markdown(metric_karte("Hinterlegte Wünsche", n_wuensche), unsafe_allow_html=True)

    # Zeitleiste Ereignisse
    if p["ereignisse"]:
        st.markdown('<div class="abschnitt">Geplante Ereignisse</div>', unsafe_allow_html=True)
        for e in p["ereignisse"]:
            quelle = e.get("quelle_name") or "–"
            ziel   = e.get("ziel_name") or "–"
            bew    = f" · {quelle} → {ziel}" if e["typ"] in ("Wechsel", "Abordnung", "Rückkehr") else ""
            st.markdown(f"""
            <div class="zeitpunkt">
                <div style="font-size:0.78rem;color:#888">{e['datum']}</div>
                <div>{badge_ereignis(e['typ'])} {bew}</div>
                {f'<div style="font-size:0.8rem;color:#666;margin-top:0.1rem">{e["bemerkung"]}</div>' if e.get('bemerkung') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Keine Ereignisse hinterlegt.")

    # Wünsche
    if p["wuensche"]:
        st.markdown('<div class="abschnitt">Hinterlegte Wünsche</div>', unsafe_allow_html=True)
        for w in p["wuensche"]:
            ziel_txt = w.get("ds_name") or w.get("wunsch_region") or "–"
            typ_txt = "Dienststelle" if w.get("ds_name") else "Region"
            st.markdown(f"""
            <div class="karte">
                <span style="font-weight:600;font-size:0.95rem">Priorität {w['prioritaet']}</span>
                <span style="color:#888;font-size:0.8rem"> · {typ_txt}: {ziel_txt}</span>
                {f'<div style="font-size:0.8rem;color:#555;margin-top:0.2rem">{w["bemerkung"]}</div>' if w.get('bemerkung') else ''}
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Dienststellenansicht
# ─────────────────────────────────────────────

def seite_dienststellen():
    dienststellen = logik.alle_dienststellen()
    if not dienststellen:
        st.info("Keine Dienststellen vorhanden.")
        return

    optionen = {d["name"]: d["id"] for d in dienststellen}
    auswahl = st.selectbox("Dienststelle auswählen", list(optionen.keys()))
    ds_id = optionen[auswahl]

    detail = logik.lade_dienststelle_detail(ds_id)
    bs = detail.get("besetzung_stichtag") or {}

    # Header
    typ_icon = "⚖️" if detail["typ"] == "Gericht" else "🏛️"
    st.markdown(f"""
    <div class="pp-header" style="padding:1rem 1.5rem">
        <div>
            <div style="font-size:1.2rem;font-weight:700">{typ_icon} {detail['name']}</div>
            <div style="opacity:0.8;font-size:0.85rem">{detail['region']} · {detail['typ']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Kennzahlen
    c1, c2, c3, c4 = st.columns(4)
    anzahl = bs.get("anzahl_personen", 0)
    aka    = bs.get("aka_summe", 0.0)
    bedarf = detail.get("pebby_bedarf", 0.0)
    deckung = bs.get("deckung", aka - bedarf)

    with c1: st.markdown(metric_karte("Personen (heute)", anzahl), unsafe_allow_html=True)
    with c2: st.markdown(metric_karte("AKA-Summe", f"{aka:.2f}"), unsafe_allow_html=True)
    with c3: st.markdown(metric_karte("PEBB§Y-Bedarf", f"{bedarf:.1f}"), unsafe_allow_html=True)
    with c4:
        modus = "ok" if deckung >= 0 else "warn"
        st.markdown(metric_karte("Deckung", f"{deckung:+.2f}", modus), unsafe_allow_html=True)

    # Deckungsbalken
    st.markdown(deckbar(aka, bedarf), unsafe_allow_html=True)

    # Aktuelle Besetzung
    st.markdown('<div class="abschnitt">Aktuelle Besetzung</div>', unsafe_allow_html=True)
    personen_ds = bs.get("personen", [])
    if personen_ds:
        rows = []
        for p in personen_ds:
            rows.append({
                "Name": p["name"],
                "Status": p["status"],
                "Laufbahn": p["laufbahnstatus"],
                "AKA": p["aka_faktor"],
                "Elternzeit": "✓" if p.get("in_elternzeit") else "",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Personen dieser Dienststelle zugeordnet.")

    # Zu-/Abgänge
    col_zu, col_ab = st.columns(2)
    with col_zu:
        st.markdown('<div class="abschnitt">Zugänge (12 Monate)</div>', unsafe_allow_html=True)
        if detail["zugaenge"]:
            for e in detail["zugaenge"]:
                st.markdown(f"""
                <div class="zeitpunkt">
                    <div style="font-size:0.78rem;color:#888">{e['datum']}</div>
                    <div>{badge_ereignis(e['typ'])} <b>{e['person_name']}</b></div>
                    <div style="font-size:0.78rem;color:#666">von: {e.get('quelle_name') or '–'}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Keine Zugänge geplant.")

    with col_ab:
        st.markdown('<div class="abschnitt">Abgänge (12 Monate)</div>', unsafe_allow_html=True)
        if detail["abgaenge"]:
            for e in detail["abgaenge"]:
                st.markdown(f"""
                <div class="zeitpunkt">
                    <div style="font-size:0.78rem;color:#888">{e['datum']}</div>
                    <div>{badge_ereignis(e['typ'])} <b>{e['person_name']}</b></div>
                    <div style="font-size:0.78rem;color:#666">nach: {e.get('ziel_name') or 'Ausscheiden'}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Keine Abgänge geplant.")

    # Planstellen
    st.markdown('<div class="abschnitt">Planstellen</div>', unsafe_allow_html=True)
    if detail["planstellen"]:
        rows = [{"Bezeichnung": p["bezeichnung"], "Besetzt": "✓" if p["besetzt"] else "○"}
                for p in detail["planstellen"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# Stichtagsansicht
# ─────────────────────────────────────────────

def seite_stichtag():
    st.markdown('<div class="abschnitt">Stichtagssimulation</div>', unsafe_allow_html=True)
    st.caption("Wählen Sie ein beliebiges Datum – das System berechnet die Personalsituation aller Dienststellen.")

    # Filter-Zeile oben
    col_a, col_b, col_c = st.columns([2, 2, 3])
    with col_a:
        stichtag = st.date_input(
            "Stichtag",
            value=date.today() + timedelta(days=180),
            min_value=date(2020, 1, 1),
            max_value=date(2040, 12, 31),
        )
    with col_b:
        typ_filter = st.multiselect(
            "Typ",
            ["Gericht", "Staatsanwaltschaft"],
            default=["Gericht", "Staatsanwaltschaft"],
        )
    with col_c:
        region_filter = st.multiselect(
            "Region",
            logik.alle_regionen(),
            default=[],
        )

    # Berechnung
    besetzung = logik.berechne_besetzung_zum_stichtag(stichtag)
    if typ_filter:
        besetzung = [b for b in besetzung if b["typ"] in typ_filter]
    if region_filter:
        besetzung = [b for b in besetzung if b["region"] in region_filter]

    if not besetzung:
        st.info("Keine Daten für die gewählten Filter.")
        return

    # Kennzahlen
    gesamt_aka    = sum(b["aka_summe"]   for b in besetzung)
    unterdeckt    = sum(1 for b in besetzung if b["deckung"] < 0)
    ueberdeckt    = sum(1 for b in besetzung if b["deckung"] >= 0 and b["pebby_bedarf"] > 0)

    cc = st.columns(4)
    cc[0].metric("Dienststellen", len(besetzung))
    cc[1].metric("AKA gesamt",   f"{gesamt_aka:.1f}")
    cc[2].metric("Unterdeckt",   unterdeckt)
    cc[3].metric("Ausreichend",  ueberdeckt)

    # Tabelle – Styling über eine Hilfsspalte, kein .map() nötig
    st.markdown('<div class="abschnitt">Besetzungstabelle</div>', unsafe_allow_html=True)

    rows = []
    for b in besetzung:
        deckung = round(b["deckung"], 2)
        if deckung >= 0:
            ampel = "🟢"
        elif deckung >= -2:
            ampel = "🟡"
        else:
            ampel = "🔴"
        rows.append({
            "": ampel,
            "Dienststelle": b["name"],
            "Typ": b["typ"],
            "Region": b["region"],
            "Personen": b["anzahl_personen"],
            "AKA": round(b["aka_summe"], 2),
            "PEBB§Y-Bedarf": b["pebby_bedarf"],
            "Deckung": deckung,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"": st.column_config.TextColumn(width="small")})

    # Chart
    st.markdown('<div class="abschnitt">Visuelle Übersicht</div>', unsafe_allow_html=True)
    df_chart = df[["Dienststelle", "Deckung"]].copy().sort_values("Deckung")
    df_chart["Farbe"] = df_chart["Deckung"].apply(deckungsfarbe)

    fig = px.bar(
        df_chart, x="Deckung", y="Dienststelle", orientation="h",
        color="Deckung",
        color_continuous_scale=[(0, "#C0392B"), (0.4, "#E8A020"), (0.6, "#2E7D52"), (1, "#1A5C38")],
        labels={"Deckung": "AKA-Deckung"},
    )
    fig.add_vline(x=0, line_dash="solid", line_color="#333", line_width=1.5)
    fig.update_layout(
        height=max(350, len(df_chart) * 24),
        margin=dict(l=0, r=20, t=10, b=20),
        plot_bgcolor="#fff", paper_bgcolor="#fff",
        coloraxis_showscale=False,
        font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# Wunsch-Matching
# ─────────────────────────────────────────────

def seite_wunsch_matching():
    st.markdown('<div class="abschnitt">Wunsch-Matching</div>', unsafe_allow_html=True)
    st.caption("Zeigt Beschäftigte, die Interesse an einer Dienststelle oder deren Region hinterlegt haben.")

    dienststellen = logik.alle_dienststellen()
    optionen = {d["name"]: d["id"] for d in dienststellen}
    auswahl = st.selectbox("Dienststelle auswählen (z.B. bei freier Stelle)", list(optionen.keys()))
    ds_id = optionen[auswahl]

    matches = logik.wunsch_matching(ds_id)

    if not matches:
        st.info("Keine passenden Beschäftigten mit hinterlegtem Wunsch gefunden.")
        return

    st.success(f"{len(matches)} Treffer gefunden")

    col_direkt, col_region = st.columns(2)

    direkt = [m for m in matches if m["match_score"] == 1]
    region = [m for m in matches if m["match_score"] == 2]

    with col_direkt:
        st.markdown(f'<div class="abschnitt">Direkter Wunsch ({len(direkt)})</div>', unsafe_allow_html=True)
        for m in direkt:
            _render_match_card(m, top=True)

    with col_region:
        st.markdown(f'<div class="abschnitt">Regionswunsch ({len(region)})</div>', unsafe_allow_html=True)
        for m in region:
            _render_match_card(m, top=False)


def _render_match_card(m: dict, top: bool):
    css_extra = "top" if top else ""
    prio_stern = "★" * m["prioritaet"] + "☆" * (3 - m["prioritaet"])
    st.markdown(f"""
    <div class="match-card {css_extra}">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:700">{m['name']}</span>
            <span style="color:#E8A020;font-size:0.9rem">{prio_stern}</span>
        </div>
        <div style="margin-top:0.2rem">
            {badge_status(m['status'])} {badge_laufbahn(m['laufbahnstatus'])}
        </div>
        <div style="font-size:0.8rem;color:#666;margin-top:0.3rem">
            Aktuell: {m.get('aktuelle_ds_name') or '—'} · AKA {m['aka_faktor']:.2f}
        </div>
        {f'<div style="font-size:0.78rem;color:#888;margin-top:0.1rem">{m["bemerkung"]}</div>' if m.get('bemerkung') else ''}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Planungsansicht (Ereignisse CRUD)
# ─────────────────────────────────────────────

def seite_planung():
    st.markdown('<div class="abschnitt">Personalereignisse verwalten</div>', unsafe_allow_html=True)

    tab_neu, tab_liste, tab_wunsch = st.tabs(["Ereignis anlegen", "Alle Ereignisse", "Wunsch anlegen"])

    personen  = logik.alle_personen()
    ds_liste  = logik.alle_dienststellen()

    p_opts    = {f"{p['name']} ({p['status']})": p["id"] for p in personen}
    ds_opts   = {"(keine)": None} | {d["name"]: d["id"] for d in ds_liste}

    with tab_neu:
        with st.form("ereignis_form"):
            st.subheader("Neues Ereignis")
            person_key = st.selectbox("Person", list(p_opts.keys()))
            datum      = st.date_input("Datum", value=date.today() + timedelta(days=90))
            typ        = st.selectbox("Typ", ["Neueinstellung", "Wechsel", "Abordnung",
                                               "Elternzeit", "Rückkehr", "Ruhestand"])
            quelle_key = st.selectbox("Quell-Dienststelle", list(ds_opts.keys()), key="quelle")
            ziel_key   = st.selectbox("Ziel-Dienststelle",  list(ds_opts.keys()), key="ziel")
            bemerkung  = st.text_input("Bemerkung (optional)")
            submitted  = st.form_submit_button("Ereignis speichern", type="primary")

        if submitted:
            pid      = p_opts[person_key]
            quelle   = ds_opts[quelle_key]
            ziel     = ds_opts[ziel_key]
            logik.ereignis_anlegen(pid, datum.isoformat(), typ, quelle, ziel, bemerkung)
            st.success(f"Ereignis für {person_key} gespeichert.")
            st.rerun()

    with tab_liste:
        from database import get_connection
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT e.id, e.datum, e.typ, p.name as person_name,
                       ds_q.name as quelle, ds_z.name as ziel, e.bemerkung
                FROM ereignis e
                JOIN person p ON e.person_id = p.id
                LEFT JOIN dienststelle ds_q ON e.quelle_dienststelle = ds_q.id
                LEFT JOIN dienststelle ds_z ON e.ziel_dienststelle   = ds_z.id
                ORDER BY e.datum ASC
            """).fetchall()

        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            df.columns = ["ID", "Datum", "Typ", "Person", "Von", "Nach", "Bemerkung"]
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Datum": st.column_config.DateColumn(format="DD.MM.YYYY")})

            del_id = st.number_input("Ereignis-ID löschen", min_value=1, step=1, value=1)
            if st.button("Löschen", type="secondary"):
                logik.ereignis_loeschen(int(del_id))
                st.success(f"Ereignis #{del_id} gelöscht.")
                st.rerun()
        else:
            st.info("Keine Ereignisse vorhanden.")

    with tab_wunsch:
        st.subheader("Neuen Wunsch hinterlegen")
        with st.form("wunsch_form"):
            person_key2 = st.selectbox("Person", list(p_opts.keys()), key="wp")
            wunsch_typ  = st.radio("Wunschtyp", ["Region", "Dienststelle"], horizontal=True)
            regionen    = logik.alle_regionen()
            wunsch_reg  = st.selectbox("Wunsch-Region", regionen) if wunsch_typ == "Region" else None
            ds_wunsch_key = st.selectbox("Wunsch-Dienststelle", list(ds_opts.keys()), key="wds") if wunsch_typ == "Dienststelle" else None
            prioritaet  = st.slider("Priorität", 1, 3, 1)
            bem2        = st.text_input("Bemerkung")
            sub2        = st.form_submit_button("Wunsch speichern", type="primary")

        if sub2:
            pid2    = p_opts[person_key2]
            ds_wunsch = ds_opts.get(ds_wunsch_key) if ds_wunsch_key else None
            logik.wunsch_anlegen(pid2, wunsch_reg, ds_wunsch, prioritaet, bem2)
            st.success("Wunsch gespeichert.")
            st.rerun()


# ─────────────────────────────────────────────
# Hauptanwendung
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Personalplanung Justiz",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(STYLE, unsafe_allow_html=True)
    initialisiere()

    # Header
    st.markdown("""
    <div class="pp-header">
        <div style="font-size:2rem">⚖️</div>
        <div>
            <h1>Personalplanungssystem Justizverwaltung</h1>
            <p>Proof of Concept · Gerichte & Staatsanwaltschaften Baden-Württemberg</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    with st.sidebar:
        st.markdown("### Navigation")
        seite = st.radio(
            "Bereich",
            ["📊 Dashboard", "👤 Personen", "🏛️ Dienststellen",
             "📅 Stichtagssimulation", "💬 Wunsch-Matching", "✏️ Planung"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption(f"Datenstand: {date.today().strftime('%d.%m.%Y')}")

        if st.button("🔄 Testdaten neu laden", type="secondary"):
            with st.spinner("Erzeuge Testdaten …"):
                testdaten.erzeuge_testdaten()
            st.success("Testdaten neu geladen.")
            st.rerun()

    # Seitenrouting
    if seite == "📊 Dashboard":
        seite_dashboard()
    elif seite == "👤 Personen":
        seite_personen()
    elif seite == "🏛️ Dienststellen":
        seite_dienststellen()
    elif seite == "📅 Stichtagssimulation":
        seite_stichtag()
    elif seite == "💬 Wunsch-Matching":
        seite_wunsch_matching()
    elif seite == "✏️ Planung":
        seite_planung()


main()
