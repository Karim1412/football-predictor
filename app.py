from flask import Flask, render_template, request, jsonify
import os, json, random

app = Flask(__name__)
BASE = os.path.dirname(__file__)
MOD  = os.path.join(BASE, "models")

# ── Load H2H data (generated from Colab) ──────────────────────
H2H_DATA = {}
TEAM_LEAGUES = {}
try:
    with open(os.path.join(MOD, "h2h_data.json")) as f:
        raw = json.load(f)
    H2H_DATA    = raw.get("h2h", {})
    TEAM_LEAGUES = raw.get("teams", {})
    print(f"[H2H] Loaded {len(H2H_DATA)} pairs, {len(TEAM_LEAGUES)} teams")
except Exception as e:
    print(f"[H2H] h2h_data.json not found — H2H will be empty ({e})")

# ── Load ML model ─────────────────────────────────────────────
DEMO_MODE = False
try:
    from predictor import predict, team_stats
    # Merge ML teams with H2H teams for the fullest list
    ALL_TEAMS = sorted(set(list(team_stats.keys()) + list(TEAM_LEAGUES.keys())))
    print(f"[ML MODE] {len(ALL_TEAMS)} teams total")
except Exception as e:
    print(f"[DEMO MODE] {e}")
    DEMO_MODE = True
    ALL_TEAMS = sorted(TEAM_LEAGUES.keys()) if TEAM_LEAGUES else [
        "Arsenal","Aston Villa","Birmingham","Blackburn","Blackpool",
        "Bolton","Bournemouth","Bradford","Brentford","Brighton","Burnley",
        "Cardiff","Charlton","Chelsea","Coventry","Crystal Palace","Derby",
        "Everton","Fulham","Huddersfield","Hull","Ipswich","Leeds","Leicester","Liverpool",
        "Luton","Man City","Man United","Middlesbrough","Newcastle","Norwich",
        "Nott'm Forest","Portsmouth","QPR","Reading",
        "Sheffield United","Southampton","Stoke","Sunderland",
        "Swansea","Tottenham","Watford","West Brom","West Ham","Wigan","Wolves",
        "Barcelona","Real Madrid","Ath Madrid","Sevilla","Valencia",
        "Villarreal","Ath Bilbao","Sociedad","Osasuna","Getafe",
        "Celta","Mallorca","Girona","Las Palmas","Alaves",
        "Bayern Munich","Dortmund","RB Leipzig","Leverkusen","Ein Frankfurt",
        "Wolfsburg","Freiburg","Stuttgart","Augsburg","Mainz","Hoffenheim",
        "M'gladbach","Union Berlin","Werder Bremen","Bochum","Heidenheim","Darmstadt",
        "Juventus","Inter","Milan","Napoli","Roma","Lazio","Fiorentina",
        "Atalanta","Bologna","Torino","Monza","Udinese","Cagliari","Lecce",
        "Empoli","Frosinone","Salernitana","Sassuolo","Genoa","Verona",
        "Paris SG","Lyon","Marseille","Monaco","Lille","Rennes","Nice","Lens",
        "Strasbourg","Reims","Toulouse","Montpellier","Nantes","Le Havre",
        "Clermont","Lorient","Metz","Brest",
    ]


# ── Logo proxy ────────────────────────────────────────────────
import urllib.request, urllib.parse, os as _os
from flask import Response, request as freq

