#!/usr/bin/env python3
"""
Run ONCE to download cup & UCL data from openfootball (GitHub) and merge
into models/h2h_data.json.

    python download_cup_data.py

No API key, no registration required.
Sources:
  - UEFA Champions League  (2011-12 → 2025-26)
  - FA Cup / English       (2018-19 → 2025-26)
  - Coppa Italia           (2020-21 → 2025-26)
"""

import os, re, json, datetime, urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
H2H_FILE = os.path.join(BASE_DIR, "models", "h2h_data.json")

# ── Competitions to download ───────────────────────────────────────────────
SOURCES = [
    # (league_label, url_template, seasons, format)
    {
        "label":   "UEFA_Champions_League",
        "url":     "https://raw.githubusercontent.com/openfootball/champions-league/master/{season}/cl.txt",
        "seasons": ["2011-12","2012-13","2013-14","2014-15","2015-16","2016-17",
                    "2017-18","2018-19","2019-20","2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"],
        "format":  "ucl",    # "Team A (XXX)  v  Team B (YYY)  2-1"
    },
    {
        "label":   "FA_Cup",
        "url":     "https://raw.githubusercontent.com/openfootball/eng-england/master/{season}/facup.txt",
        "seasons": ["2018-19","2019-20","2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"],
        "format":  "facup",  # "Team A  v  Team B  2-1 (1-0)"  – no country codes
    },
    {
        "label":   "Coppa_Italia",
        "url":     "https://raw.githubusercontent.com/openfootball/italy/master/{season}/cup.txt",
        "seasons": ["2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"],
        "format":  "coppa",  # "Team A  2-1  Team B"  – score in the middle
    },
]

# ── Name normalisation maps ────────────────────────────────────────────────
UCL_NAME_MAP = {
    # England
    "Arsenal FC":"Arsenal",                     "Chelsea FC":"Chelsea",
    "Liverpool FC":"Liverpool",                 "Manchester City":"Man City",
    "Manchester City FC":"Man City",            "Manchester United":"Man United",
    "Manchester United FC":"Man United",        "Tottenham Hotspur":"Tottenham",
    "Newcastle United FC":"Newcastle",          "Newcastle United":"Newcastle",
    "Leicester City":"Leicester",               "Aston Villa":"Aston Villa",
    # Spain
    "FC Barcelona":"Barcelona",                 "Real Madrid":"Real Madrid",
    "Real Madrid CF":"Real Madrid",             "Atlético Madrid":"Ath Madrid",
    "Club Atlético de Madrid":"Ath Madrid",     "Athletic Club":"Ath Bilbao",
    "Sevilla FC":"Sevilla",                     "Valencia CF":"Valencia",
    "Villarreal CF":"Villarreal",               "Real Sociedad":"Sociedad",
    "Real Sociedad de Fútbol":"Sociedad",       "Racing Club de Lens":"Lens",
    "Málaga CF":"Malaga",                       "Girona FC":"Girona",
    # Germany
    "FC Bayern München":"Bayern Munich",        "Bayern München":"Bayern Munich",
    "Borussia Dortmund":"Dortmund",             "Bor. Mönchengladbach":"M'gladbach",
    "Bayer Leverkusen":"Leverkusen",            "RB Leipzig":"RB Leipzig",
    "FC Schalke 04":"Schalke 04",               "Eintracht Frankfurt":"Ein Frankfurt",
    "VfL Wolfsburg":"Wolfsburg",                "1. FC Union Berlin":"Union Berlin",
    "1899 Hoffenheim":"Hoffenheim",             "VfB Stuttgart":"Stuttgart",
    "SC Freiburg":"Freiburg",                   "SV Werder Bremen":"Werder Bremen",
    # Italy
    "AC Milan":"Milan",                         "FC Internazionale Milano":"Inter",
    "Inter":"Inter",                            "Juventus":"Juventus",
    "AS Roma":"Roma",                           "SS Lazio":"Lazio",
    "Lazio Roma":"Lazio",                       "SSC Napoli":"Napoli",
    "Atalanta":"Atalanta",                      "ACF Fiorentina":"Fiorentina",
    "Udinese Calcio":"Udinese",                 "Genoa CFC":"Genoa",
    "Hellas Verona":"Verona",                   "Bologna FC":"Bologna",
    "Cagliari Calcio":"Cagliari",               "US Salernitana 1919":"Salernitana",
    "Torino FC":"Torino",                       "Empoli FC":"Empoli",
    "Frosinone Calcio":"Frosinone",             "AC Monza":"Monza",
    "US Lecce":"Lecce",                         "US Sassuolo Calcio":"Sassuolo",
    "Sassuolo Calcio":"Sassuolo",               "UC Sampdoria":"Sampdoria",
    "Spezia Calcio":"Spezia",                   "Venezia FC":"Venezia",
    "Benevento Calcio":"Benevento",             "US Cremonese":"Cremonese",
    "Pisa SC":"Pisa",                           "Parma Calcio 1913":"Parma",
    # France
    "Paris Saint-Germain":"Paris SG",           "Paris Saint-Germain FC":"Paris SG",
    "Olympique Lyonnais":"Lyon",                "Olympique Marseille":"Marseille",
    "AS Monaco":"Monaco",                       "Lille OSC":"Lille",
    "Stade Rennais":"Rennes",                   "Montpellier HSC":"Montpellier",
    "RC Lens":"Lens",                           "Stade de Reims":"Reims",
    "RC Strasbourg Alsace":"Strasbourg",        "OGC Nice":"Nice",
    "FC Nantes":"Nantes",                       "FC Lorient":"Lorient",
    "Stade Brestois 29":"Brest",
}

