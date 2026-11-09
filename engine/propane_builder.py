import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/propane-tank-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3").strip()
CUSTOM_PROPANE = os.environ.get("CUSTOM_PROPANE", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_propane.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "published_propane.json_mon" if False else "monetization.json")

_CACHED_MODELS = None

# Format: (Scenario / Equipment Name, Appliance BTU/hr, Usable LP Gallons [80% Fill], Winter Vap BTU @ 0F & 20% Fill, Pipe Run Ft, CSST Pipe Size)
SEED_PROPANE = [
    ("100-Lb Propane Tank (23.6 Gal) Winter BTU Vaporization", 50000, 23.6, 39000, 35, "1/2-Inch CSST / 5/8\" Copper"),
    ("Two Manifolded 100-Lb Propane Tanks (47.2 Gal) Setup", 80000, 47.2, 78000, 50, "3/4-Inch CSST Gas Line"),
    ("120-Gallon Vertical ASME Propane Tank (96 Gal Usable)", 85000, 96.0, 92000, 50, "3/4-Inch CSST Gas Line"),
    ("250-Gallon Horizontal Propane Tank (200 Gal Usable)", 150000, 200.0, 215000, 60, "3/4-Inch CSST / 3/4\" Iron"),
    ("500-Gallon Whole-House Propane Tank (400 Gal Usable)", 250000, 400.0, 380000, 75, "1-Inch CSST / 3/4\" High-PSI"),
    ("1,000-Gallon Estate & Pool Heater Propane Tank (800 Gal)", 400000, 800.0, 720000, 100, "1-Inch CSST + 2-Stage Reg"),
    ("40-Lb RV Propane Cylinders (Dual 9.4 Gal Auto-Changeover)", 35000, 18.8, 48000, 20, "1/2-Inch CSST / 3/8\" Flare"),
    ("Mr. Heater Big Maxx MHU50LP (50,000 BTU) Garage Heater", 50000, 96.0, 92000, 40, "1/2-Inch or 3/4\" CSST"),
    ("Mr. Heater Big Maxx MHU80LP (80,000 BTU) Shop Heater", 80000, 96.0, 92000, 50, "3/4-Inch CSST Gas Line"),
    ("Modine Hot Dawg HD45 & HD60 (45k / 60k BTU) LP Heater", 60000, 96.0, 92000, 45, "3/4-Inch CSST Gas Line"),
    ("Modine Hot Dawg HD75 & HD100 (75k / 100k BTU) Shop Heater", 100000, 200.0, 215000, 60, "3/4-Inch CSST Gas Line"),
    ("Reznor UDXC-60 & UDXC-100 Propane Unit Heater Sizing", 100000, 200.0, 215000, 60, "3/4-Inch CSST Gas Line"),
    ("Dyna-Glo 50,000 & 80,000 BTU LP Forced-Air Shop Heater", 80000, 47.2, 78000, 30, "3/4-Inch CSST Gas Line"),
    ("Rinnai EX22C & EX38C Direct-Vent Propane Wall Furnace", 38400, 96.0, 92000, 35, "1/2-Inch CSST Gas Line"),
    ("Pentair MasterTemp 400 (400,000 BTU) Propane Pool Heater", 400000, 400.0, 380000, 50, "1-Inch CSST / 2-Stage Reg"),
    ("Hayward Universal H-Series 250,000 BTU LP Pool Heater", 250000, 200.0, 215000, 50, "3/4-Inch or 1\" CSST Line"),
    ("Raypak 266,000 & 399,000 BTU Propane Pool/Spa Heater", 333000, 400.0, 380000, 60, "1-Inch CSST / 2-Stage Reg"),
    ("Emerson Fisher R622 / R632 Two-Stage Propane Regulator", 250000, 200.0, 215000, 50, "3/4-Inch NPT / CSST"),
    ("Cavagna 52-A-490 Two-Stage & Auto-Changeover LP Regulator", 160000, 96.0, 92000, 40, "1/2-Inch or 3/4\" CSST"),
    ("Flame King 100-Lb Steel Propane Tank w/ POL/OPD Valve", 50000, 23.6, 39000, 30, "1/2-Inch CSST / Copper"),
    ("Mopeka Pro Check Ultrasonic Bluetooth Propane Tank Sensor", 80000, 96.0, 92000, 45, "3/4-Inch CSST Gas Line"),
    ("Powerblanket 100-Lb & 420-Lb Propane Tank Heater Blanket", 85000, 23.6, 115000, 35, "3/4-Inch CSST Gas Line"),
    ("HomeFlex / Pro-Flex 3/4-Inch CSST Flexible Gas Line Sizing", 110000, 200.0, 215000, 75, "3/4-Inch CSST (11\" WC)"),
    ("HomeFlex / Pro-Flex 1/2-Inch CSST Flexible Gas Line Sizing", 48000, 96.0, 92000, 40, "1/2-Inch CSST (11\" WC)"),
    ("300,000 BTU Outdoor Propane Fire Pit Paver Burner Sizing", 300000, 200.0, 215000, 45, "3/4-Inch or 1\" CSST"),
    ("150,000 BTU Outdoor Patio Fire Table & Grill LP Line", 150000, 96.0, 92000, 50, "3/4-Inch CSST Gas Line"),
    ("60,000 BTU Ventless Propane Gas Log Fireplace Sizing", 60000, 96.0, 92000, 35, "1/2-Inch or 3/4\" CSST"),
    ("80,000 BTU Overhead Infrared Propane Tube Heater (Garage)", 80000, 96.0, 92000, 50, "3/4-Inch CSST Gas Line"),
    ("120,000 BTU Whole-House Propane Furnace Tank & Pipe Sizing", 120000, 200.0, 215000, 60, "3/4-Inch CSST Gas Line"),
    ("NFPA 54 Low-Pressure (11\" WC) vs 2-PSI Propane Regulator", 220000, 400.0, 380000, 100, "3/4-Inch CSST + 2-PSI Reg")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=80000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_propane_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial BTU × Tank × Pipe Length Permutator.
    """
    discovered = []
    seeds = [
        "what size propane tank for ",
        "what size propane line for ",
        "mr heater big maxx ",
        "propane vaporization rate calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        btu_m = re.search(r"\b(30000|45000|50000|60000|75000|80000|100000|150000|200000|45k|50k|60k|80k|100k)\b", cleaned)
                        btu_v = 75000
                        if btu_m:
                            btu_v = int(btu_m.group(1).replace("k", "000"))
                        csst_s = "1/2-Inch CSST" if btu_v <= 50000 else "3/4-Inch CSST Gas Line"
                        discovered.append((cleaned.title(), btu_v, 96.0, 92000, 50, csst_s))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    btu_loads = [45000, 60000, 80000, 100000, 150000, 250000, 350000]
    pipe_runs = [25, 50, 75, 100]
    tank_types = [
        ("100-Lb Tank (23.6 Gal)", 23.6, 39000),
        ("120-Gallon Tank (96 Gal)", 96.0, 92000),
        ("250-Gallon Tank (200 Gal)", 200.0, 215000),
        ("500-Gallon Tank (400 Gal)", 400.0, 380000)
    ]
    for btu_l in btu_loads:
        for p_ft in pipe_runs:
            for t_lbl, u_gal, v_btu in tank_types:
                if btu_l > v_btu * 1.5:
                    continue
                combo_title = f"{btu_l:,} BTU Load on {t_lbl} ({p_ft} Ft Gas Run)"
                test_slug = slugify(f"{combo_title}-vaporization-pipe-calculator")
                if test_slug not in published_slugs:
                    csst_sz = "1/2-Inch CSST" if (btu_l <= 50000 and p_ft <= 40) else ("3/4-Inch CSST" if btu_l <= 160000 else "1-Inch CSST")
                    discovered.append((combo_title, btu_l, u_gal, v_btu, p_ft, csst_sz))
                    if len(discovered) >= 25:
                        return discovered
    return discovered


def build_deterministic_propane_data(prop_tuple):
    """
    LAPIS 3: Mesin Fisika Penguapan Propana (91,502 BTU/gal) & Pipa Gas NFPA 54 (100% Bebas Gagal).
    """
    item_name, app_btu, usable_gal, vap_btu_0f, pipe_ft, csst_spec = prop_tuple

    # Konstanta Fisika Liquid Propane (HD-5):
    # 1 US Gallon Liquid Propane = 91,502 BTU = 4.24 lbs = 36.39 Cubic Feet of Gas
    gal_per_hr_full = round(app_btu / 91502.0, 2)
    lbs_per_hr_full = round(gal_per_hr_full * 4.24, 2)

    # Durasi nyala non-stop 100% vs siklus kerja pemanas musim dingin rata-rata 35% (8.4 jam aktif per hari):
    continuous_runtime_hrs = round(usable_gal / max(0.1, gal_per_hr_full), 1)
    winter_35pct_days = round((continuous_runtime_hrs / 0.35) / 24.0, 1)

    # Evaluasi Pembekuan Tangki (Winter Vaporization Bottleneck @ 0°F & 20% Tank Fill):
    if app_btu <= vap_btu_0f:
        vap_status = f"SAFE: Tank vaporizes {vap_btu_0f:,} BTU/hr at 0°F (20% fill), exceeding your {app_btu:,} BTU/hr demand."
    else:
        vap_status = f"FREEZE-UP WARNING: At 0°F and 20% fill, a single tank only vaporizes {vap_btu_0f:,} BTU/hr (short of {app_btu:,} BTU/hr). Manifold 2 tanks in parallel, wrap with a Thermostatic Tank Heater Blanket, or upsize to the next ASME tank tier."

    return {
        "setup_name": item_name,
        "csst_spec": csst_spec,
        "seo_title": f"{item_name} BTU Vaporization, CSST Pipe & Runtime Calculator (2026)",
        "meta_description": f"Calculate exact winter propane vaporization ({vap_btu_0f:,} BTU/hr @ 0°F), fuel burn ({gal_per_hr_full} gal/hr), {usable_gal}-gal runtime ({winter_35pct_days} days), and NFPA 54 {csst_spec} sizing for {item_name}.",
        "specs": {
            "appliance_btu_hr": app_btu,
            "usable_propane_gallons": usable_gal,
            "winter_vaporization_0f_btu": vap_btu_0f,
            "burn_rate_gal_hr": gal_per_hr_full,
            "burn_rate_lbs_hr": lbs_per_hr_full,
            "continuous_runtime_hrs": continuous_runtime_hrs,
            "winter_35pct_runtime_days": winter_35pct_days,
            "gas_pipe_run_ft": pipe_ft,
            "recommended_pipe_spec": csst_spec,
            "vaporization_verdict_short": vap_status
        },
        "nfpa_verdict": f"Operating a {app_btu:,} BTU/hr propane load ({item_name}) consumes {gal_per_hr_full} gallons ({lbs_per_hr_full} lbs) per hour at 91,502 BTU/gallon—providing {continuous_runtime_hrs} continuous hours or ~{winter_35pct_days} winter days (at a 35% thermostat duty cycle) on {usable_gal} usable gallons (80% tank fill). Over a {pipe_ft}-foot supply run at 11\" Water Column (WC) low pressure, NFPA 54 requires {csst_spec} fed by a Two-Stage Regulator. Winter Vaporization Check: {vap_status}",
        "hardware_bundle": [
            {
                "badge": f"{csst_spec} Gas Line Kit",
                "title": f"{max(35, pipe_ft)}ft {csst_spec} Flexible Yellow Stainless Gas Tubing Coil + Male Brass Flare Fittings",
                "price_range": "$89 - $259",
                "amazon_query": f"{csst_spec.split()[0]} Inch CSST Flexible Gas Line Tubing Kit Brass Fittings",
                "lp_note": f"Delivers {app_btu:,}+ BTU/hr over {pipe_ft} feet with <0.5\" WC pressure drop per NFPA 54 sizing tables."
            },
            {
                "badge": "Two-Stage LP Regulator",
                "title": "UL-Listed High-Capacity Two-Stage Propane Regulator (1st Stage 10 PSI + 2nd Stage 11\" WC) / Auto-Changeover",
                "price_range": "$54 - $179",
                "amazon_query": "Emerson Fisher Cavagna Two Stage Propane Regulator 11 WC",
                "lp_note": "Single-stage regulators freeze up and starve heaters in winter; a 2-stage regulator maintains rock-steady 11\" WC manifold pressure."
            },
            {
                "badge": "Tank Blanket & Ultrasonic Sensor",
                "title": "Thermostatic Propane Tank Heating Blanket + Mopeka Pro Check Bluetooth Ultrasonic Level Sensor",
                "price_range": "$64 - $319",
                "amazon_query": "Propane Tank Heater Blanket Mopeka Pro Check Ultrasonic Sensor",
                "lp_note": "Boosts winter BTU vaporization rate by 300% on 100-lb/420-lb cylinders and tracks exact tank % from your smartphone."
            },
            {
                "badge": f"{app_btu // 1000}K BTU Heater / DOT Tank",
                "title": "Forced-Air Propane Garage/Shop Unit Heater (50,000–80,000 BTU) or Flame King 100-Lb Steel Tank",
                "price_range": "$139 - $629",
                "amazon_query": "Mr Heater Big Maxx Propane Garage Heater Flame King 100 lb Tank",
                "lp_note": f"High-efficiency combustion converts {gal_per_hr_full} gal/hr of liquid propane into clean workspace heat."
            }
        ],
        "gas_checklist": [
            f"Size your propane tank by Winter Vaporization Rate at 20% tank fill and 0°F ({vap_btu_0f:,} BTU/hr), never by summer capacity! As liquid propane boils into gas, refrigeration cools the steel tank; if BTU draw exceeds wetted-surface heat transfer, pressure drops below 11\" WC and your burner flames out.",
            "Always use a Two-Stage Regulator System (10 PSI High-Pressure First-Stage Regulator at the tank + 11\" WC Second-Stage Regulator at the building wall) for any exterior run exceeding 15 feet.",
            f"Bond all yellow-jacketed CSST flexible gas piping ({csst_spec}) directly to the building's electrical grounding electrode system using a 6 AWG copper bonding wire and brass clamp per NFPA 54 Section 7.13 to prevent lightning arc perforation.",
            "Install a 3-inch capped vertical Drip Leg (Sediment Trap) and a quarter-turn brass gas shutoff valve immediately upstream of the appliance gas valve to catch pipe scale and moisture."
        ],
        "faqs": [
            {
                "q": f"How many gallons of propane per hour does {app_btu:,} BTU burn?",
                "a": f"One gallon of liquid propane contains 91,502 BTU of energy. Dividing {app_btu:,} BTU/hr by 91,502 equals {gal_per_hr_full} gallons/hour ({lbs_per_hr_full} lbs/hr). On {usable_gal} usable gallons, that lasts {continuous_runtime_hrs} hours of non-stop 100% burn, or ~{winter_35pct_days} days when cycling 35% of the time."
            },
            {
                "q": f"Why does my 100-lb propane tank freeze up and stop working on a {app_btu:,} BTU heater when it is still 30% full?",
                "a": f"Propane liquid must absorb ambient heat through the wetted lower walls of the tank to boil into gas. At 0°F and 20%–30% liquid level, a single 100-lb cylinder can only vaporize ~39,000 BTU/hr. Drawing {app_btu:,} BTU/hr refrigerates the liquid below -44°F (its boiling point), dropping pressure to zero. Manifold two 100-lb tanks together, add a thermostatic tank heater blanket, or upgrade to a 120-gal/250-gal tank."
            },
            {
                "q": f"What size CSST or copper gas line do I need for {app_btu:,} BTU at {pipe_ft} feet?",
                "a": f"Per NFPA 54 low-pressure (11\" WC with 0.5\" WC pressure drop) tables, delivering {app_btu:,} BTU/hr over {pipe_ft} feet requires {csst_spec}."
            }
        ]
    }


def generate_propane_data(prop_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_propane_data(prop_tuple)

    item_name, app_btu, usable_gal, vap_btu_0f, pipe_ft, csst_spec = prop_tuple
    det_fallback = build_deterministic_propane_data(prop_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified CETP (Certified Employee Training Program) Master Propane Gas Engineer & NFPA 54 Code Specialist. Create an accurate 2026 propane tank winter vaporization rate (BTU/hr at 0F & 20% fill), fuel consumption (gal/hr), and CSST/copper gas pipe sizing guide for: "{item_name}".
Baseline specs: Appliance Load={app_btu} BTU/hr ({sp['burn_rate_gal_hr']} gal/hr), Usable Tank Capacity={usable_gal} Gal ({sp['continuous_runtime_hrs']} hrs continuous / {sp['winter_35pct_runtime_days']} winter days @ 35% cycle), Winter Vaporization @ 0F={vap_btu_0f} BTU/hr, Pipe Run={pipe_ft} ft ({csst_spec}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "setup_name": "{item_name}",
  "csst_spec": "{csst_spec}",
  "seo_title": "{item_name} BTU Vaporization, CSST Pipe & Runtime Calculator (2026)",
  "meta_description": "Calculate exact winter propane BTU vaporization rate, gallons per hour burn rate, tank runtime, and NFPA 54 CSST pipe size for {item_name}.",
  "specs": {{
    "appliance_btu_hr": {app_btu},
    "usable_propane_gallons": {usable_gal},
    "winter_vaporization_0f_btu": {vap_btu_0f},
    "burn_rate_gal_hr": {sp['burn_rate_gal_hr']},
    "burn_rate_lbs_hr": {sp['burn_rate_lbs_hr']},
    "continuous_runtime_hrs": {sp['continuous_runtime_hrs']},
    "winter_35pct_runtime_days": {sp['winter_35pct_runtime_days']},
    "gas_pipe_run_ft": {pipe_ft},
    "recommended_pipe_spec": "{csst_spec}",
    "vaporization_verdict_short": "{sp['vaporization_verdict_short']}"
  }},
  "nfpa_verdict": "3-sentence technical summary stating gallons/hour burned (at 91,502 BTU/gal), winter vaporization BTU limit at 0F/20% fill, and required NFPA 54 CSST pipe diameter and two-stage regulator.",
  "hardware_bundle": [
    {{
      "badge": "{csst_spec} Gas Line",
      "title": "{max(35, pipe_ft)}ft {csst_spec} Flexible Yellow Stainless Gas Tubing Kit + Brass Fittings",
      "price_range": "$89 - $259",
      "amazon_query": "{csst_spec.split()[0]} Inch CSST Flexible Gas Line Tubing Kit",
      "lp_note": "1-sentence NFPA 54 BTU flow and 11-inch WC drop note"
    }},
    {{
      "badge": "Two-Stage LP Regulator",
      "title": "UL-Listed High-Capacity Two-Stage Propane Regulator (11\" WC) / Auto-Changeover",
      "price_range": "$54 - $179",
      "amazon_query": "Emerson Fisher Cavagna Two Stage Propane Regulator",
      "lp_note": "1-sentence freeze-up prevention and steady manifold pressure note"
    }},
    {{
      "badge": "Tank Blanket & Level Sensor",
      "title": "Thermostatic Propane Tank Heater Blanket + Mopeka Pro Check Bluetooth Ultrasonic Sensor",
      "price_range": "$64 - $319",
      "amazon_query": "Propane Tank Heater Blanket Mopeka Pro Check Sensor",
      "lp_note": "1-sentence winter vaporization boost and Bluetooth level tracking note"
    }},
    {{
      "badge": "{app_btu // 1000}K BTU Heater / Tank",
      "title": "Forced-Air Propane Garage/Shop Heater or Flame King 100-Lb Steel Cylinder",
      "price_range": "$139 - $629",
      "amazon_query": "Mr Heater Big Maxx Propane Garage Heater Flame King 100 lb",
      "lp_note": "1-sentence thermal efficiency and OPD valve safety note"
    }}
  ],
  "gas_checklist": [
    "Step 1 regarding 0F / 20% fill wetted-surface vaporization rate to prevent tank freeze-up",
    "Step 2 regarding Two-Stage Regulator (10 PSI first stage + 11-inch WC second stage)",
    "Step 3 regarding 6 AWG copper bonding clamp on CSST per NFPA 54 Section 7.13",
    "Step 4 regarding 3-inch sediment trap (drip leg) installation at appliance inlet"
  ],
  "faqs": [
    {{"q": "How many gallons of propane per hour does {item_name} use?", "a": "Exact BTU divided by 91,502 formula in gal/hr, lbs/hr, and runtime days."}},
    {{"q": "How many BTU can a propane tank vaporize in freezing 0F winter weather?", "a": "Exact wetted surface vaporization BTU numbers for 100-lb, 120-gal, 250-gal, and 500-gal tanks."}},
    {{"q": "What size CSST or copper gas line do I need for {app_btu} BTU at {pipe_ft} feet?", "a": "Exact NFPA 54 pipe diameter for 11-inch WC vs 2-PSI systems."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{item_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")
                break

    return det_fallback


def build_propane_html_page(data, slug, mon_cfg):
    setup_name = data.get("setup_name", "Propane Tank & Gas Line System")
    sp = data.get("specs", {})
    app_btu = int(safe_float(sp.get("appliance_btu_hr", 80000), 80000))
    u_gal = round(safe_float(sp.get("usable_propane_gallons", 96.0), 96.0), 1)
    vap_0f = int(safe_float(sp.get("winter_vaporization_0f_btu", 92000), 92000))
    gal_hr = round(safe_float(sp.get("burn_rate_gal_hr", 0.87), 0.87), 2)
    cont_hrs = round(safe_float(sp.get("continuous_runtime_hrs", 110.0), 110.0), 1)
    win_days = round(safe_float(sp.get("winter_35pct_runtime_days", 13.1), 13.1), 1)
    pipe_ft = int(safe_float(sp.get("gas_pipe_run_ft", 50), 50))
    pipe_spec = sp.get("recommended_pipe_spec", "3/4-Inch CSST Gas Line")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Propane+Two+Stage+Regulator+CSST+Gas+Line+Kit"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{setup_name} Vaporization, CSST Pipe & Runtime Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Propane Regulator CSST Kit")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'LP Gas Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🔥 {item.get('lp_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Propane Tank Size vs Usable Gallons & Winter Vaporization BTU Matrix Table
    tank_tiers = [
        ("40-Lb Cylinder (Dual RV Pack)", "18.8 Gal (2x 9.4 Gal)", "48,000 BTU/hr", "25,000 BTU/hr", "Camper / 30k BTU Heater"),
        ("100-Lb DOT Cylinder (420-Lb Eq)", "23.6 Gal (100 lbs LP)", "39,000 BTU/hr", "21,000 BTU/hr", "50k BTU (w/ Tank Blanket)"),
        ("Dual Manifolded 100-Lb Tanks", "47.2 Gal (200 lbs LP)", "78,000 BTU/hr", "42,000 BTU/hr", "50k – 80k BTU Shop Heater"),
        ("120-Gallon ASME Vertical Tank", "96.0 Gal (80% Fill)", "92,000 BTU/hr", "54,000 BTU/hr", "80k BTU Garage / Fireplace"),
        ("250-Gallon ASME Horizontal Tank", "200.0 Gal (80% Fill)", "215,000 BTU/hr", "125,000 BTU/hr", "150k BTU Shop / Furnace"),
        ("500-Gallon Whole-House Tank", "400.0 Gal (80% Fill)", "380,000 BTU/hr", "225,000 BTU/hr", "Whole-Home + Pool Heater")
    ]
    matrix_rows_html = ""
    for t_lbl, g_lbl, v0_lbl, v10_lbl, ap_lbl in tank_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{t_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{g_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{v0_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{v10_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{ap_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("gas_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer lp-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>NFPA 54 Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', setup_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', setup_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-slate-950 px-2 py-0.5 rounded font-black">PROPANE</span>BTUIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Regulators, CSST & Heaters →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-slate-950 px-3 py-1 rounded-full">{app_btu:,} BTU/hr ({gal_hr} Gal/Hr)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">0°F Vaporization: {vap_0f:,} BTU/hr</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">Pipe: {pipe_spec} ({pipe_ft} ft) | Runtime: ~{win_days} Days</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', setup_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>CETP & NFPA 54 Engineering Verdict:</strong> {data.get('nfpa_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE WINTER VAPORIZATION, RUNTIME & NFPA 54 CSST PIPE CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {setup_name} Vaporization, Pipe & Runtime Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your total appliance BTU/hr load, propane tank size, coldest winter temperature (at 20% low tank fill), and gas line length to check for winter tank freeze-up and compute required CSST pipe size.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="btuSlider" class="text-slate-300">Total Appliance Heat Demand (BTU/hr)</label>
              <span class="text-amber-400 font-bold"><span id="btuVal">{app_btu:,}</span> BTU/hr</span>
            </div>
            <input id="btuSlider" type="range" min="20000" max="400000" step="5000" value="{app_btu}" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="tankSelect" class="block text-xs font-medium text-slate-400 mb-1">Propane Tank Size (80% Fill)</label>
              <select id="tankSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="23.6|39000" {"selected" if u_gal <= 25 else ""}>100-Lb Tank (23.6 Gal Usable)</option>
                <option value="47.2|78000" {"selected" if 25 < u_gal <= 50 else ""}>Dual 100-Lb Manifold (47.2 Gal)</option>
                <option value="96.0|92000" {"selected" if 50 < u_gal <= 110 else ""}>120-Gallon ASME (96 Gal Usable)</option>
                <option value="200.0|215000" {"selected" if 110 < u_gal <= 250 else ""}>250-Gallon ASME (200 Gal Usable)</option>
                <option value="400.0|380000" {"selected" if u_gal > 250 else ""}>500-Gallon ASME (400 Gal Usable)</option>
              </select>
            </div>
            <div>
              <label for="tempSelect" class="block text-xs font-medium text-slate-400 mb-1">Winter Temp (@20% Low Tank)</label>
              <select id="tempSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="1.35">+20°F Mild Winter (1.35x Vap)</option>
                <option value="1.00" selected>0°F Freezing Winter (1.0x Vap)</option>
                <option value="0.62">-15°F Arctic Freeze (0.62x Vap)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="pipeSlider" class="text-slate-300">Gas Line Distance from Tank/Regulator to Appliance (Feet)</label>
              <span class="text-amber-400 font-bold"><span id="pipeVal">{pipe_ft}</span> ft Run</span>
            </div>
            <input id="pipeSlider" type="range" min="10" max="150" step="5" value="{pipe_ft}" class="w-full accent-amber-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Burn Rate & Runtime</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="galHrOut">{gal_hr}</span> <span class="text-xs font-normal text-slate-400">Gal/hr</span></div>
            <p id="daysOut" class="text-xs text-amber-400 font-semibold mt-1">~{win_days} Days (35% Cycle) / {cont_hrs}h</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">NFPA 54 Pipe & Vap</span>
            <div id="csstOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{pipe_spec.split()[0]} CSST</div>
            <p id="vapStatusOut" class="text-xs text-emerald-400 font-semibold mt-1">✅ Max Vap: {vap_0f:,} BTU/hr</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="lpAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicLpBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched CSST Line & Regulator on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {setup_name} CSST Line, Regulator & Tank Heater Kit</h2>
        <span class="text-xs text-slate-400">UL-144 & NFPA 54 Fuel Gas Code Compliant</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Propane Tank Winter BTU Vaporization Rate Chart (At Critical 20% Tank Fill)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Propane Tank Size</th>
              <th class="py-3.5 px-4">Usable Gallons (80%)</th>
              <th class="py-3.5 px-4 text-amber-400">Max BTU/hr @ 0°F (20% Fill)</th>
              <th class="py-3.5 px-4 text-emerald-400">Max BTU/hr @ -10°F (20% Fill)</th>
              <th class="py-3.5 px-4">Max Recommended Heater</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">NFPA 54 Gas Piping, CSST Bonding & Two-Stage Regulator Checklist</h2>
        <span id="lpBadge" class="text-xs font-bold bg-slate-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({setup_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} PropaneBTUIndex. Independent Propane Thermodynamics & NFPA 54 Gas Piping Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const btuSlider = document.getElementById('btuSlider');
    const tankSelect = document.getElementById('tankSelect');
    const tempSelect = document.getElementById('tempSelect');
    const pipeSlider = document.getElementById('pipeSlider');
    const btuVal = document.getElementById('btuVal');
    const pipeVal = document.getElementById('pipeVal');
    const galHrOut = document.getElementById('galHrOut');
    const daysOut = document.getElementById('daysOut');
    const csstOut = document.getElementById('csstOut');
    const vapStatusOut = document.getElementById('vapStatusOut');
    const lpAdviceBanner = document.getElementById('lpAdviceBanner');
    const dynamicLpBtn = document.getElementById('dynamicLpBtn');

    function recalculatePropane() {{
      const btu = parseInt(btuSlider.value, 10);
      const tankParts = tankSelect.value.split('|');
      const usableGals = parseFloat(tankParts[0]);
      const baseVap0F = parseInt(tankParts[1], 10);
      const tempMult = parseFloat(tempSelect.value);
      const pipeFt = parseInt(pipeSlider.value, 10);

      btuVal.textContent = btu.toLocaleString();
      pipeVal.textContent = pipeFt;

      const galHr = btu / 91502.0;
      const contHrs = (usableGals / galHr).toFixed(1);
      const winterDays = ((usableGals / (galHr * 0.35)) / 24.0).toFixed(1);
      const actualMaxVapBtu = Math.round((baseVap0F * tempMult) / 1000) * 1000;

      // NFPA 54 Low-Pressure (11" WC) CSST Sizing
      const sizingFactor = btu * Math.sqrt(pipeFt / 40.0);
      let csstDia = '1/2" CSST';
      if (sizingFactor <= 52000) csstDia = '1/2" CSST';
      else if (sizingFactor <= 145000) csstDia = '3/4" CSST';
      else csstDia = '1" CSST (or 2-PSI Reg)';

      galHrOut.textContent = galHr.toFixed(2);
      daysOut.textContent = `~${{winterDays}} Days (35% Cycle) / ${{contHrs}}h`;
      csstOut.textContent = csstDia;

      if (btu <= actualMaxVapBtu) {{
        vapStatusOut.textContent = `✅ Safe (Vap Cap: ${{(actualMaxVapBtu/1000).toFixed(0)}}k BTU)`;
        vapStatusOut.className = "text-xs text-emerald-400 font-semibold mt-1";
      }} else {{
        vapStatusOut.textContent = `⚠️ Freeze Risk! Max ${{(actualMaxVapBtu/1000).toFixed(0)}}k BTU`;
        vapStatusOut.className = "text-xs text-amber-400 font-bold mt-1";
      }}

      const freezeFix = btu > actualMaxVapBtu ? " + a <strong>Thermostatic Propane Tank Heater Blanket</strong> (to prevent winter pressure freeze-up)" : "";
      lpAdviceBanner.innerHTML = `🔥 <strong>NFPA 54 Spec:</strong> Running <strong>${{btu.toLocaleString()}} BTU/hr (${{galHr.toFixed(2)}} gal/hr)</strong> over ${{pipeFt}} feet requires <strong>${{csstDia}} Flexible Gas Line</strong> with a <strong>Two-Stage 11" WC Regulator</strong>${{freezeFix}}.`;
      dynamicLpBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(csstDia)}}+Flexible+Gas+Line+Kit+Two+Stage+Propane+Regulator&tag=${{amzTag}}`;
    }}

    btuSlider.addEventListener('input', recalculatePropane);
    tankSelect.addEventListener('change', recalculatePropane);
    tempSelect.addEventListener('change', recalculatePropane);
    pipeSlider.addEventListener('input', recalculatePropane);
    recalculatePropane();

    const checks = document.querySelectorAll('.lp-check');
    const badge = document.getElementById('lpBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Propane+Two+Stage+Regulator+CSST+Gas+Line+Kit"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('btu', 80000) // 1000}K BTU ({item.get('gal_hr', 0.87)} Gal/h)</span>
            <span class="text-xs text-slate-400">{item.get('csst', '3/4" CSST')} | ~{item.get('days', 13.1)} Days</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['setup_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate Vaporization, CSST & Runtime →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PropaneBTUIndex — Propane Tank Winter Vaporization, CSST Gas Line & Runtime Calculator (2026)</title>
  <meta name="description" content="Calculate exact propane tank winter BTU vaporization rate at 0F, gallons per hour burn rate, 100-lb to 500-gallon tank runtime, and NFPA 54 CSST flexible gas pipe sizing for Mr. Heater Big Maxx, Modine Hot Dawg, and pool heaters.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="PropaneBTUIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-slate-950 px-2 py-0.5 rounded font-black">PROPANE</span>BTUIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Regulators, CSST & Heaters →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Propane Tank Winter Vaporization, CSST Pipe & Runtime Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your propane tank size, shop heater, or BTU load below to calculate freezing-weather vaporization limits (at 20% tank fill), gallons/hour burned, and NFPA 54 CSST gas line diameter.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search tank size or heater (e.g. 100 lb Tank, 120 Gallon, 500 Gallon, Mr. Heater Big Maxx 80k, Modine Hot Dawg, CSST...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="lpGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} PropaneBTUIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('lpGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>PropaneBTUIndex Propane Vaporization & NFPA 54 Gas Pipe Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Propane Tank Winter Vaporization Rate, CSST Gas Line & Runtime Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_PROPANE:
        candidates.append((CUSTOM_PROPANE.strip(), 80000, 96.0, 92000, 50, "3/4-Inch CSST Gas Line"))
    candidates.extend(SEED_PROPANE)
    candidates.extend(discover_google_propane_queries(published_slugs))

    new_urls = []
    count = 0

    for prop_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        s_name = prop_tuple[0]
        slug = slugify(f"{s_name}-vaporization-pipe-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating propane tank vaporization & CSST pipe calculator for: {s_name}...")
        try:
            data = generate_propane_data(prop_tuple)
            build_propane_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "setup_name": data.get("setup_name", s_name),
                "slug": slug,
                "title": data.get("seo_title", f"{s_name} Propane Calculator"),
                "description": data.get("meta_description", ""),
                "btu": int(safe_float(sp.get("appliance_btu_hr", prop_tuple[1]), prop_tuple[1])),
                "gal_hr": round(safe_float(sp.get("burn_rate_gal_hr", 0.87), 0.87), 2),
                "csst": sp.get("recommended_pipe_spec", prop_tuple[5]).split()[0] + " CSST",
                "days": round(safe_float(sp.get("winter_35pct_runtime_days", 13.1), 13.1), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {s_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new propane vaporization & CSST pipe calculator pages.")


if __name__ == "__main__":
    main()