TEAM_NAME_MAP = {
    "Ath Madrid":"Atletico Madrid",       "Ath Bilbao":"Athletic Club",
    "Sociedad":"Real Sociedad",            "Celta":"Celta Vigo",
    "Ein Frankfurt":"Eintracht Frankfurt", "M'gladbach":"Borussia Monchengladbach",
    "Dortmund":"Borussia Dortmund",        "Leverkusen":"Bayer Leverkusen",
    "Milan":"AC Milan",                    "Inter":"Inter Milan",
    "Paris SG":"Paris Saint-Germain",      "Nott'm Forest":"Nottingham Forest",
    "Man United":"Manchester United",      "Man City":"Manchester City",
    "West Brom":"West Bromwich Albion",    "West Ham":"West Ham United",
    "Wolves":"Wolverhampton Wanderers",    "Newcastle":"Newcastle United",
    "Espanol":"Espanyol",                  "Betis":"Real Betis",
    "Valladolid":"Real Valladolid",        "FC Koln":"FC Cologne",
    "St Etienne":"Saint-Etienne",          "Brest":"Stade Brestois 29",
    "Clermont":"Clermont Foot",            "Las Palmas":"UD Las Palmas",
    "Alaves":"Deportivo Alaves",           "Fortuna Dusseldorf":"Fortuna Dusseldorf",
    "Sp Gijon":"Sporting Gijon",           "La Coruna":"Deportivo La Coruna",
    "Vallecano":"Rayo Vallecano",          "Greuther Furth":"Greuther Furth",
    "Munich 1860":"1860 Munich",           "Holstein Kiel":"Holstein Kiel",
    "St Pauli":"FC St Pauli",              "Hoffenheim":"TSG Hoffenheim",
    "Hansa Rostock":"Hansa Rostock",       "RB Leipzig":"RB Leipzig",
    "Schalke 04":"Schalke",                "Nurnberg":"FC Nurnberg",
    "Bielefeld":"Arminia Bielefeld",       "Ingolstadt":"FC Ingolstadt 04",
    "Paderborn":"SC Paderborn 07",         "Duisburg":"MSV Duisburg",
    "Augsburg":"FC Augsburg",              "Mainz":"Mainz 05",
    "Wolfsburg":"VfL Wolfsburg",           "Stuttgart":"VfB Stuttgart",
    "Freiburg":"SC Freiburg",              "Hertha":"Hertha Berlin",
    "Bochum":"VfL Bochum",                 "Hamburg":"Hamburger SV",
    "Hannover":"Hannover 96",              "Heidenheim":"1. FC Heidenheim",
    "Darmstadt":"SV Darmstadt 98",         "Cottbus":"Energie Cottbus",
    "Braunschweig":"Eintracht Braunschweig","Luton":"Luton Town",
    "Sheffield United":"Sheffield United", "Crystal Palace":"Crystal Palace",
    "Bournemouth":"Bournemouth",           "Huddersfield":"Huddersfield Town",
    "Hull":"Hull City",                    "Blackburn":"Blackburn Rovers",
    "Bolton":"Bolton Wanderers",           "Bradford":"Bradford City",
    "Charlton":"Charlton Athletic",        "Coventry":"Coventry City",
    "Derby":"Derby County",                "Ipswich":"Ipswich Town",
    "Leeds":"Leeds United",                "Leicester":"Leicester City",
    "Middlesbrough":"Middlesbrough",       "Norwich":"Norwich City",
    "Portsmouth":"Portsmouth",             "QPR":"Queens Park Rangers",
    "Sunderland":"Sunderland",             "Wigan":"Wigan Athletic",
    "Stoke":"Stoke City",                  "Birmingham":"Birmingham City",
    "Swansea":"Swansea City",              "Cardiff":"Cardiff City",
    "Nottm Forest":"Nottingham Forest",    "Werder Bremen":"Werder Bremen",
    "Nantes":"FC Nantes",                  "Guingamp":"En Avant Guingamp",
    "Le Havre":"Le Havre AC",              "Lens":"RC Lens",
    "Troyes":"ESTAC Troyes",               "Reims":"Stade de Reims",
    "Sochaux":"FC Sochaux-Montbeliard",    "Metz":"FC Metz",
    "Ajaccio":"AC Ajaccio",                "Sedan":"CS Sedan",
    "Bastia":"SC Bastia",                  "Caen":"Stade Malherbe Caen",
    "Nancy":"AS Nancy",                    "Dijon":"Dijon FCO",
    "Lorient":"FC Lorient",                "Valenciennes":"Valenciennes FC",
    "Grenoble":"Grenoble Foot 38",
}

# Load pre-downloaded logo map (built by generate_logos.py)
_STATIC_LOGOS = {}
_logo_map_path = _os.path.join(_os.path.dirname(__file__), "static", "logo_map.json")
if _os.path.exists(_logo_map_path):
    with open(_logo_map_path) as _f:
        _STATIC_LOGOS = json.load(_f)

_logo_cache = {}   # in-memory cache for live-fetched logos

def _fetch_from_sportsdb(team):
    """Fetch badge bytes from TheSportsDB. Returns (bytes, content_type) or None."""
    search = TEAM_NAME_MAP.get(team, team)
    api = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={urllib.parse.quote(search)}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        data = json.loads(r.read())
    teams_data = data.get("teams") or []
    if not teams_data or not teams_data[0].get("strBadge"):
        return None
    badge_url = teams_data[0]["strBadge"] + "/medium"
    req2 = urllib.request.Request(badge_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req2, timeout=6) as r2:
        return r2.read(), r2.headers.get("Content-Type", "image/png")

@app.route("/logo/<path:team>")
def team_logo(team):
    team = urllib.parse.unquote(team)

    # 1. Serve from pre-downloaded static file
    if team in _STATIC_LOGOS:
        static_path = _os.path.join(_os.path.dirname(__file__), _STATIC_LOGOS[team].lstrip("/"))
        if _os.path.exists(static_path):
            with open(static_path, "rb") as f:
                return Response(f.read(), mimetype="image/png")

    # 2. In-memory cache (live fetch)
    if team in _logo_cache:
        img_bytes, content_type = _logo_cache[team]
        return Response(img_bytes, mimetype=content_type)

    # 3. Live fetch from TheSportsDB
    try:
        result = _fetch_from_sportsdb(team)
        if result:
            _logo_cache[team] = result
            return Response(result[0], mimetype=result[1])
    except Exception as e:
        print(f"[LOGO] {team!r}: {e}")

    return "", 404