FA_CUP_NAME_MAP = {
    "Arsenal FC":"Arsenal",             "Chelsea FC":"Chelsea",
    "Liverpool FC":"Liverpool",         "Manchester City":"Man City",
    "Manchester United":"Man United",   "Tottenham Hotspur":"Tottenham",
    "Newcastle United":"Newcastle",     "Aston Villa":"Aston Villa",
    "Everton FC":"Everton",             "Leicester City":"Leicester",
    "West Ham United":"West Ham",       "Leeds United":"Leeds",
    "Wolverhampton Wanderers":"Wolves", "Crystal Palace":"Crystal Palace",
    "Brighton & Hove Albion":"Brighton","Southampton FC":"Southampton",
    "Watford FC":"Watford",             "Burnley FC":"Burnley",
    "Norwich City":"Norwich",           "Brentford FC":"Brentford",
    "Fulham FC":"Fulham",               "Bournemouth AFC":"Bournemouth",
    "Nottingham Forest":"Nott'm Forest","Sheffield United":"Sheffield United",
    "Luton Town":"Luton",               "Coventry City":"Coventry",
    "Sunderland AFC":"Sunderland",      "Bolton Wanderers":"Bolton",
    "Blackburn Rovers":"Blackburn",     "Wigan Athletic":"Wigan",
    "Stoke City":"Stoke",               "Birmingham City":"Birmingham",
    "Swansea City":"Swansea",           "Cardiff City":"Cardiff",
    "Middlesbrough FC":"Middlesbrough", "Derby County":"Derby",
    "Huddersfield Town":"Huddersfield", "Hull City":"Hull",
    "Queens Park Rangers":"QPR",        "Charlton Athletic":"Charlton",
    "Bradford City":"Bradford",         "Ipswich Town":"Ipswich",
    "Reading FC":"Reading",             "Portsmouth FC":"Portsmouth",
    "West Bromwich Albion":"West Brom",
}

# Coppa Italia uses mostly same names as our JSON - only a few differ
COPPA_NAME_MAP = {
    "AC Milan":"Milan",             "FC Internazionale Milano":"Inter",
    "AS Roma":"Roma",               "SS Lazio":"Lazio",
    "Lazio Roma":"Lazio",           "SSC Napoli":"Napoli",
    "ACF Fiorentina":"Fiorentina",  "Udinese Calcio":"Udinese",
    "Genoa CFC":"Genoa",            "Hellas Verona":"Verona",
    "Bologna FC":"Bologna",         "Cagliari Calcio":"Cagliari",
    "US Salernitana 1919":"Salernitana",
    "Torino FC":"Torino",           "Empoli FC":"Empoli",
    "Frosinone Calcio":"Frosinone", "AC Monza":"Monza",
    "US Lecce":"Lecce",             "Sassuolo Calcio":"Sassuolo",
    "UC Sampdoria":"Sampdoria",     "Spezia Calcio":"Spezia",
    "Venezia FC":"Venezia",         "US Cremonese":"Cremonese",
    "Parma Calcio 1913":"Parma",    "Pisa SC":"Pisa",
}

NAME_MAPS = {
    "ucl":   UCL_NAME_MAP,
    "facup": FA_CUP_NAME_MAP,
    "coppa": COPPA_NAME_MAP,
}

# ── Parsers ────────────────────────────────────────────────────────────────
def parse_date(raw, season):
    """Convert 'Sep 19 2023' or 'Sep 20' to 'Sep 20, 2023'."""
    raw = raw.strip()
    yr1 = int(season.split("-")[0])
    yr2 = yr1 + 1
    for fmt, yr in [("%b %d %Y", None), ("%b %d", None)]:
        try:
            if "%Y" in fmt:
                dt = datetime.datetime.strptime(raw, fmt)
            else:
                # Infer year: Sep-Dec = first year, Jan-Jun = second
                dt = datetime.datetime.strptime(raw, fmt)
                month = dt.month
                yr = yr1 if month >= 7 else yr2
                dt = dt.replace(year=yr)
            return dt.strftime("%b %d, %Y")
        except:
            pass
    return raw

