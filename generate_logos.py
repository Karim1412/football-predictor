#!/usr/bin/env python3
"""
Run this ONCE before starting the app:
    python generate_logos.py

Downloads all team badges from TheSportsDB into static/logos/
Flask then serves them directly - no external requests during runtime.
"""
import os, json, time, urllib.request, urllib.parse

LOGOS_DIR = os.path.join(os.path.dirname(__file__), "static", "logos")
os.makedirs(LOGOS_DIR, exist_ok=True)

TEAM_NAME_MAP = {
    "Ath Madrid": "Atletico Madrid",      "Ath Bilbao": "Athletic Club",
    "Sociedad": "Real Sociedad",           "Celta": "Celta Vigo",
    "Ein Frankfurt": "Eintracht Frankfurt","M'gladbach": "Borussia Monchengladbach",
    "Werder Bremen": "Werder Bremen",      "Dortmund": "Borussia Dortmund",
    "Leverkusen": "Bayer Leverkusen",      "Milan": "AC Milan",
    "Inter": "Inter Milan",                "Paris SG": "Paris Saint-Germain",
    "Nott'm Forest": "Nottingham Forest",  "Man United": "Manchester United",
    "Man City": "Manchester City",         "West Brom": "West Bromwich Albion",
    "West Ham": "West Ham United",         "Wolves": "Wolverhampton Wanderers",
    "Newcastle": "Newcastle United",       "Espanol": "Espanyol",
    "Betis": "Real Betis",                 "Valladolid": "Real Valladolid",
    "FC Koln": "FC Cologne",               "St Etienne": "Saint-Etienne",
    "Brest": "Stade Brestois 29",          "Clermont": "Clermont Foot",
    "Las Palmas": "UD Las Palmas",         "Alaves": "Deportivo Alaves",
    "Fortuna Dusseldorf": "Fortuna Dusseldorf",
    "Sp Gijon": "Sporting Gijon",          "La Coruna": "Deportivo La Coruna",
    "Vallecano": "Rayo Vallecano",         "Greuther Furth": "Greuther Furth",
    "Munich 1860": "1860 Munich",          "Holstein Kiel": "Holstein Kiel",
    "St Pauli": "FC St Pauli",             "Hoffenheim": "TSG Hoffenheim",
    "Hansa Rostock": "Hansa Rostock",      "RB Leipzig": "RB Leipzig",
    "Schalke 04": "Schalke",               "Nurnberg": "FC Nurnberg",
    "Kaiserslautern": "Kaiserslautern",    "Cottbus": "Energie Cottbus",
    "Bielefeld": "Arminia Bielefeld",      "Ingolstadt": "FC Ingolstadt 04",
    "Paderborn": "SC Paderborn 07",        "Braunschweig": "Eintracht Braunschweig",
    "Duisburg": "MSV Duisburg",            "Augsburg": "FC Augsburg",
    "Mainz": "Mainz 05",                   "Wolfsburg": "VfL Wolfsburg",
    "Stuttgart": "VfB Stuttgart",          "Freiburg": "SC Freiburg",
    "Hertha": "Hertha Berlin",             "Union Berlin": "Union Berlin",
    "Bochum": "VfL Bochum",               "Hamburg": "Hamburger SV",
    "Hannover": "Hannover 96",             "Heidenheim": "1. FC Heidenheim",
    "Darmstadt": "SV Darmstadt 98",
    "Sheffield United": "Sheffield United","Luton": "Luton Town",
    "Brentford": "Brentford",              "Brighton": "Brighton",
    "Crystal Palace": "Crystal Palace",    "Bournemouth": "Bournemouth",
    "Fulham": "Fulham",                    "Nottm Forest": "Nottingham Forest",
    "Watford": "Watford",                  "Swansea": "Swansea City",
    "Cardiff": "Cardiff City",             "Huddersfield": "Huddersfield Town",
    "Hull": "Hull City",                   "Reading": "Reading",
    "Blackburn": "Blackburn Rovers",       "Blackpool": "Blackpool",
    "Bolton": "Bolton Wanderers",          "Bradford": "Bradford City",
    "Burnley": "Burnley",                  "Charlton": "Charlton Athletic",
    "Coventry": "Coventry City",           "Derby": "Derby County",
    "Ipswich": "Ipswich Town",             "Leeds": "Leeds United",
    "Leicester": "Leicester City",         "Middlesbrough": "Middlesbrough",
    "Norwich": "Norwich City",             "Portsmouth": "Portsmouth",
    "QPR": "Queens Park Rangers",          "Sunderland": "Sunderland",
    "Wigan": "Wigan Athletic",             "Stoke": "Stoke City",
    "Birmingham": "Birmingham City",       "Bolton": "Bolton Wanderers",
}

H2H_TEAMS_JSON = "models/h2h_data.json"

def safe_filename(team):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in team) + ".png"

def fetch_badge(search_name, retries=5):
    """Fetch badge with exponential backoff on 429 Too Many Requests."""
    url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={urllib.parse.quote(search_name)}"
    wait = 2  # initial wait in seconds
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            teams = data.get("teams") or []
            if not teams or not teams[0].get("strBadge"):
                return None
            badge_url = teams[0]["strBadge"] + "/medium"
            req2 = urllib.request.Request(badge_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=10) as r2:
                return r2.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    Rate limited — waiting {wait}s before retry {attempt+1}/{retries}...")
                time.sleep(wait)
                wait *= 2  # exponential backoff: 2, 4, 8, 16, 32 seconds
            else:
                raise
    print(f"    Gave up after {retries} retries for: {search_name}")
    return None

def main():
    with open(H2H_TEAMS_JSON) as f:
        all_teams = sorted(json.load(f)["teams"].keys())

    results = {}
    ok = fail = skip = 0

    for i, team in enumerate(all_teams):
        fname = safe_filename(team)
        fpath = os.path.join(LOGOS_DIR, fname)

        if os.path.exists(fpath) and os.path.getsize(fpath) > 500:
            results[team] = f"/static/logos/{fname}"
            skip += 1
            continue

        search = TEAM_NAME_MAP.get(team, team)
        try:
            img = fetch_badge(search)
            if img:
                with open(fpath, "wb") as f:
                    f.write(img)
                results[team] = f"/static/logos/{fname}"
                ok += 1
                print(f"  [{i+1}/{len(all_teams)}] ✓ {team}")
            else:
                fail += 1
                print(f"  [{i+1}/{len(all_teams)}] ✗ {team} (not found)")
        except Exception as e:
            fail += 1
            print(f"  [{i+1}/{len(all_teams)}] ✗ {team}: {e}")

        time.sleep(0.5)  # stay well under rate limit

    out = os.path.join(os.path.dirname(__file__), "static", "logo_map.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone! {ok} downloaded, {skip} cached, {fail} failed")
    print(f"Logo map saved to: {out}")

if __name__ == "__main__":
    main()