def _parse_match_date(d):
    """Parse multiple date formats into a datetime for sorting."""
    import datetime as _dt
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(d.strip(), fmt)
        except:
            pass
    return _dt.datetime.min

def get_h2h(home, away, n=10):
    """
    Return last n H2H matches sorted by date descending.
    Includes all competitions (domestic league + UCL + FA Cup + Coppa Italia
    after running download_cup_data.py).
    """
    key = "|".join(sorted([home, away]))
    matches = H2H_DATA.get(key, [])
    if not matches:
        return [], None

    # Sort by date descending so most recent appears first
    # regardless of which competition or league
    matches = sorted(matches, key=lambda m: _parse_match_date(m["date"]), reverse=True)[:n]

    result = []
    wins = draws = losses = 0
    for m in matches:
        hs, as_ = m["hs"], m["as_"]
        if m["home"] == home:
            if hs > as_:    outcome, wins   = "Win",  wins+1
            elif hs == as_: outcome, draws  = "Draw", draws+1
            else:           outcome, losses = "Loss", losses+1
        else:
            hs, as_ = as_, hs   # flip score to selected home-team perspective
            if hs > as_:    outcome, wins   = "Win",  wins+1
            elif hs == as_: outcome, draws  = "Draw", draws+1
            else:           outcome, losses = "Loss", losses+1

        # Make league label human-readable
        league_raw = m.get("league", "")
        league_display = (league_raw
            .replace("UEFA_Champions_League", "UCL")
            .replace("FA_Cup",                "FA Cup")
            .replace("Coppa_Italia",          "Coppa Italia")
            .replace("England_PL",            "Premier League")
            .replace("Spain_LaLiga",          "La Liga")
            .replace("Germany_Bundesliga",    "Bundesliga")
            .replace("Italy_SerieA",          "Serie A")
            .replace("France_Ligue1",         "Ligue 1")
            .replace("_", " "))

        result.append({
            "date":    m["date"],
            "home":    m["home"],
            "away":    m["away"],
            "score":   f"{m['hs']}–{m['as_']}",
            "outcome": outcome,
            "league":  league_display,
        })

    summary = {
        "home": home, "away": away,
        "home_wins": wins, "draws": draws, "away_wins": losses,
        "total": len(result),
    }
    return result, summary


@app.route("/")
def index():
    return render_template("index.html",
                           teams=ALL_TEAMS,
                           team_leagues=json.dumps(TEAM_LEAGUES),
                           demo=DEMO_MODE)

@app.route("/predict", methods=["POST"])
def predict_route():
    data = request.get_json(force=True, silent=True) or {}
    home = str(data.get("home_team","")).strip()
    away = str(data.get("away_team","")).strip()

    if not home or not away:
        return jsonify({"error": "Please select both teams."}), 400
    if home == away:
        return jsonify({"error": "Select two different teams."}), 400

    h2h, summary = get_h2h(home, away)

    if not DEMO_MODE:
        if home not in team_stats or away not in team_stats:
            return jsonify({"error": f"Team not found: '{home}' or '{away}'"}), 404
        try:
            result = predict(home, away)
            result["h2h"] = h2h
            result["h2h_summary"] = summary
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Demo mode
    random.seed(abs(hash(home + away)) % (2**31))
    ph  = round(random.uniform(0.33, 0.52), 3)
    pd_ = round(random.uniform(0.17, 0.28), 3)
    pa  = round(max(1 - ph - pd_, 0.05), 3)
    probs  = [ph, pd_, pa]
    labels = {0:"Home Win", 1:"Draw", 2:"Away Win"}
    pred   = labels[probs.index(max(probs))]
    rnd    = lambda a,b: round(random.uniform(a,b), 2)
    form   = lambda: random.choices(["W","D","L"], weights=[45,25,30], k=5)

    return jsonify({
        "home_team": home, "away_team": away,
        "prediction": pred,
        "prob_home": round(ph*100,1), "prob_draw": round(pd_*100,1), "prob_away": round(pa*100,1),
        "confidence": round(max(probs)*100,1),
        "home_form": form(), "away_form": form(),
        "home_stats": {"Goals Scored":rnd(1.1,2.8),"Goals Conceded":rnd(0.6,1.6),
                       "Points / Game":rnd(1.1,2.3),"Shots on Target":rnd(3.2,6.8)},
        "away_stats": {"Goals Scored":rnd(1.1,2.8),"Goals Conceded":rnd(0.6,1.6),
                       "Points / Game":rnd(1.1,2.3),"Shots on Target":rnd(3.2,6.8)},
        "h2h": h2h, "h2h_summary": summary,
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)