def normalize(name, fmt):
    m = NAME_MAPS.get(fmt, {})
    return m.get(name.strip(), name.strip())

# UCL / FA Cup format: "Team A (XXX)  v  Team B (YYY)  2-1"
# FA Cup format (no country code): "Team A  v  Team B  2-1 (1-0)"
RE_UCL   = re.compile(
    r'(?:^\s{4}(?:\d{1,2}:\d{2})?\s+|^\s{11})'
    r'(.+?)\s+\([A-Z]{3}\)\s+v\s+(.+?)\s+\([A-Z]{3}\)\s+(\d+)-(\d+)'
)
RE_FACUP = re.compile(
    r'(?:^\s{4}(?:\d{1,2}:\d{2})?\s+|^\s{11})'
    r'(.+?)\s{2,}v\s{2,}(.+?)\s+(\d+)-(\d+)'
)
# Coppa Italia: "  Team A  2-1 (...)  Team B"  (score in middle)
RE_COPPA = re.compile(
    r'^\s{2}(?:\d{1,2}:\d{2}\s+)?(.+?)\s{2,}(\d+)-(\d+)(?:\s+\d-\d)?\s+(?:\([^)]+\)\s+)?(.+?)\s*$'
)

RE_DATE_FULL  = re.compile(r'^\s{1,4}(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w+\s+\d{1,2}\s+\d{4})')
RE_DATE_SHORT = re.compile(r'^\s{1,4}(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w+\s+\d{1,2})\s*$')
# Coppa Italia uses no weekday prefix sometimes
RE_DATE_COPPA = re.compile(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w+\s+\d{1,2}(?:\s+\d{4})?)')

def parse_file(text, fmt, season, label, known_teams):
    matches = []
    current_date = None

    for line in text.splitlines():
        # -- date detection --
        m = RE_DATE_FULL.match(line) or RE_DATE_COPPA.match(line)
        if m:
            current_date = parse_date(m.group(2), season)
            continue
        m = RE_DATE_SHORT.match(line)
        if m:
            current_date = parse_date(m.group(2), season)
            continue

        if not current_date:
            continue

        # -- match detection --
        if fmt == "coppa":
            m = RE_COPPA.match(line)
            if not m:
                continue
            home = normalize(m.group(1).strip(), fmt)
            hs   = int(m.group(2))
            as_  = int(m.group(3))
            away = normalize(m.group(4).strip(), fmt)
        elif fmt == "ucl":
            m = RE_UCL.match(line)
            if not m:
                continue
            home = normalize(m.group(1), fmt)
            away = normalize(m.group(2), fmt)
            hs, as_ = int(m.group(3)), int(m.group(4))
        else:  # facup
            m = RE_FACUP.match(line)
            if not m:
                continue
            home = normalize(m.group(1), fmt)
            away = normalize(m.group(2), fmt)
            hs, as_ = int(m.group(3)), int(m.group(4))

        # Only keep matches where both teams are tracked
        if home not in known_teams or away not in known_teams:
            continue

        matches.append({
            "date":   current_date,
            "home":   home,
            "away":   away,
            "hs":     hs,
            "as_":    as_,
            "league": label,
        })

    return matches

# ── Main ───────────────────────────────────────────────────────────────────
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", errors="replace")

def main():
    print("Loading h2h_data.json ...")
    with open(H2H_FILE) as f:
        data = json.load(f)
    h2h = data["h2h"]
    known_teams = set(data["teams"].keys())

    grand_total = 0

    for src in SOURCES:
        print(f"\n── {src['label']} ──")
        src_total = 0
        for season in src["seasons"]:
            url = src["url"].format(season=season)
            try:
                text = fetch(url)
            except Exception as e:
                print(f"  {season}: fetch failed — {e}")
                continue

            matches = parse_file(text, src["format"], season,
                                 src["label"], known_teams)
            added = 0
            for m in matches:
                key = "|".join(sorted([m["home"], m["away"]]))
                if key not in h2h:
                    h2h[key] = []
                existing = {(x["date"], x["hs"], x["as_"]) for x in h2h[key]}
                if (m["date"], m["hs"], m["as_"]) not in existing:
                    h2h[key].append(m)
                    added += 1
            src_total += added
            print(f"  {season}: {len(matches)} relevant, {added} new added")

        print(f"  → {src['label']} total: +{src_total}")
        grand_total += src_total

    # Sort each match list by date descending
    def sort_key(m):
        for fmt in ("%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(m["date"], fmt)
            except:
                pass
        return datetime.datetime.min

    for key in h2h:
        h2h[key].sort(key=sort_key, reverse=True)

    data["h2h"] = h2h
    data["total_matches"] = sum(len(v) for v in h2h.values())
    data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d")

    print(f"\nSaving ...")
    with open(H2H_FILE, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"Done! +{grand_total} cup/UCL matches. New total: {data['total_matches']}")

if __name__ == "__main__":
    main()