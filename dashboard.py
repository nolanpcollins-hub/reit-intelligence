"""
dashboard.py
US REIT Intelligence Engine — Full Universe Coverage
Executive-grade platform for Fund Supervisor, PM, and CIO.
Covers 130+ REITs across 13 sectors.
Run: streamlit run dashboard.py
"""

import os
import sqlite3
import urllib.parse

import datetime
import io

import feedparser
import pandas as pd
import requests
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ─── Constants ────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_intelligence.db")

REIT_SECTORS: dict[str, list[str]] = {
    "Apartment":        ["AVB", "EQR", "ESS", "UDR", "MAA", "CPT", "IRT", "CSR", "NXRT", "BRT"],
    "Alt Housing":      ["INVH", "AMH", "MRP", "SUI", "ELS", "UMH"],
    "Industrial":       ["PLD", "EGP", "REXR", "FR", "TRNO", "STAG", "LXP", "ILPT", "COLD", "LINE"],
    "Healthcare":       ["WELL", "VTR", "AHR", "DHC", "JAN", "OHI", "CTRE", "SBRA", "NHI", "LTC",
                         "DOC", "ARE", "HR", "MPT", "SILA", "UHT", "CHCT", "XRN"],
    "Specialty":        ["LAMR", "OUT", "AMT", "CCI", "SBAC", "IIPR", "FPI"],
    "Data Centers":     ["EQIX", "DLR", "IRM"],
    "Shopping Centers": ["KIM", "FRT", "BRX", "KRG", "UE", "CTO", "REG", "PECO", "IVT",
                         "AKR", "CURB", "WSR", "BFS", "SITC"],
    "Mall":             ["SPG", "MAC", "SKT", "CBL"],
    "Self Storage":     ["PSA", "EXR", "CUBE", "NSA", "SMA"],
    "Hotel":            ["HST", "RHP", "PK", "DRH", "SHO", "PEB", "XHR", "APLE", "RLJ", "SVC", "CLDT", "BHR"],
    "Office":           ["BXP", "JBGS", "VNO", "SLG", "ESRT", "CUZ", "HIW", "PDM", "KRC", "DEI",
                         "AAT", "HPP", "CDP", "DEA", "BDN"],
    "Diversified":      ["GOOD", "ALX", "AHRT", "LAND", "NXDT", "PKST"],
    "Timber":           ["RYN", "WY"],
}

ALL_TICKERS: list[str] = [t for tickers in REIT_SECTORS.values() for t in tickers]

TICKER_NAMES: dict[str, str] = {
    # Apartment
    "AVB":  "AvalonBay Communities",
    "EQR":  "Equity Residential",
    "ESS":  "Essex Property Trust",
    "UDR":  "UDR Inc.",
    "MAA":  "Mid-America Apartment",
    "CPT":  "Camden Property Trust",
    "IRT":  "Independence Realty Trust",
    "CSR":  "Centerspace",
    "NXRT": "NexPoint Residential Trust",
    "BRT":  "BRT Realty Trust",
    # Alt Housing
    "INVH": "Invitation Homes",
    "AMH":  "American Homes 4 Rent",
    "MRP":  "Millrose Properties",
    "SUI":  "Sun Communities",
    "ELS":  "Equity LifeStyle Properties",
    "UMH":  "UMH Properties",
    # Industrial
    "PLD":  "Prologis",
    "EGP":  "EastGroup Properties",
    "REXR": "Rexford Industrial Realty",
    "FR":   "First Industrial Realty Trust",
    "TRNO": "Terreno Realty",
    "STAG": "STAG Industrial",
    "LXP":  "LXP Industrial Trust",
    "ILPT": "Industrial Logistics Properties Trust",
    "COLD": "Americold Realty Trust",
    "LINE": "Lineage",
    # Healthcare
    "WELL": "Welltower",
    "VTR":  "Ventas",
    "AHR":  "American Healthcare REIT",
    "DHC":  "Diversified Healthcare Trust",
    "JAN":  "Janus Living",
    "OHI":  "Omega Healthcare Investors",
    "CTRE": "CareTrust REIT",
    "SBRA": "Sabra Health Care REIT",
    "NHI":  "National Health Investors",
    "LTC":  "LTC Properties",
    "DOC":  "Healthpeak Properties",
    "ARE":  "Alexandria Real Estate Equities",
    "HR":   "Healthcare Realty Trust",
    "MPT":  "Medical Properties Trust",
    "SILA": "Sila Realty Trust",
    "UHT":  "Universal Health Realty Income Trust",
    "CHCT": "Community Healthcare Trust",
    "XRN":  "Chiron Real Estate",
    # Specialty
    "LAMR": "Lamar Advertising",
    "OUT":  "Outfront Media",
    "AMT":  "American Tower",
    "CCI":  "Crown Castle",
    "SBAC": "SBA Communications",
    "IIPR": "Innovative Industrial Properties",
    "FPI":  "Forum Pacific",
    # Data Centers
    "EQIX": "Equinix",
    "DLR":  "Digital Realty Trust",
    "IRM":  "Iron Mountain",
    # Shopping Centers
    "KIM":  "Kimco Realty",
    "FRT":  "Federal Realty Investment Trust",
    "BRX":  "Brixmor Property Group",
    "KRG":  "Kite Realty Group Trust",
    "UE":   "Urban Edge Properties",
    "CTO":  "CTO Realty Growth",
    "REG":  "Regency Centers",
    "PECO": "Phillips Edison & Company",
    "IVT":  "InvenTrust Properties",
    "AKR":  "Acadia Realty Trust",
    "CURB": "Curbline Properties",
    "WSR":  "Whitestone REIT",
    "BFS":  "Saul Centers",
    "SITC": "SITE Centers",
    # Mall
    "SPG":  "Simon Property Group",
    "MAC":  "Macerich",
    "SKT":  "Tanger",
    "CBL":  "CBL & Associates Properties",
    # Self Storage
    "PSA":  "Public Storage",
    "EXR":  "Extra Space Storage",
    "CUBE": "CubeSmart",
    "NSA":  "National Storage Affiliates",
    "SMA":  "SmartStop Self Storage REIT",
    # Hotel
    "HST":  "Host Hotels & Resorts",
    "RHP":  "Ryman Hospitality Properties",
    "PK":   "Park Hotels & Resorts",
    "DRH":  "DiamondRock Hospitality",
    "SHO":  "Sportshero",
    "PEB":  "Pebblebrook Hotel Trust",
    "XHR":  "Xenia Hotels & Resorts",
    "APLE": "Apple Hospitality REIT",
    "RLJ":  "RLJ Lodging Trust",
    "SVC":  "Service Properties Trust",
    "CLDT": "Chatham Lodging Trust",
    "BHR":  "Braemar Hotels & Resorts",
    # Office
    "BXP":  "BXP Inc.",
    "JBGS": "JBG SMITH Properties",
    "VNO":  "Vornado Realty Trust",
    "SLG":  "SL Green Realty",
    "ESRT": "Empire State Realty Trust",
    "CUZ":  "Cousins Properties",
    "HIW":  "Highwoods Properties",
    "PDM":  "Piedmont Realty Trust",
    "KRC":  "Kilroy Realty",
    "DEI":  "Douglas Emmett",
    "AAT":  "AATech SpA SB",
    "HPP":  "Hudson Pacific Properties",
    "CDP":  "COPT Defense Properties",
    "DEA":  "Easterly Government Properties",
    "BDN":  "Brandywine Realty Trust",
    # Diversified
    "GOOD": "Gladstone Commercial",
    "ALX":  "Alexander's",
    "AHRT": "AH Realty Trust",
    "LAND": "Land Securities Group",
    "NXDT": "NexPoint Diversified Real Estate Trust",
    "PKST": "Peakstone Realty Trust",
    # Timber
    "RYN":  "Rayonier",
    "WY":   "Weyerhaeuser",
}

RISK_COLORS = {"Critical": "#FF4B4B", "Moderate": "#FFA500", "Low/Stable": "#21C55D"}

SOL_COLORS = {
    "Active Enforced":    "#FF4B4B",
    "Pending Vote":       "#FFA500",
    "Developing Ballot":  "#C9A84C",
    "Defeated/Preempted": "#21C55D",
}

# Baseline sentiment for ALL 50 states (used for choropleth when no DB row exists).
# Based on known preemption laws, active rent control, and legislative trajectory.
STATE_BASELINE = {
    "AK": 0.60, "AL": 0.65, "AR": 0.68, "AZ": -0.38, "CA": -0.82,
    "CO": -0.42, "CT": -0.18, "DE": 0.28, "FL": 0.80, "GA": -0.22,
    "HI": -0.30, "IA": 0.62, "ID": 0.68, "IL": -0.35, "IN": 0.65,
    "KS": 0.68, "KY": 0.62, "LA": 0.65, "MA": -0.55, "MD": -0.55,
    "ME": 0.18, "MI": 0.55, "MN": -0.58, "MO": 0.62, "MS": 0.68,
    "MT": 0.62, "NC": 0.68, "ND": 0.55, "NE": 0.58, "NH": 0.30,
    "NJ": -0.60, "NM": -0.22, "NV": 0.62, "NY": -0.62, "OH": 0.58,
    "OK": 0.68, "OR": -0.58, "PA": -0.15, "RI": -0.12, "SC": 0.65,
    "SD": 0.58, "TN": 0.68, "TX": 0.72, "UT": 0.48, "VA": 0.15,
    "VT": -0.18, "WA": -0.52, "WI": 0.58, "WV": 0.62, "WY": 0.72,
}

ALL_STATES = sorted(STATE_BASELINE.keys())

# Structured ballot supplement data (signature counts, litigation, candidate info)
BALLOT_SUPPLEMENTS = {
    "Cambridge": {
        "type": "ballot",
        "signatures_collected": 8400,
        "signatures_required": 5000,
        "deadline": "Filed — November 2026 ballot",
        "polling": "58% support (Suffolk University, March 2026)",
        "litigation": "Greater Boston Real Estate Board — Home Rule Amendment challenge filed",
        "litigation_risk": "High",
        "next_milestone": "Cambridge Election Commission title review, August 2026",
    },
    "Phoenix": {
        "type": "ballot",
        "signatures_collected": 142000,
        "signatures_required": 237645,
        "deadline": "July 3, 2026",
        "polling": "54% support (OH Predictive Insights, April 2026)",
        "litigation": "Arizona Multihousing Association — title & summary challenge, Maricopa Superior Court",
        "litigation_risk": "Medium",
        "next_milestone": "Signature drive close-out: July 3, 2026",
    },
    "Atlanta": {
        "type": "candidate",
        "candidate": "Councilwoman Keisha Dorsey",
        "office": "Atlanta Mayor",
        "election_date": "November 3, 2026",
        "polling": "38% (leading) — Atlanta Journal-Constitution, May 2026",
        "stance": "Pro-stabilization study commission; not a direct rent control advocate",
        "endorsements": "SEIU Local 32BJ, Atlanta Progressive Caucus, DSA ATL",
        "opposition": "Atlanta Apartment Association, NMHC, Georgia Chamber of Commerce",
        "tickers": "MAA, CPT, INVH",
        "risk_if_elected": "Study commission precursor to state preemption repeal attempt in 2027",
    },
}

# ─── Power & Grid State Baseline ─────────────────────────────────────────────

POWER_GRID_STATES: dict[str, dict] = {
    # ── Hub states: detailed 2026 entries ────────────────────────────────────
    "VA": {
        "name": "Virginia",
        "grid_operator": "PJM Interconnection",
        "power_outlook": (
            "PJM faces high bottleneck risk in Northern Virginia due to massive hyperscale "
            "campus buildout (Loudoun County 'Data Center Alley'). SB 1015 (2024) requires "
            "new data centers >5MW to demonstrate green backup power or lose property tax "
            "incentive. Dominion Energy capacity queue backlog exceeds 35 GW. HB 1761 (2025) "
            "ratepayer protection framework requires large loads to fund proportional grid "
            "upgrade costs. Interconnection wait times averaging 4–6 years."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "SB 1015 (2024) active: data centers must use renewable backup or forfeit tax "
            "credits. HB 1761 (2025) ratepayer protection: large loads fund proportional "
            "grid upgrade costs. VSCC reviewing utility rate cases annually."
        ),
        "ratepayer_bill": True,
        "risk_level": "High",
        "key_reits": ["EQIX", "DLR", "IRM"],
    },
    "TX": {
        "name": "Texas",
        "grid_operator": "ERCOT",
        "power_outlook": (
            "ERCOT operates as an island grid with strong renewable capacity (wind + solar) "
            "but significant volatility during peak demand events. SB 6 (2023) requires "
            "mandatory large-load registration for facilities >75MW before grid "
            "interconnection. New capacity market rules (PCM) being implemented 2024–2026. "
            "Dallas/Fort Worth, San Antonio, and Austin metros are primary buildout zones. "
            "Behind-the-meter solar and on-site generation increasingly required."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "SB 6 (2023): mandatory large-load registration for facilities >75MW before "
            "interconnection. PUCT Rule §25.55 amended requiring behind-the-meter resilience "
            "plans. No moratorium; business-friendly but ERCOT grid stress events create "
            "headline risk. ERCOT PCM transition may increase power costs 8–15% by 2027."
        ),
        "ratepayer_bill": False,
        "risk_level": "High",
        "key_reits": ["EQIX", "DLR"],
    },
    "OH": {
        "name": "Ohio",
        "grid_operator": "PJM / MISO (split territory)",
        "power_outlook": (
            "Emerging AI hub with Columbus metro growing rapidly. HB 315 (2025) Ratepayer "
            "Protection Act: tech companies with loads >10MW must contribute directly to "
            "grid infrastructure costs rather than socializing costs across all ratepayers. "
            "AEP Ohio and FirstEnergy serving primary buildout areas. Columbus designated "
            "'AI Corridor' by Governor's office. PUCO implementing new rate structures."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "HB 315 (2025) — Ratepayer Protection Act: large loads >10MW must fund grid "
            "infrastructure costs directly. PUCO reviewing rate structure. No construction "
            "moratorium. Columbus AI Corridor designation attracting hyperscale investment "
            "despite new cost-allocation rules."
        ),
        "ratepayer_bill": True,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR", "IRM"],
    },
    "NY": {
        "name": "New York",
        "grid_operator": "NYISO",
        "power_outlook": (
            "NYC under a 12-month construction moratorium on new data centers exceeding "
            "7.5MW within the five boroughs, effective Q2 2025. Permitting reforms require "
            "exhaustive grid impact studies. Upstate NY (Buffalo/Albany) remains viable. "
            "Con Edison grid capacity in Manhattan extremely constrained; average "
            "interconnection wait 5–8 years. State SB 7768 pending — would extend "
            "moratorium statewide and require 100% renewable for new data centers."
        ),
        "dc_hub": True,
        "moratorium": True,
        "legislative_status": (
            "NYC Admin Code §28-101 amended: 12-month moratorium on data center permits "
            ">7.5MW in NYC boroughs (Q2 2025–Q2 2026). State SB 7768 pending: would extend "
            "moratorium statewide and require 100% renewable energy for new facilities. "
            "NYSPSC reviewing Con Edison capacity allocation rules."
        ),
        "ratepayer_bill": False,
        "risk_level": "High",
        "key_reits": ["EQIX", "DLR"],
    },
    "GA": {
        "name": "Georgia",
        "grid_operator": "Southern Company / Georgia Power",
        "power_outlook": (
            "Hot growth market (Atlanta metro) with Georgia Power under pressure from "
            "hyperscale demand. HB 1192 (2024) eliminated automatic data center tax "
            "incentives unless facility uses green backup power (battery storage or "
            "on-site renewable). Georgia Power Integrated Resource Plan amended to add "
            "8.6 GW new capacity by 2031. Vogtle nuclear expansion provides baseload "
            "stability. Generally favorable regulatory environment."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "HB 1192 (2024): data center equipment tax exemptions now conditional on green "
            "backup power certification. DOR Rule 560-12-2-.111 updated. No moratorium. "
            "Georgia PSC approved Georgia Power capacity expansion including new gas "
            "peakers and battery storage."
        ),
        "ratepayer_bill": False,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR", "IRM"],
    },
    "MD": {
        "name": "Maryland",
        "grid_operator": "PJM Interconnection",
        "power_outlook": (
            "Montgomery County and Prince George's County data center corridor adjacent "
            "to Northern Virginia. SB 628 (2025) mandated Clean Energy Grid Study "
            "examining ratepayer impact of large-load data centers. BGE and Pepco "
            "(Exelon utilities) facing interconnection queue congestion. HB 933 (2025) "
            "ratepayer protection framework requires large loads >20MW to submit economic "
            "impact study before interconnection."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "SB 628 (2025): Maryland PSC mandated to complete Clean Energy Grid Study by "
            "Jan 2026. HB 933 (2025): large loads >20MW must submit economic impact study "
            "before interconnection approval. Study results pending — potential for "
            "additional cost-allocation rules in 2026 legislative session."
        ),
        "ratepayer_bill": True,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR"],
    },
    "OK": {
        "name": "Oklahoma",
        "grid_operator": "SPP (Southwest Power Pool)",
        "power_outlook": (
            "Strong wind power capacity (top 3 US wind state) makes Oklahoma attractive "
            "for renewable PPAs. SB 1488 (2024) enacted an 18-month moratorium on new "
            "facilities >100MW pending grid impact review. SPP studying large-load "
            "integration. Tulsa and Oklahoma City metros have smaller existing campuses. "
            "Wind PPAs remain available for facilities under the 100MW threshold."
        ),
        "dc_hub": True,
        "moratorium": True,
        "legislative_status": (
            "SB 1488 (2024): 18-month moratorium on construction permits for data center "
            "facilities exceeding 100MW aggregate load. OCC (Corporation Commission) "
            "conducting grid impact study due Q3 2026. Wind energy PPAs remain available "
            "for facilities under 100MW threshold."
        ),
        "ratepayer_bill": False,
        "risk_level": "High",
        "key_reits": ["EQIX"],
    },
    "CA": {
        "name": "California",
        "grid_operator": "CAISO",
        "power_outlook": (
            "Strictest grid integration requirements in the US. AB 205 (2022) requires "
            "on-site backup generators meet Tier 4 emissions standards and limits runtime "
            "hours. CAISO grid already strained; new data center interconnection requests "
            "face mandatory grid impact studies and 6–9 year wait times in Bay Area / LA. "
            "CPUC mandating renewable integration for all large commercial loads. Bay Area "
            "county planning commissions imposing local moratoriums on new campuses."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "AB 205 (2022): strict backup generator emissions rules limiting diesel "
            "runtime. SB 100 (100% clean electricity by 2045) drives renewable PPA "
            "requirements for large loads. CPUC Rulemaking R.20-05-003 governing data "
            "center grid integration. Bay Area counties imposing local moratoriums on "
            "new campuses pending EIR studies."
        ),
        "ratepayer_bill": False,
        "risk_level": "High",
        "key_reits": ["EQIX", "DLR"],
    },
    "IL": {
        "name": "Illinois",
        "grid_operator": "MISO (Midcontinent ISO)",
        "power_outlook": (
            "Chicago metro is an established data center hub with competitive PPA market. "
            "Data center tax exemptions under review by Illinois General Assembly "
            "(SB 2400, 2025). ComEd (Exelon) managing MISO interconnection queue with "
            "growing AI campus load. Illinois Future Energy Jobs Act (FEJA) supporting "
            "renewable buildout for large loads. No moratorium risk currently."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "SB 2400 (2025): data center sales tax exemption under review — potential "
            "sunset for facilities not meeting green energy benchmarks. ICC Rate Case "
            "pending for ComEd grid upgrade cost allocation. No moratorium; political "
            "risk is legislative narrowing of tax benefits."
        ),
        "ratepayer_bill": False,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR"],
    },
    "NV": {
        "name": "Nevada",
        "grid_operator": "NV Energy",
        "power_outlook": (
            "Strong solar PPA availability in southern Nevada. Las Vegas metro has "
            "established data center presence. NV Energy's Renewable Choice Program "
            "enables large loads to contract directly for renewable energy (AB 356, 2023). "
            "Gaming district cooling infrastructure competes for water and electrical "
            "capacity. Northern Nevada (Reno) is secondary hub. Low legislative risk."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "AB 356 (2023): expanded Renewable Choice Program enabling direct renewable "
            "PPAs for loads >1MW. No moratorium or ratepayer protection bill active. "
            "PUCN reviewing NV Energy integrated resource plan. Water usage (evaporative "
            "cooling) subject to Clark County permitting scrutiny."
        ),
        "ratepayer_bill": False,
        "risk_level": "Low",
        "key_reits": ["EQIX", "DLR"],
    },
    "AZ": {
        "name": "Arizona",
        "grid_operator": "APS (Arizona Public Service) / SRP",
        "power_outlook": (
            "Phoenix metro faces permitting delays and water cooling concerns for large "
            "desert buildout. APS interconnection queue growing; summer peak demand "
            "constraints limit available capacity. APS and SRP both have solar PPA "
            "programs but water scarcity forces air-cooled or closed-loop designs at "
            "significant cost premium. HB 2821 (2025) mandates water usage disclosure "
            "for large data centers."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "No state-level moratorium. ACC (Arizona Corporation Commission) reviewing "
            "large commercial interconnection standards. Maricopa County Water Resource "
            "Planning Commission imposing water-use impact requirements on data center "
            "permits >500,000 sq ft. HB 2821 (2025): mandatory water usage disclosure "
            "for large data centers."
        ),
        "ratepayer_bill": False,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR"],
    },
    "WA": {
        "name": "Washington",
        "grid_operator": "BPA (Bonneville Power Administration)",
        "power_outlook": (
            "Abundant hydropower from BPA makes Washington one of the lowest-cost clean "
            "energy markets for data centers. Eastern Washington counties (Grant, Douglas, "
            "Chelan) have hosted hyperscale campuses for 15+ years. Grant County PUD "
            "enacted temporary review period (2024–2025) for new large-load requests. "
            "SB 5722 (2025) studying data center energy and water impacts in Columbia Basin."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "No statewide moratorium. Grant County PUD (GCPUD) enacted temporary review "
            "period for new large-load interconnection (2024–2025). SB 5722 (2025): study "
            "on data center energy and water impacts in Columbia Basin. Seattle metro "
            "served by Puget Sound Energy with competitive rates but limited new capacity."
        ),
        "ratepayer_bill": False,
        "risk_level": "Low",
        "key_reits": ["EQIX"],
    },
    "OR": {
        "name": "Oregon",
        "grid_operator": "BPA / PacifiCorp",
        "power_outlook": (
            "The Dalles (Hood River County) is a major hyperscale hub. BPA hydropower "
            "provides clean, low-cost baseload. PacifiCorp serves central/eastern Oregon. "
            "Oregon PUC reviewing large-load cost allocation (HB 3141, 2025). No "
            "moratorium but local opposition to further buildout growing in The Dalles "
            "area. Hood River County updated land use rules for environmental review."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "HB 3141 (2025): Oregon PUC directed to study ratepayer impacts of large "
            "commercial loads and report by Jan 2026. No moratorium enacted. Hood River "
            "County planning commission updated land use rules requiring enhanced "
            "environmental review for data centers >250,000 sq ft."
        ),
        "ratepayer_bill": False,
        "risk_level": "Low",
        "key_reits": ["EQIX"],
    },
    "NJ": {
        "name": "New Jersey",
        "grid_operator": "PJM Interconnection",
        "power_outlook": (
            "Northern New Jersey (transit zone) faces severe grid constraints. PJM "
            "Northern NJ load pocket has limited new capacity; interconnection queue "
            "heavily backlogged. Growing ratepayer push as PSE&G rate cases include "
            "large-load infrastructure costs (A-3826, 2025). Proximity to NYC financial "
            "district drives demand despite higher costs."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "A-3826 (2025): NJ BPU directed to study data center grid impacts and cost "
            "allocation options. NJBPU rate proceedings for PSE&G include large-load "
            "rider discussions. No moratorium. Ratepayer advocacy groups petitioning "
            "BPU to require data center cost segregation in utility rate filings."
        ),
        "ratepayer_bill": True,
        "risk_level": "Moderate",
        "key_reits": ["EQIX", "DLR"],
    },
    "NC": {
        "name": "North Carolina",
        "grid_operator": "Duke Energy Carolinas / Progress",
        "power_outlook": (
            "Charlotte and Raleigh-Durham metros growing as data center hubs. Duke Energy "
            "filing expanded capacity plans to serve hyperscale demand. NCUC reviewing "
            "rate structures. State offers competitive tax incentives without green energy "
            "condition. Generally favorable regulatory environment. HB 600 (2025) data "
            "center incentive expansion pending."
        ),
        "dc_hub": True,
        "moratorium": False,
        "legislative_status": (
            "No moratorium or ratepayer protection bill. NCUC Docket E-7, Sub 1214: "
            "Duke Energy rate case includes large-load grid upgrade cost allocation review. "
            "HB 600 (2025): data center incentive expansion pending — extending sales tax "
            "exemption to include colocation operators."
        ),
        "ratepayer_bill": False,
        "risk_level": "Low",
        "key_reits": ["EQIX", "DLR"],
    },
    # ── Non-hub states: default template ─────────────────────────────────────
    "AK": {
        "name": "Alaska",
        "grid_operator": "GVEA / ML&P (Railbelt Grid)",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "AL": {
        "name": "Alabama",
        "grid_operator": "Southern Company / Alabama Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "AR": {
        "name": "Arkansas",
        "grid_operator": "Entergy Arkansas / SWEPCO",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "CO": {
        "name": "Colorado",
        "grid_operator": "Xcel Energy / Black Hills",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "CT": {
        "name": "Connecticut",
        "grid_operator": "Eversource / UI",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "DE": {
        "name": "Delaware",
        "grid_operator": "PJM / Delmarva Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "FL": {
        "name": "Florida",
        "grid_operator": "FPL / Duke Energy Florida",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "HI": {
        "name": "Hawaii",
        "grid_operator": "HECO / HELCO",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "IA": {
        "name": "Iowa",
        "grid_operator": "MidAmerican Energy / Alliant Energy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "ID": {
        "name": "Idaho",
        "grid_operator": "Idaho Power / PacifiCorp",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "IN": {
        "name": "Indiana",
        "grid_operator": "AES Indiana / Duke Energy Indiana",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "KS": {
        "name": "Kansas",
        "grid_operator": "Evergy / Westar Energy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "KY": {
        "name": "Kentucky",
        "grid_operator": "Louisville Gas & Electric / Kentucky Utilities",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "LA": {
        "name": "Louisiana",
        "grid_operator": "Entergy Louisiana / CLECO",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MA": {
        "name": "Massachusetts",
        "grid_operator": "Eversource / National Grid",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "ME": {
        "name": "Maine",
        "grid_operator": "Central Maine Power / Versant",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MI": {
        "name": "Michigan",
        "grid_operator": "DTE Energy / Consumers Energy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MN": {
        "name": "Minnesota",
        "grid_operator": "Xcel Energy / Minnesota Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MO": {
        "name": "Missouri",
        "grid_operator": "Ameren Missouri / Evergy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MS": {
        "name": "Mississippi",
        "grid_operator": "Entergy Mississippi / Mississippi Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "MT": {
        "name": "Montana",
        "grid_operator": "NorthWestern Energy / BPA",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "ND": {
        "name": "North Dakota",
        "grid_operator": "Xcel Energy / MDU Resources",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "NE": {
        "name": "Nebraska",
        "grid_operator": "OPPD / LES / NPPD",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "NH": {
        "name": "New Hampshire",
        "grid_operator": "Eversource / NH Electric Co-op",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "NM": {
        "name": "New Mexico",
        "grid_operator": "PNM Resources / Xcel Energy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "PA": {
        "name": "Pennsylvania",
        "grid_operator": "PJM / PPL / PECO",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "RI": {
        "name": "Rhode Island",
        "grid_operator": "National Grid",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "SC": {
        "name": "South Carolina",
        "grid_operator": "Dominion Energy SC / Duke Energy SC",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "SD": {
        "name": "South Dakota",
        "grid_operator": "Xcel Energy / MDU Resources",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "TN": {
        "name": "Tennessee",
        "grid_operator": "TVA (Tennessee Valley Authority)",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "UT": {
        "name": "Utah",
        "grid_operator": "Rocky Mountain Power / PacifiCorp",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "VT": {
        "name": "Vermont",
        "grid_operator": "Green Mountain Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "WI": {
        "name": "Wisconsin",
        "grid_operator": "We Energies / Alliant Energy",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "WV": {
        "name": "West Virginia",
        "grid_operator": "Appalachian Power / Mon Power",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
    "WY": {
        "name": "Wyoming",
        "grid_operator": "Rocky Mountain Power / Black Hills",
        "power_outlook": "Stable Supply / Low Legislative Activity. No active moratorium or ratepayer protection bill. Standard utility interconnection timelines.",
        "dc_hub": False, "moratorium": False, "legislative_status": "No data-center-specific legislation active. Standard PUC oversight.",
        "ratepayer_bill": False, "risk_level": "Low", "key_reits": [],
    },
}

GRID_REIT_NARRATIVES: dict[tuple[str, str], str] = {
    ("VA", "EQIX"): (
        "Equinix operates its largest global campus concentration in Ashburn, VA (DC1–DC15+). "
        "SB 1015 green backup power requirement creates capex pressure for battery storage "
        "retrofits on new campus phases. PJM interconnection queue backlog of 35+ GW threatens "
        "timeline for new capacity additions. Near-term NOI impact: Neutral (existing campus "
        "unaffected); new build risk: Elevated. Pricing power benefits from supply scarcity."
    ),
    ("VA", "DLR"): (
        "Digital Realty's Ashburn campus (IAD portfolio) is the largest single-tenant hyperscale "
        "concentration in Northern Virginia. Ratepayer protection framework (HB 1761) requires DLR "
        "to fund grid upgrades proportionally — analysts estimate $15–40M per campus phase. "
        "High sensitivity to any PJM capacity market tightening or Dominion Energy rate case outcomes."
    ),
    ("VA", "IRM"): (
        "Iron Mountain data centers in Northern Virginia benefit from existing power contracts "
        "pre-dating SB 1015, limiting retrofit exposure vs greenfield competitors. IRM's "
        "colocation model partially insulates from direct grid cost liability. New build risk "
        "is low relative to hyperscale operators."
    ),
    ("TX", "EQIX"): (
        "Equinix Dallas campus (DA1–DA6) operates on ERCOT. SB 6 large-load registration applies "
        "to any campus expansion >75MW. Winter Storm Uri precedent requires battery storage "
        "redundancy for SLA compliance. ERCOT PCM (capacity market) transition may increase "
        "power costs 8–15% by 2027 per company guidance. Texas remains a core growth market."
    ),
    ("TX", "DLR"): (
        "Digital Realty has significant Dallas and San Antonio footprint. ERCOT grid volatility "
        "creates power cost variability — key earnings risk factor. Behind-the-meter solar "
        "partnerships mitigate but don't eliminate exposure. Management flagged Texas grid "
        "as top operational risk in 2025 10-K. Pivoting some Texas capacity to behind-the-meter."
    ),
    ("OH", "EQIX"): (
        "Equinix Columbus campus (CMH1–CMH3) in growing AI hub. HB 315 ratepayer protection "
        "means Equinix will directly fund grid upgrade costs — company estimates $10–25M "
        "additional capex per campus phase over 5-year horizon. Columbus AI Corridor incentive "
        "packages partly offset grid costs. Net impact: moderate capex headwind."
    ),
    ("OH", "DLR"): (
        "Digital Realty Columbus footprint benefits from Ohio's emerging AI corridor status. "
        "PJM/MISO split territory creates interconnection complexity but no active moratorium. "
        "HB 315 cost allocation adds capex overhead; watch 2026 capex guidance for Ohio-specific "
        "line items. Long-term outlook: positive given Columbus growth trajectory."
    ),
    ("OH", "IRM"): (
        "Iron Mountain's Ohio presence is primarily records management with limited hyperscale "
        "data center exposure. Low direct risk from HB 315 given smaller power footprint. "
        "Not a primary growth driver for IRM in the Ohio market."
    ),
    ("NY", "EQIX"): (
        "Equinix NYC campus (NY1–NY9) are existing facilities grandfathered before the 2025 "
        "moratorium. New campus development in NYC boroughs is halted during moratorium period. "
        "Equinix has pivoted expansion to Secaucus NJ and Ashburn VA. Moratorium creates "
        "competitive moat for existing NYC capacity — pricing power elevated significantly. "
        "State SB 7768 statewide extension is the key watch item."
    ),
    ("NY", "DLR"): (
        "Digital Realty limited new NYC development exposure due to moratorium. Existing Manhattan "
        "assets benefit from scarcity-driven pricing. DLR has redirected NY-area pipeline to "
        "New Jersey and Northern Virginia campuses. SB 7768 statewide extension would freeze "
        "competitive supply another year — net positive for existing operators."
    ),
    ("GA", "EQIX"): (
        "Equinix Atlanta campus (AT1–AT5) subject to HB 1192 green backup power certification "
        "for new phases. Battery storage retrofit requirement adds capex on expansion. Atlanta "
        "remains high-growth market; Georgia Power capacity expansion (8.6 GW by 2031) supports "
        "continued buildout. Tax incentive continuity preserved with green certification."
    ),
    ("GA", "DLR"): (
        "Digital Realty Atlanta footprint faces HB 1192 green backup power certification requirement. "
        "DLR has announced renewable energy agreements with Georgia Power covering new Atlanta campus "
        "phases, aligning with existing sustainability commitments. Risk assessment: Moderate — "
        "manageable given DLR's renewable energy portfolio."
    ),
    ("GA", "IRM"): (
        "Iron Mountain Atlanta data centers benefit from Georgia's hot growth market and Georgia "
        "Power capacity expansion. HB 1192 green backup requirement aligns with IRM's stated "
        "sustainability goals. Colocation focus means tax incentive exposure is smaller than "
        "hyperscale operators. Net risk: Low."
    ),
    ("MD", "EQIX"): (
        "Equinix has limited direct Maryland footprint relative to its Northern Virginia presence. "
        "PJM interconnection congestion in the DC-Maryland corridor is shared risk. SB 628 grid "
        "study results (due Jan 2026) may create additional cost allocation requirements that "
        "affect Maryland campus expansion economics."
    ),
    ("MD", "DLR"): (
        "Digital Realty Maryland properties (Beltsville/Rockville corridor) subject to HB 933 "
        "large-load impact study requirement for interconnection >20MW. Ratepayer framework "
        "creates predictability but adds $5–15M per campus to interconnection costs. Watch "
        "2026 Maryland legislative session for cost-allocation rule formalization."
    ),
    ("OK", "EQIX"): (
        "Equinix has minimal Oklahoma footprint. SB 1488 moratorium on >100MW facilities prevents "
        "any large campus development until OCC study completes (Q3 2026). Wind PPA availability "
        "is attractive for future development post-moratorium. No near-term NOI impact given "
        "small existing exposure."
    ),
    ("CA", "EQIX"): (
        "Equinix Silicon Valley campus (SV1–SV15) is its largest global cluster by revenue. "
        "AB 205 backup generator restrictions require significant battery storage investment. "
        "CAISO 6–9 year interconnection wait means Silicon Valley expansion pipeline is "
        "effectively frozen for new builds. Existing assets benefit from supply scarcity — "
        "pricing power elevated. Key risk: CPUC renewable mandate cost escalation 3–5% annually."
    ),
    ("CA", "DLR"): (
        "Digital Realty Bay Area and LA footprint faces AB 205 and CAISO constraints. DLR has "
        "signaled prioritizing Texas and Virginia for new North American capacity vs California, "
        "reflecting grid risk-adjusted returns. California assets priced at premium reflecting "
        "supply scarcity but carry elevated regulatory execution risk on any new build."
    ),
    ("IL", "EQIX"): (
        "Equinix Chicago campus (CH1–CH8) benefits from MISO competitive PPA market and established "
        "hyperscale presence. SB 2400 tax exemption review is a watch item — loss of exemption "
        "could increase operating costs 3–5% per analyst estimates. No moratorium risk; Chicago "
        "remains Tier 1 market. Existing contracts likely grandfathered."
    ),
    ("IL", "DLR"): (
        "Digital Realty Chicago footprint leverages MISO grid and competitive power market. "
        "SB 2400 tax exemption sustainability under review is manageable — existing contracts "
        "grandfathered, new builds may face higher effective tax rates post-2026. Net impact: "
        "low to moderate depending on legislative outcome."
    ),
    ("NV", "EQIX"): (
        "Equinix Las Vegas campus (LV1–LV2) benefits from NV Energy solar PPA availability "
        "and AB 356 Renewable Choice Program. Low moratorium and ratepayer risk. Gaming district "
        "electrical constraints limit expansion density in central Las Vegas. Reno (northern NV) "
        "offers better greenfield economics. Overall: favorable regulatory environment."
    ),
    ("NV", "DLR"): (
        "Digital Realty Nevada presence is modest relative to Virginia/Texas footprint. "
        "Favorable regulatory environment and low grid risk. Water cooling constraints in desert "
        "environment increase cooling capex for large expansion. Long-term: water scarcity "
        "is a tail risk, but manageable with air-cooled or closed-loop design."
    ),
    ("AZ", "EQIX"): (
        "Equinix Phoenix campus (PHX1–PHX3) faces APS permitting delays and water scarcity "
        "constraints. Maricopa County water impact study required for new builds >500K sq ft. "
        "HB 2821 water disclosure adds administrative burden. No moratorium but permitting "
        "timeline risk: 18–30 months vs 12–18 months in Virginia or Texas."
    ),
    ("AZ", "DLR"): (
        "Digital Realty Phoenix footprint managed under water-conscious design requirements. "
        "Air-cooled or closed-loop systems add 10–15% capex premium vs evaporative cooling. "
        "Long-term Arizona water scarcity is a tail risk for large campus development beyond "
        "existing commitments. APS grid capacity generally adequate near-term."
    ),
    ("WA", "EQIX"): (
        "Equinix eastern Washington campus operations benefit from BPA hydropower — among the "
        "lowest-cost clean energy globally. Grant County PUD temporary review period (2024–2025) "
        "has limited immediate expansion but no formal moratorium enacted. Seattle presence "
        "benefits from Puget Sound Energy competitive rates. SB 5722 water/energy study to watch."
    ),
    ("OR", "EQIX"): (
        "Equinix The Dalles campus (PDX) operates on BPA hydropower with established infrastructure "
        "and long-term power agreements. HB 3141 PUC study adds regulatory uncertainty but no "
        "moratorium risk. Hood River County land use changes may slow permitting for new phases "
        "but existing campus operations are unaffected. Near-term: stable."
    ),
    ("NJ", "EQIX"): (
        "Equinix Secaucus campus (NY4–NY8) serves NYC market from PJM Northern NJ load pocket. "
        "Grid congestion is the primary constraint for expansion. A-3826 BPU study may create "
        "large-load cost allocation rules — potential $20–50M incremental capex risk for new "
        "capacity. Existing capacity benefits from NYC-driven demand with no viable alternative."
    ),
    ("NJ", "DLR"): (
        "Digital Realty NJ footprint faces PJM Northern NJ congestion constraints. Ratepayer "
        "advocacy may result in direct cost allocation for grid upgrades. Key strategic asset: "
        "transit zone location creates irreplaceable low-latency access to Wall Street and "
        "NYC financial services — demand inelastic despite higher grid costs."
    ),
    ("NC", "EQIX"): (
        "Equinix Charlotte campus (CLT) benefits from Duke Energy capacity expansion plan and "
        "no moratorium risk. Competitive state tax incentive environment without green energy "
        "condition. NCUC rate case (Docket E-7, Sub 1214) to watch for cost allocation outcome. "
        "Overall: favorable market with growth trajectory."
    ),
    ("NC", "DLR"): (
        "Digital Realty announced Raleigh-Durham expansion (RDU campus). Duke Energy capacity "
        "additions support growth. HB 600 data center incentive expansion bill would further "
        "improve economics. Low regulatory risk vs peer markets — NC is an emerging Tier 1 "
        "market for hyperscale buildout."
    ),
}

# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="REIT Regulatory Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ─── Import ─── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ─── Global ─── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    font-size: 15px !important;
}
.stApp { background-color: #06101E; color: #E2EBF6; }
.block-container { padding: 1.6rem 2.2rem 5rem 2.2rem !important; max-width: 100% !important; }
p { font-size: 0.95rem !important; line-height: 1.72 !important; color: #D8E8F6 !important; }

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background-color: #050D18 !important;
    border-right: 1px solid #182D48;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
[data-testid="stSidebarContent"] { padding: 0 1.1rem; }
[data-testid="stSidebar"] label {
    color: #7A9BBE !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* ─── Metric cards ─── */
[data-testid="metric-container"] {
    background: linear-gradient(140deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 12px;
    padding: 20px 24px !important;
}
[data-testid="stMetricValue"] {
    color: #C9A84C !important;
    font-size: 2.0rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricLabel"] {
    color: #6E90B2 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; color: #6E90B2 !important; }

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #050D18;
    gap: 4px;
    border-bottom: 2px solid #182D48;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background-color: #0B1A2D;
    color: #6E90B2;
    border-radius: 8px 8px 0 0;
    padding: 11px 24px;
    font-size: 0.90rem;
    font-weight: 600;
    border: 1px solid #182D48;
    border-bottom: none;
    transition: all 0.18s;
    letter-spacing: 0.01em;
}
.stTabs [data-baseweb="tab"]:hover { color: #D0DDF0 !important; background-color: #0F2035 !important; }
.stTabs [aria-selected="true"] {
    background-color: #142438 !important;
    color: #C9A84C !important;
    border-color: #2E5070 !important;
    border-bottom: 2px solid #C9A84C !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.6rem !important; }

/* ─── Buttons ─── */
.stButton > button {
    background: #0B1A2D !important;
    color: #C9A84C !important;
    border: 1px solid #3A5A20 !important;
    border-color: rgba(201,168,76,0.5) !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
    letter-spacing: 0.02em;
}
.stButton > button:hover {
    background: #C9A84C !important;
    color: #06101E !important;
    border-color: #C9A84C !important;
}

/* ─── Multiselect / Select ─── */
[data-baseweb="select"] { background-color: #0B1A2D !important; }
[data-baseweb="select"] div { color: #D8E8F6 !important; font-size: 0.88rem !important; }
[data-baseweb="tag"] { background-color: #1D3450 !important; color: #C9A84C !important; font-weight: 600 !important; }
[data-baseweb="menu"] { background-color: #0B1A2D !important; border: 1px solid #1D3450 !important; }
[data-baseweb="menu"] li { color: #D8E8F6 !important; font-size: 0.88rem !important; }
[data-baseweb="menu"] li:hover { background-color: #142438 !important; }

/* ─── Text inputs ─── */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background-color: #0B1A2D !important;
    color: #E2EBF6 !important;
    border: 1px solid #1D3450 !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: #C9A84C !important;
    box-shadow: 0 0 0 2px rgba(201,168,76,0.15) !important;
}
[data-testid="stTextInput"] label, [data-testid="stTextArea"] label {
    color: #6E90B2 !important; font-size: 0.78rem !important;
    font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important;
}

/* ─── Dataframe ─── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] th {
    background: #0B1A2D !important;
    color: #C9A84C !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stDataFrame"] td { color: #D8E8F6 !important; font-size: 0.88rem !important; }

/* ─── Expanders ─── */
details {
    background-color: #0B1A2D !important;
    border: 1px solid #1D3450 !important;
    border-radius: 10px !important;
    margin-bottom: 4px;
}
summary {
    color: #C8DAEA !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
    font-size: 0.91rem !important;
    letter-spacing: 0.01em;
}
summary:hover { color: #E8F0FA !important; }

/* ─── Progress ─── */
.stProgress > div > div { background: linear-gradient(90deg, #C9A84C, #E8C96A) !important; }
.stProgress > div { background-color: #1D3450 !important; border-radius: 99px !important; height: 8px !important; }

/* ─── Dividers ─── */
hr { border-color: #182D48 !important; margin: 1.4rem 0 !important; }

/* ─── Spinners / info ─── */
[data-testid="stSpinner"] p { color: #C9A84C !important; }

/* ─── Chat (inline inside column) ─── */
[data-testid="stChatMessage"] {
    background-color: #0B1A2D !important;
    border: 1px solid #1D3450 !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin-bottom: 8px !important;
}
[data-testid="stChatMessage"] p { font-size: 0.92rem !important; line-height: 1.68 !important; color: #D8E8F6 !important; }
[data-testid="stChatInput"] {
    background: #06101E !important;
    border-top: 2px solid #1D3450 !important;
    padding: 10px 16px !important;
}
[data-testid="stChatInput"] textarea {
    background-color: #0B1A2D !important;
    color: #E2EBF6 !important;
    border: 1.5px solid #1D3450 !important;
    border-radius: 12px !important;
    font-size: 0.93rem !important;
    padding: 10px 16px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #00FF88 !important;
    box-shadow: 0 0 0 3px rgba(0,255,136,0.1) !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #00DD77, #00AA55) !important;
    border-radius: 10px !important;
    border: none !important;
}

/* ─── Page header ─── */
.page-header { border-bottom: 2px solid #C9A84C; padding-bottom: 14px; margin-bottom: 24px; }
.page-header h1 {
    color: #EBF1FA;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 0 0 5px 0;
    letter-spacing: -0.02em;
}
.page-header p { color: #6E90B2 !important; font-size: 0.85rem !important; margin: 0; }

/* ─── Section titles ─── */
.section-title {
    color: #C9A84C;
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    border-bottom: 1px solid #182D48;
    padding-bottom: 7px;
    margin-bottom: 16px;
}

/* ─── Cards ─── */
.intel-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
    transition: border-color 0.18s, box-shadow 0.18s;
}
.intel-card:hover { border-color: #2E5070; box-shadow: 0 4px 24px rgba(0,0,0,0.3); }

.news-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-left: 4px solid #1D3450;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.news-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.35); }
.news-card.critical { border-left-color: #FF4B4B; }
.news-card.moderate { border-left-color: #FFA500; }
.news-card.stable   { border-left-color: #21C55D; }

.market-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 18px;
    transition: border-color 0.18s, box-shadow 0.18s;
}
.market-card:hover { border-color: #2E5070; box-shadow: 0 6px 30px rgba(0,0,0,0.35); }

/* ─── Audit quote ─── */
.audit-quote {
    background-color: #050D18;
    border-left: 4px solid #C9A84C;
    padding: 14px 18px;
    border-radius: 0 10px 10px 0;
    font-style: italic;
    color: #B8CEE8;
    font-size: 0.90rem;
    line-height: 1.75;
    margin: 12px 0;
}

/* ─── Table ─── */
.tbl-header {
    color: #C9A84C;
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 10px 8px;
    border-bottom: 2px solid #1D3450;
}
.tbl-cell {
    color: #D8E8F6;
    font-size: 0.90rem;
    padding: 12px 8px;
    border-bottom: 1px solid #111E2E;
    vertical-align: top;
    word-wrap: break-word;
    word-break: break-word;
    line-height: 1.55;
}

/* ─── Badges / chips ─── */
.sent-tag {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.sent-bearish { background: #3D0E0E; color: #FF7B7B; border: 1px solid rgba(255,75,75,0.3); }
.sent-bullish { background: #0A2E18; color: #34D973; border: 1px solid rgba(52,217,115,0.3); }
.sent-neutral { background: #152030; color: #7A9BBE; border: 1px solid rgba(122,155,190,0.3); }

.risk-tag {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.risk-critical { background: #2E0808; color: #FF5555; border: 1px solid rgba(255,75,75,0.3); }
.risk-moderate { background: #211400; color: #FFB020; border: 1px solid rgba(255,160,32,0.3); }
.risk-low      { background: #082214; color: #28D96A; border: 1px solid rgba(40,217,106,0.3); }

.ticker-chip {
    display: inline-block;
    background: #102030;
    color: #C9A84C;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.80rem;
    font-weight: 700;
    white-space: nowrap;
    margin: 2px;
    border: 1px solid rgba(201,168,76,0.3);
}

.sol-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.sol-active   { background: #2E0808; color: #FF5555; border: 1px solid rgba(255,75,75,0.3); }
.sol-pending  { background: #211400; color: #FFB020; border: 1px solid rgba(255,160,32,0.3); }
.sol-ballot   { background: #1E1800; color: #C9A84C; border: 1px solid rgba(201,168,76,0.3); }
.sol-defeated { background: #082214; color: #28D96A; border: 1px solid rgba(40,217,106,0.3); }

/* ─── Stat boxes ─── */
.stat-box {
    background: #050D18;
    border: 1px solid #1D3450;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.stat-box .stat-val { color: #C9A84C; font-size: 1.45rem; font-weight: 700; }
.stat-box .stat-lbl {
    color: #6E90B2; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.07em; margin-top: 3px;
}

/* ─── Floating AI robot button ─── */
@keyframes neon-pulse {
    0%   { box-shadow: 0 0 8px 2px rgba(0,255,136,0.7), 0 4px 20px rgba(0,0,0,0.6); }
    50%  { box-shadow: 0 0 22px 8px rgba(0,255,136,0.4), 0 4px 20px rgba(0,0,0,0.6); }
    100% { box-shadow: 0 0 8px 2px rgba(0,255,136,0.7), 0 4px 20px rgba(0,0,0,0.6); }
}
#ai-fab {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 99999;
    width: 62px;
    height: 62px;
    border-radius: 50%;
    background: linear-gradient(135deg, #00FF88 0%, #00BB55 100%);
    border: 2px solid rgba(0,255,136,0.6);
    cursor: pointer;
    font-size: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: neon-pulse 2.4s ease-in-out infinite;
    transition: transform 0.2s;
    text-decoration: none;
    line-height: 1;
}
#ai-fab:hover { transform: scale(1.14); }

/* ─── Chat panel ─── */
.chat-panel-wrap {
    background: linear-gradient(160deg, #070F1D 0%, #0B1A2D 100%);
    border: 1.5px solid #00CC66;
    border-radius: 18px;
    padding: 0;
    overflow: hidden;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 40px rgba(0,204,102,0.08);
}
.chat-panel-header {
    background: linear-gradient(90deg, #071A0F 0%, #0A2318 100%);
    border-bottom: 1px solid #00CC66;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.chat-panel-body { padding: 14px 16px 0 16px; max-height: 380px; overflow-y: auto; }

/* ─── Sig bar ─── */
.sig-bar-container { margin: 8px 0 14px 0; }
.sig-bar-label { font-size: 0.82rem; color: #6E90B2; margin-bottom: 4px; display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True)


# ─── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        # Auto-seed when deployed (e.g. Streamlit Community Cloud)
        try:
            import db_seeder
            db_seeder.main()
        except Exception:
            st.error(f"Database not found at `{DB_PATH}`. Run `python db_seeder.py` first.")
            st.stop()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM market_intelligence ORDER BY last_updated DESC", conn
    )
    conn.close()
    return df


df_all = load_data()


# ─── Live News Scraper ─────────────────────────────────────────────────────────

# Maps tickers to company names for better search results (one per sector to stay within RSS rate limits)
_TICKER_SEARCH_TERMS = {
    # Apartment
    "AVB":  "AvalonBay Communities REIT",
    "EQR":  "Equity Residential REIT",
    "ESS":  "Essex Property Trust REIT",
    "MAA":  "Mid-America Apartment REIT",
    "CPT":  "Camden Property Trust REIT",
    "UDR":  "UDR apartment REIT",
    # Alt Housing
    "INVH": "Invitation Homes single family rental REIT",
    "AMH":  "American Homes 4 Rent REIT",
    "SUI":  "Sun Communities manufactured housing REIT",
    # Industrial
    "PLD":  "Prologis industrial REIT logistics",
    "REXR": "Rexford Industrial Realty REIT",
    # Healthcare
    "WELL": "Welltower healthcare REIT",
    "ARE":  "Alexandria Real Estate Equities life science REIT",
    # Specialty
    "AMT":  "American Tower cell tower REIT",
    "IIPR": "Innovative Industrial Properties cannabis REIT",
    # Data Centers
    "EQIX": "Equinix data center REIT",
    "DLR":  "Digital Realty data center REIT",
    # Shopping Centers
    "KIM":  "Kimco Realty shopping center REIT",
    "REG":  "Regency Centers grocery anchored REIT",
    # Mall
    "SPG":  "Simon Property Group mall REIT",
    # Self Storage
    "PSA":  "Public Storage self storage REIT",
    # Hotel
    "HST":  "Host Hotels Resorts REIT",
    # Office
    "BXP":  "BXP Boston Properties office REIT",
    "SLG":  "SL Green Realty office REIT",
    # Diversified / Timber
    "WY":   "Weyerhaeuser timber REIT",
    # Keep Centerspace for Midwest coverage
    "CSR":  "Centerspace REIT",
}

_TOPIC_QUERIES = [
    # Core national topics
    ("rent control legislation", []),
    ("apartment rent cap law", []),
    ("multifamily REIT regulation", ["AVB", "EQR", "ESS", "MAA", "CPT", "UDR"]),
    ("algorithmic pricing rent ban", ["AVB", "EQR", "ESS"]),
    ("single family rental regulation", ["INVH", "AMH"]),
    # Macro REIT drivers
    ("federal reserve interest rate housing", []),
    ("housing market 2026 outlook", []),
    ("apartment rent inflation 2026", []),
    ("commercial real estate market", []),
    ("multifamily vacancy rates 2026", []),
    # City-level rent/housing policy
    ("rent control Atlanta Georgia", []),
    ("rent control Houston Texas", []),
    ("rent control Dallas Texas", []),
    ("rent control Austin Texas", []),
    ("rent control Denver Colorado", []),
    ("rent control Chicago Illinois", []),
    ("rent control Minneapolis Minnesota", []),
    ("rent control Seattle Washington", []),
    ("rent control Phoenix Arizona", []),
    ("rent control Nashville Tennessee", []),
    ("rent control Charlotte North Carolina", []),
    ("rent control Miami Florida", []),
    ("rent control Boston Massachusetts", []),
    ("NYC rent stabilization 2026", ["EQR", "AVB"]),
    # State legislative
    ("California housing bill 2026", ["ESS", "AVB", "EQR"]),
    ("Oregon rent control legislation", ["ESS"]),
    ("Minnesota rent control legislation", ["CSR"]),
    ("Colorado rent control housing", ["UDR", "CPT", "CSR"]),
    ("Georgia housing regulation Atlanta", ["MAA", "CPT"]),
    ("Texas housing preemption", ["MAA", "CPT", "INVH", "AMH"]),
    # Election/political
    ("mayor election housing policy 2026", []),
    ("governor election rent control 2026", []),
    ("senate election housing legislation 2026", []),
]


@st.cache_data(ttl=300)
def fetch_live_news() -> pd.DataFrame:
    """Pull headlines from Google News RSS for tracked tickers and rent-control topics."""
    rows = []
    seen_titles = set()

    def _fetch(query: str, tickers: list):
        url = (
            "https://news.google.com/rss/search?"
            + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        )
        try:
            feed = feedparser.parse(url)
        except Exception:
            return
        for entry in feed.entries[:5]:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            source = entry.get("source", {}).get("title", "Google News")
            published = entry.get("published", "")[:16]
            link = entry.get("link", "")
            summary_raw = entry.get("summary", "")
            # Strip HTML tags from summary
            import re
            summary = re.sub(r"<[^>]+>", " ", summary_raw).strip()[:300]
            rows.append({
                "headline": title,
                "source_name": source,
                "published": published,
                "url": link,
                "tickers_exposed": ",".join(tickers) if tickers else "",
                "summary": summary,
            })

    # Per-ticker queries
    for ticker, term in _TICKER_SEARCH_TERMS.items():
        _fetch(term, [ticker])

    # Topic queries
    for query, tickers in _TOPIC_QUERIES:
        _fetch(query, tickers)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ─── Power & Grid News Scraper ────────────────────────────────────────────────

_GRID_NEWS_QUERIES: list[tuple[str, str]] = [
    ("data center power grid", ""),
    ("utility ratepayer protection bill data center", ""),
    ("AI power moratorium data center", ""),
    ("hyperscale electricity demand utility", ""),
    ("data center construction moratorium", ""),
    ("PJM capacity data center large load", ""),
    ("ERCOT large load registration data center", ""),
    ("Virginia data center power grid Dominion Energy", "VA"),
    ("Texas ERCOT data center SB 6 large load", "TX"),
    ("Ohio data center grid upgrade AI campus ratepayer", "OH"),
    ("New York data center moratorium 7.5MW NYISO", "NY"),
    ("Georgia data center Georgia Power grid", "GA"),
    ("Oklahoma data center moratorium SB 1488", "OK"),
    ("California data center CAISO AB 205 interconnection", "CA"),
    ("Illinois data center MISO tax exemption SB 2400", "IL"),
    ("New Jersey data center PJM grid constraint BPU", "NJ"),
]

_GRID_NEWS_FALLBACK: list[dict] = [
    {
        "headline": "PJM Reports 35GW Queue Backlog as Data Center Demand Accelerates in Northern Virginia",
        "source_name": "Utility Dive",
        "published": "2026-05-12",
        "url": "",
        "state": "VA",
        "summary": (
            "PJM Interconnection reports its queue has surpassed 35 GW in new requests, "
            "driven primarily by hyperscale data center load in the Northern Virginia corridor. "
            "Average interconnection timelines have extended to 4–6 years."
        ),
    },
    {
        "headline": "Oklahoma SB 1488 Moratorium Freezes Large Data Center Projects Over 100MW",
        "source_name": "S&P Global Market Intelligence",
        "published": "2026-04-18",
        "url": "",
        "state": "OK",
        "summary": (
            "Oklahoma's 18-month moratorium on data center facilities exceeding 100MW aggregate "
            "load took effect following SB 1488 signing. OCC conducting grid impact study due Q3 2026."
        ),
    },
    {
        "headline": "NYC Data Center Moratorium In Effect: No New Builds Over 7.5MW in Five Boroughs",
        "source_name": "The Wall Street Journal",
        "published": "2026-03-29",
        "url": "",
        "state": "NY",
        "summary": (
            "New York City's construction moratorium on new data centers exceeding 7.5MW "
            "remains in effect across all five boroughs. State legislation (SB 7768) pending "
            "would extend the restriction statewide."
        ),
    },
    {
        "headline": "ERCOT Implements New Large Load Registration Rules Under SB 6 Framework",
        "source_name": "Houston Chronicle",
        "published": "2026-04-05",
        "url": "",
        "state": "TX",
        "summary": (
            "Texas data center operators with loads exceeding 75MW must complete ERCOT's "
            "mandatory large-load registration before grid interconnection. PUCT officials "
            "say the rule prevents sudden grid stress events during peak demand periods."
        ),
    },
    {
        "headline": "Ohio Ratepayer Protection Act Forces Tech Giants to Fund Grid Upgrades Directly",
        "source_name": "Columbus Dispatch",
        "published": "2026-03-14",
        "url": "",
        "state": "OH",
        "summary": (
            "HB 315 requires data center operators consuming more than 10MW to directly "
            "fund the cost of grid infrastructure upgrades rather than socializing costs "
            "across all Ohio ratepayers. PUCO implementing new rate filing procedures."
        ),
    },
    {
        "headline": "California CAISO Warns of 6–9 Year Interconnection Waits for Bay Area Data Centers",
        "source_name": "Bloomberg",
        "published": "2026-02-28",
        "url": "",
        "state": "CA",
        "summary": (
            "CAISO's latest interconnection queue report shows Bay Area data center projects "
            "now waiting up to 9 years for grid access. Hyperscale operators are pivoting "
            "expansion to Texas, Virginia, and Georgia."
        ),
    },
    {
        "headline": "Virginia SB 1015 Green Backup Power Rule Reshapes Data Center Economics in NOVA",
        "source_name": "Bisnow",
        "published": "2026-02-10",
        "url": "",
        "state": "VA",
        "summary": (
            "Virginia's requirement that new data centers use green backup power to qualify "
            "for property tax incentives is forcing hyperscale operators to renegotiate power "
            "purchase agreements ahead of new campus phases in Northern Virginia."
        ),
    },
    {
        "headline": "Georgia HB 1192: Data Centers Must Use Green Backup Power to Qualify for Tax Incentives",
        "source_name": "Atlanta Business Chronicle",
        "published": "2026-01-22",
        "url": "",
        "state": "GA",
        "summary": (
            "Georgia's equipment tax exemption for data centers now requires certification of "
            "green backup power systems. The change applies to new facility permits filed after "
            "January 1, 2025, prompting battery storage retrofit plans across Atlanta campuses."
        ),
    },
]


@st.cache_data(ttl=300)
def fetch_grid_news() -> pd.DataFrame:
    rows: list[dict] = []
    seen_titles: set[str] = set()

    def _fetch(query: str, state_tag: str) -> None:
        url = (
            "https://news.google.com/rss/search?"
            + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        )
        try:
            feed = feedparser.parse(url)
        except Exception:
            return
        for entry in feed.entries[:5]:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            source = entry.get("source", {}).get("title", "Google News")
            published = entry.get("published", "")[:16]
            link = entry.get("link", "")
            summary_raw = entry.get("summary", "")
            summary = re.sub(r"<[^>]+>", " ", summary_raw).strip()[:300]
            rows.append({
                "headline": title,
                "source_name": source,
                "published": published,
                "url": link,
                "state": state_tag,
                "summary": summary,
            })

    for _query, _state_tag in _GRID_NEWS_QUERIES:
        _fetch(_query, _state_tag)

    if not rows:
        return pd.DataFrame(_GRID_NEWS_FALLBACK)
    return pd.DataFrame(rows)


# ─── Prediction Market Feeds ──────────────────────────────────────────────────

_POLY_KEYWORDS = [
    # Housing / rent control
    "rent control", "rent cap", "rent stabilization", "housing ballot",
    "eviction moratorium", "multifamily", "real estate crash", "housing market",
    "new york rent", "oregon rent", "california rent", "zoning ballot",
    # Macro / REIT drivers
    "federal reserve", "rate cut", "rate hike", "interest rate", "fed funds",
    "recession", "unemployment rate", "jobs report", "cpi inflation", "gdp growth",
    "treasury yield", "mortgage rate", "10-year yield",
]

_MANIFOLD_QUERIES = [
    ("rent control", "Housing Policy"),
    ("rent freeze NYC", "Housing Policy"),
    ("housing ballot", "Housing Policy"),
    ("zoning reform", "Housing Policy"),
    ("federal reserve rate cut 2026", "Fed / Rates"),
    ("federal reserve hike 2026", "Fed / Rates"),
    ("recession 2026", "Macro"),
    ("us inflation 2026", "Macro"),
    ("unemployment 2026", "Macro"),
    ("real estate crash", "Real Estate"),
    ("housing market 2026", "Real Estate"),
]

_PREDICTIT_KEYWORDS = [
    # Congressional control — directly affects national housing legislation
    "control the senate", "control the house", "house seats", "senate seats",
    # State governor races in highest rent-control-risk states
    "governor of california", "governor of new york", "governor of oregon",
    "governor of washington", "governor of colorado", "governor of minnesota",
    "governor of illinois", "governor of massachusetts", "governor of new jersey",
    # Key Senate races in those states
    "senate election in california", "senate election in new york",
    "senate election in oregon", "senate election in washington",
    "senate election in colorado", "senate election in minnesota",
    "senate election in illinois", "senate election in massachusetts",
    # Economy / Fed (PredictIt occasionally has these)
    "federal reserve", "interest rate", "inflation", "recession",
]


@st.cache_data(ttl=300)
def fetch_polymarket_odds() -> list[dict]:
    """Fetch active Polymarket markets relevant to housing/macro/elections."""
    results = []
    seen_ids = set()
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "closed": "false", "limit": 500},
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        markets = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
    except Exception:
        return []

    for m in markets:
        question = m.get("question", "")
        if not question:
            continue
        q_lower = question.lower()
        if not any(kw in q_lower for kw in _POLY_KEYWORDS):
            continue
        mid = m.get("id", question)
        if mid in seen_ids:
            continue
        seen_ids.add(mid)

        outcomes = m.get("outcomes", "[]")
        prices   = m.get("outcomePrices", "[]")
        try:
            outcomes = outcomes if isinstance(outcomes, list) else __import__("json").loads(outcomes)
            prices   = prices   if isinstance(prices,   list) else __import__("json").loads(prices)
        except Exception:
            outcomes, prices = [], []

        prob = None
        for oc, pr in zip(outcomes, prices):
            if str(oc).lower() == "yes":
                try:
                    prob = round(float(pr) * 100, 1)
                except (TypeError, ValueError):
                    pass
                break
        if prob is None and prices:
            try:
                prob = round(float(prices[0]) * 100, 1)
            except (TypeError, ValueError):
                pass

        end_date = (m.get("endDate") or "")[:10]
        volume = m.get("volume", 0)
        try:
            volume = int(float(volume))
        except (TypeError, ValueError):
            volume = 0

        slug = m.get("slug", "")
        url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"

        results.append({"question": question, "prob": prob, "end_date": end_date,
                        "volume": volume, "url": url})

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:20]


@st.cache_data(ttl=300)
def fetch_manifold_odds() -> list[dict]:
    """Fetch Manifold Markets binary questions relevant to housing/macro."""
    results = []
    seen_ids = set()
    for term, category in _MANIFOLD_QUERIES:
        try:
            resp = requests.get(
                "https://api.manifold.markets/v0/search-markets",
                params={"term": term, "limit": 4, "filter": "open",
                        "sort": "liquidity", "contractType": "BINARY"},
                timeout=8,
            )
            markets = resp.json() if resp.ok else []
        except Exception:
            continue
        for m in markets:
            if m.get("probability") is None:
                continue
            mid = m.get("id", m.get("url", ""))
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            try:
                prob = round(float(m["probability"]) * 100, 1)
            except (TypeError, ValueError):
                continue
            close_ms = m.get("closeTime", 0)
            try:
                import datetime
                end_date = datetime.datetime.fromtimestamp(close_ms / 1000).strftime("%Y-%m-%d")
            except Exception:
                end_date = ""
            results.append({
                "question": m.get("question", ""),
                "prob": prob,
                "end_date": end_date,
                "volume": int(m.get("volume", 0)),
                "traders": m.get("uniqueBettorCount", 0),
                "url": m.get("url", "https://manifold.markets"),
                "category": category,
            })
    results.sort(key=lambda x: x["volume"], reverse=True)
    seen_q: set = set()
    deduped = []
    for r in results:
        key = r["question"][:60].lower()
        if key not in seen_q:
            seen_q.add(key)
            deduped.append(r)
    return deduped[:20]


@st.cache_data(ttl=300)
def fetch_predictit_odds() -> list[dict]:
    """Fetch PredictIt markets relevant to elections in REIT-exposed states + congressional control."""
    try:
        resp = requests.get(
            "https://www.predictit.org/api/marketdata/all/",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        all_markets = resp.json().get("markets", [])
    except Exception:
        return []

    results = []
    for m in all_markets:
        name = m.get("name", "")
        if not any(kw in name.lower() for kw in _PREDICTIT_KEYWORDS):
            continue
        contracts = m.get("contracts", [])
        contract_rows = []
        for c in contracts:
            price = c.get("lastTradePrice") or c.get("bestYesPrice")
            try:
                prob = round(float(price) * 100, 1) if price is not None else None
            except (TypeError, ValueError):
                prob = None
            contract_rows.append({"name": c.get("name", ""), "prob": prob})
        contract_rows = [r for r in contract_rows if r["prob"] is not None]
        if not contract_rows:
            continue
        results.append({
            "question": name,
            "contracts": contract_rows[:4],
            "url": m.get("url", "https://www.predictit.org"),
        })
    return results[:20]


# ─── Kalshi Macro Odds ────────────────────────────────────────────────────────

_KALSHI_SERIES = [
    ("KXFED",    "Fed Funds Rate",       "Will the upper bound of the federal funds rate be above {strike}% following the {meeting} FOMC meeting?"),
    ("KXCPI",    "CPI Inflation",        None),
    ("KXGDP",    "GDP Growth",           None),
    ("KXEHSALES","Existing Home Sales",  None),
]

_KALSHI_EXTRA_SERIES = ["HOUSESTART", "HOME", "FRMMAX", "CPISHELTER"]

@st.cache_data(ttl=300)
def fetch_kalshi_odds() -> list[dict]:
    """Fetch Kalshi macro markets: Fed rate, CPI, GDP, home sales, housing starts."""
    results = []
    seen = set()
    all_series = [s[0] for s in _KALSHI_SERIES] + _KALSHI_EXTRA_SERIES
    series_labels = {
        "KXFED": "Fed Funds Rate", "KXCPI": "CPI", "KXGDP": "GDP Growth",
        "KXEHSALES": "Existing Home Sales", "HOUSESTART": "Housing Starts",
        "HOME": "New Home Sales", "FRMMAX": "Mortgage Rate High", "CPISHELTER": "CPI Shelter",
    }
    for series in all_series:
        try:
            resp = requests.get(
                "https://api.elections.kalshi.com/trade-api/v2/markets",
                params={"series_ticker": series, "status": "open", "limit": 4},
                timeout=6,
                headers={"Accept": "application/json"},
            )
            markets = resp.json().get("markets", []) if resp.ok else []
        except Exception:
            continue
        for m in markets:
            title = m.get("title", "")
            if not title or title in seen:
                continue
            seen.add(title)
            price = m.get("yes_ask_dollars") or m.get("last_price_dollars")
            try:
                prob = round(float(price) * 100, 1) if price is not None else None
            except (TypeError, ValueError):
                prob = None
            close = (m.get("close_time") or "")[:10]
            results.append({
                "title": title,
                "prob": prob,
                "close": close,
                "series": series_labels.get(series, series),
                "ticker": m.get("ticker", ""),
                "url": f"https://kalshi.com/markets/{m.get('ticker','').lower()}",
            })
    results.sort(key=lambda x: (x["series"], x["close"]))
    return results


# ─── FRED Historical Data ─────────────────────────────────────────────────────

FRED_SERIES = {
    "FEDFUNDS":        ("Fed Funds Rate",          "%",  "monthly"),
    "MORTGAGE30US":    ("30-Yr Mortgage Rate",      "%",  "weekly"),
    "CUSR0000SAH1":    ("CPI Shelter",              "idx","monthly"),
    "CPIAUCSL":        ("CPI All Items",            "idx","monthly"),
    "EXHOSLUSM495S":   ("Existing Home Sales",      "M",  "monthly"),
    "UNRATE":          ("Unemployment Rate",        "%",  "monthly"),
    "HOUST":           ("Housing Starts",           "K",  "monthly"),
}

@st.cache_data(ttl=3600)
def fetch_fred_series(series_id: str, months: int = 36) -> pd.DataFrame:
    """Fetch historical FRED data via public CSV endpoint (no API key required).
    Source: Federal Reserve Bank of St. Louis (fred.stlouisfed.org)"""
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        resp.raise_for_status()
        # Validate we got CSV, not an error page
        if not resp.text.strip().startswith("observation_date"):
            return pd.DataFrame(columns=["date", "value"])
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().sort_values("date")
        cutoff = df["date"].max() - pd.DateOffset(months=months)
        return df[df["date"] >= cutoff].reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["date", "value"])


@st.cache_data(ttl=3600)
def fetch_all_fred() -> dict[str, pd.DataFrame]:
    """Fetch all FRED macro series needed for the CIO dashboard."""
    return {sid: fetch_fred_series(sid, months=36) for sid in FRED_SERIES}


# ─── REIT Market Prices ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_reit_prices(tickers: tuple[str, ...] = (), period: str = "1y") -> pd.DataFrame:
    """Fetch REIT close prices from Yahoo Finance for the given tickers only."""
    if not tickers:
        return pd.DataFrame()
    try:
        ticker_list = list(tickers)
        data = yf.download(ticker_list, period=period, progress=False,
                           auto_adjust=True, actions=False)
        # yfinance returns flat columns for a single ticker, MultiIndex for multiple
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].dropna(how="all")
        else:
            close = data[["Close"]].rename(columns={"Close": ticker_list[0]}).dropna(how="all")
        return close
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_reit_info(tickers: tuple[str, ...] = ()) -> dict[str, dict]:
    """Fetch key market stats for each REIT ticker in the given tuple."""
    result = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            fi = t.fast_info
            result[ticker] = {
                "last_price":  round(fi.last_price, 2),
                "year_high":   round(fi.year_high, 2),
                "year_low":    round(fi.year_low, 2),
                "market_cap":  fi.market_cap,
            }
        except Exception:
            result[ticker] = {}
    return result


def _sparkline(df: pd.DataFrame, color: str = "#1E90FF", height: int = 80) -> go.Figure:
    """Return a minimal Plotly sparkline figure."""
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["value"],
            mode="lines", line=dict(color=color, width=1.5),
            fill="tozeroy", fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba"),
            hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=4, b=0), height=height,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, autorange=True),
    )
    return fig


# ─── Nation View Data ─────────────────────────────────────────────────────────

# Key municipal/state elections in REIT-relevant metros, 2025-2027
CITY_ELECTION_CALENDAR = {
    # ── HIGH RENT-CONTROL RISK ──────────────────────────────────────────────────
    "New York City": {
        "state": "NY", "risk": "Critical",
        "tickers": ["EQR", "AVB"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Completed",
             "note": "Zohran Mamdani (D-primary) won — explicit rent freeze pledge; Brad Lander general election Nov 2025"},
        ],
        "rent_control_law": "Active Enforced",
        "policy_note": "Strongest rent stabilization regime in the US. ~1M stabilized units.",
    },
    "Boston": {
        "state": "MA", "risk": "Critical",
        "tickers": ["AVB", "EQR"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Completed",
             "note": "Michelle Wu re-elected; strong rent control advocate"},
            {"office": "State Senate (MA)", "date": "Nov 2026", "status": "Upcoming",
             "note": "Statewide rent control ballot measure expected 2026"},
        ],
        "rent_control_law": "Pending Vote",
        "policy_note": "Cambridge ballot filed for Nov 2026. Boston pushing state-level enabling legislation.",
    },
    "San Francisco": {
        "state": "CA", "risk": "Critical",
        "tickers": ["ESS", "AVB"],
        "elections": [
            {"office": "Mayor", "date": "Nov 5, 2024", "status": "Completed",
             "note": "Daniel Lurie elected; moderate housing stance"},
            {"office": "Board of Supervisors (key seats)", "date": "Nov 2026", "status": "Upcoming",
             "note": "Progressive vs. moderate balance determines local rental ordinance enforcement"},
        ],
        "rent_control_law": "Active Enforced",
        "policy_note": "AB 1482 + local just-cause eviction. One of the most regulated US rental markets.",
    },
    "Los Angeles": {
        "state": "CA", "risk": "Critical",
        "tickers": ["ESS", "AVB", "EQR"],
        "elections": [
            {"office": "Mayor", "date": "Nov 2026", "status": "Upcoming",
             "note": "Karen Bass faces re-election; housing policy central to campaign"},
            {"office": "City Council (key districts)", "date": "Nov 2026", "status": "Upcoming",
             "note": "RSO enforcement votes depend on council composition"},
        ],
        "rent_control_law": "Active Enforced",
        "policy_note": "LA Rent Stabilization Ordinance + AB 1482. Algorithmic pricing ban active statewide.",
    },
    "Minneapolis": {
        "state": "MN", "risk": "Critical",
        "tickers": ["CSR"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Upcoming",
             "note": "Incumbent Jacob Frey facing progressive challengers with rent stabilization platforms"},
            {"office": "City Council", "date": "Nov 4, 2025", "status": "Upcoming",
             "note": "Council majority determines rent stabilization ordinance implementation"},
        ],
        "rent_control_law": "Developing Ballot",
        "policy_note": "Minneapolis passed rent stabilization in 2021 but state preemption battles ongoing.",
    },
    "Seattle": {
        "state": "WA", "risk": "Critical",
        "tickers": ["ESS", "AVB"],
        "elections": [
            {"office": "City Council (At-Large)", "date": "Nov 2025", "status": "Upcoming",
             "note": "Council balance key to rent control ordinance proposals"},
            {"office": "State Senate (WA)", "date": "Nov 2026", "status": "Upcoming",
             "note": "WA state rent control bill has advanced; Senate control pivotal"},
        ],
        "rent_control_law": "Pending Vote",
        "policy_note": "Seattle has just-cause eviction. State-level rent cap bill active in 2026 legislature.",
    },
    # ── MODERATE RISK ──────────────────────────────────────────────────────────
    "Denver": {
        "state": "CO", "risk": "Moderate",
        "tickers": ["UDR", "CPT", "CSR"],
        "elections": [
            {"office": "Mayor", "date": "Jun 2027", "status": "Upcoming",
             "note": "Mike Johnston (incumbent); pushed state rent stabilization study"},
            {"office": "State Governor (CO)", "date": "Nov 2026", "status": "Upcoming",
             "note": "Jared Polis term-limited; successor race open — rent control stance TBD"},
            {"office": "State Legislature (CO)", "date": "Nov 2026", "status": "Upcoming",
             "note": "CO preemption law expires 2025; legislature could allow local rent control"},
        ],
        "rent_control_law": "Developing Ballot",
        "policy_note": "CO preemption sunset creates acute risk in 2025-2026 window.",
    },
    "Chicago": {
        "state": "IL", "risk": "Moderate",
        "tickers": ["EQR", "AVB"],
        "elections": [
            {"office": "Mayor", "date": "Feb 2027", "status": "Upcoming",
             "note": "Brandon Johnson up for re-election; strong tenant protection advocate"},
            {"office": "State Legislature (IL)", "date": "Nov 2026", "status": "Upcoming",
             "note": "IL preemption under legislative challenge; Chicago pushing for home rule expansion"},
        ],
        "rent_control_law": "Pending Vote",
        "policy_note": "IL preemption technically blocks rent control, but state bills to allow local control have advanced.",
    },
    "Portland": {
        "state": "OR", "risk": "Moderate",
        "tickers": ["ESS"],
        "elections": [
            {"office": "Mayor", "date": "Nov 5, 2024", "status": "Completed",
             "note": "Keith Wilson elected; moderate housing stance"},
            {"office": "City Council (new structure)", "date": "Nov 2026", "status": "Upcoming",
             "note": "New 12-member council under ranked-choice; rental policy outcomes uncertain"},
        ],
        "rent_control_law": "Active Enforced",
        "policy_note": "Oregon SB 608: 7% + CPI cap statewide. Portland has additional local eviction controls.",
    },
    "Washington DC": {
        "state": "DC", "risk": "Moderate",
        "tickers": ["EQR", "AVB", "UDR"],
        "elections": [
            {"office": "Mayor", "date": "Nov 2026", "status": "Upcoming",
             "note": "Muriel Bowser term-limited; open race with candidates favoring stronger tenant protections"},
            {"office": "DC Council", "date": "Nov 2026", "status": "Upcoming",
             "note": "Council has advanced rent increase limits beyond existing law"},
        ],
        "rent_control_law": "Active Enforced",
        "policy_note": "DC Rent Control Act covers pre-1976 buildings. New tenant protection bills expand coverage.",
    },
    # ── LOWER RISK (preemption states — watch for shifts) ─────────────────────
    "Atlanta": {
        "state": "GA", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT", "INVH"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Upcoming",
             "note": "Andre Dickens facing re-election; moderate on housing, supportive of development"},
            {"office": "City Council", "date": "Nov 2025", "status": "Upcoming",
             "note": "Watch for tenant protection ordinance proposals from progressive members"},
            {"office": "State Legislature (GA)", "date": "Nov 2026", "status": "Upcoming",
             "note": "GA has strong preemption; state races determine whether preemption holds"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "GA state preemption blocks local rent control. Watch for state-level preemption challenge if Dems gain seats.",
    },
    "Houston": {
        "state": "TX", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT", "INVH", "AMH"],
        "elections": [
            {"office": "Mayor", "date": "Nov 2027", "status": "Upcoming",
             "note": "John Whitmire (elected 2023); pro-development; TX preemption very strong"},
            {"office": "State Legislature (TX)", "date": "Nov 2026", "status": "Upcoming",
             "note": "TX preemption almost certain to hold under Republican supermajority"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "TX state preemption is among the strongest in the US. Very low near-term risk.",
    },
    "Dallas": {
        "state": "TX", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT", "INVH", "AMH"],
        "elections": [
            {"office": "Mayor", "date": "Jun 2025", "status": "Upcoming",
             "note": "Dallas mayoral race; TX preemption insulates from rent control regardless of outcome"},
            {"office": "City Council", "date": "Jun 2025", "status": "Upcoming",
             "note": "Council composition less material given state preemption"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "TX preemption. Dallas/Ft Worth is one of the largest multifamily markets in the country.",
    },
    "Austin": {
        "state": "TX", "risk": "Low/Stable",
        "tickers": ["MAA", "INVH", "AMH"],
        "elections": [
            {"office": "Mayor", "date": "Nov 2026", "status": "Upcoming",
             "note": "Kirk Watson (elected 2022); progressive on housing supply but TX preemption binding"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "TX preemption. Austin is one of the fastest-growing multifamily markets; supply-side story.",
    },
    "Phoenix": {
        "state": "AZ", "risk": "Low/Stable",
        "tickers": ["MAA", "INVH", "AMH", "CPT"],
        "elections": [
            {"office": "Mayor", "date": "Nov 2026", "status": "Upcoming",
             "note": "Kate Gallego re-election expected; AZ preemption very strong"},
            {"office": "State Legislature (AZ)", "date": "Nov 2026", "status": "Upcoming",
             "note": "AZ Republicans hold preemption firm; watch signature drive (Phoenix ballot measure 142K/237K sigs)"},
        ],
        "rent_control_law": "Developing Ballot",
        "policy_note": "AZ preemption strong but Phoenix ballot initiative has 142K of 237K signatures. Monitor closely.",
    },
    "Nashville": {
        "state": "TN", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT"],
        "elections": [
            {"office": "Mayor", "date": "Sep 2027", "status": "Upcoming",
             "note": "Freddie O'Connell (elected 2023); TN preemption binding"},
            {"office": "State Legislature (TN)", "date": "Nov 2026", "status": "Upcoming",
             "note": "TN Republican supermajority; preemption not at risk"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "TN preemption. Nashville is a major Sun Belt multifamily growth market.",
    },
    "Charlotte": {
        "state": "NC", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Upcoming",
             "note": "Vi Lyles facing re-election; NC preemption binding"},
            {"office": "State Legislature (NC)", "date": "Nov 2026", "status": "Upcoming",
             "note": "NC Republicans hold preemption; Dem gains in 2026 could shift landscape long-term"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "NC preemption. Charlotte-Mecklenburg fastest growing metro in the Southeast.",
    },
    "Raleigh": {
        "state": "NC", "risk": "Low/Stable",
        "tickers": ["MAA", "CPT"],
        "elections": [
            {"office": "Mayor", "date": "Nov 4, 2025", "status": "Upcoming",
             "note": "Mary-Ann Baldwin re-election; NC preemption binding"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "Research Triangle market. Strong job growth driving apartment demand.",
    },
    "Tampa": {
        "state": "FL", "risk": "Low/Stable",
        "tickers": ["MAA", "INVH", "AMH"],
        "elections": [
            {"office": "Mayor", "date": "Mar 2027", "status": "Upcoming",
             "note": "Jane Castor term-limited; FL preemption among strongest in US"},
            {"office": "State Legislature (FL)", "date": "Nov 2026", "status": "Upcoming",
             "note": "FL Republican supermajority; preemption not at risk"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "FL preemption overturned Orange County rent control in 2023. Bulletproof preemption.",
    },
    "Las Vegas": {
        "state": "NV", "risk": "Low/Stable",
        "tickers": ["INVH", "AMH", "UDR"],
        "elections": [
            {"office": "State Legislature (NV)", "date": "Nov 2026", "status": "Upcoming",
             "note": "NV has no rent control but Democrats hold legislature; watch for new bills"},
        ],
        "rent_control_law": "Defeated/Preempted",
        "policy_note": "NV preempts local rent control but no statewide cap. Watch state Dem majority.",
    },
}

# Key 2026 gubernatorial races in high-REIT-exposure states
GOVERNOR_RACES_2026 = {
    "CA": {"candidates": "Xavier Becerra (D) vs. Steve Hilton (R)", "risk": "Critical",
           "note": "CA governor controls AB 1482 enforcement and can sign/veto new rent caps"},
    "NY": {"candidates": "Kathy Hochul (D, incumbent)", "risk": "Critical",
           "note": "NY governor critical for Good Cause Eviction expansion and rent law renewal"},
    "OR": {"candidates": "Open seat — Tina Kotek term-limited 2026", "risk": "Moderate",
           "note": "OR has statewide rent cap (SB 608); governor influences enforcement"},
    "WA": {"candidates": "Bob Ferguson (D, incumbent)", "risk": "Moderate",
           "note": "WA rent control bill advanced in 2026; governor veto or signature is pivotal"},
    "CO": {"candidates": "Open seat — Polis term-limited", "risk": "Moderate",
           "note": "CO preemption expires 2025; new governor will set enforcement posture"},
    "MN": {"candidates": "Tim Walz (D, incumbent)", "risk": "Moderate",
           "note": "MN rent stabilization battle ongoing; governor's housing agenda matters"},
    "IL": {"candidates": "JB Pritzker (D, incumbent) up for re-election", "risk": "Moderate",
           "note": "IL preemption debate; Pritzker has signaled openness to local rent control"},
    "MA": {"candidates": "Maura Healey (D, incumbent)", "risk": "Moderate",
           "note": "MA ballot measure likely 2026; governor's stance on state rent control law critical"},
    "GA": {"candidates": "Brian Kemp term-limited — open race", "risk": "Low/Stable",
           "note": "GA preemption very strong; new governor unlikely to change"},
    "TX": {"candidates": "Greg Abbott (R, incumbent)", "risk": "Low/Stable",
           "note": "TX preemption ironclad under Abbott; no risk of change"},
    "AZ": {"candidates": "Katie Hobbs (D, incumbent)", "risk": "Low/Stable",
           "note": "AZ preemption strong; Hobbs has not signaled rent control support"},
    "FL": {"candidates": "Ron DeSantis term-limited — open race", "risk": "Low/Stable",
           "note": "FL preemption bulletproof regardless of party"},
    "NC": {"candidates": "Josh Stein (D, new governor 2025)", "risk": "Low/Stable",
           "note": "NC preemption; Dem gains in legislature could shift long-term"},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def filter_by_tickers(df: pd.DataFrame, tickers: list) -> pd.DataFrame:
    if not tickers:
        return df
    ticker_set = set(tickers)
    if ticker_set >= set(ALL_TICKERS):
        return df
    return df[df["tickers_exposed"].apply(
        lambda c: bool(ticker_set & set(str(c).split(",")))
    )]


def sol_badge(sol: str) -> str:
    css = {
        "Active Enforced":    "sol-active",
        "Pending Vote":       "sol-pending",
        "Developing Ballot":  "sol-ballot",
        "Defeated/Preempted": "sol-defeated",
    }
    klass = css.get(sol, "sol-pending")
    return f"<span class='sol-badge {klass}'>{sol}</span>"


def risk_badge(risk: str) -> str:
    css = {"Critical": "risk-critical", "Moderate": "risk-moderate", "Low/Stable": "risk-low"}
    klass = css.get(risk, "risk-low")
    return f"<span class='risk-tag {klass}'>{risk}</span>"


def sent_badge(score: float) -> str:
    if score < -0.2:
        return f"<span class='sent-tag sent-bearish'>▼ BEARISH {score:+.2f}</span>"
    elif score > 0.2:
        return f"<span class='sent-tag sent-bullish'>▲ BULLISH {score:+.2f}</span>"
    return f"<span class='sent-tag sent-neutral'>● NEUTRAL {score:+.2f}</span>"


def ticker_chips(tickers_str: str) -> str:
    return " ".join(
        f"<span class='ticker-chip'>{t.strip()}</span>"
        for t in str(tickers_str).split(",") if t.strip()
    )


def sentiment_color(score: float) -> str:
    if score < -0.2:
        return "#FF7070"
    elif score > 0.2:
        return "#2ECC71"
    return "#7A9BBE"


# ─── AI assistant ─────────────────────────────────────────────────────────────

def build_ai_context(df: pd.DataFrame, tickers: list[str] | None = None) -> str:
    active = tickers or list(REIT_SECTORS["Apartment"])
    ticker_summary = ", ".join(f"{t} ({TICKER_NAMES.get(t, t)})" for t in active)
    lines = [
        "You are an expert REIT legislative risk analyst for an institutional investment fund.",
        f"Currently tracked tickers: {ticker_summary}.",
        "CenterSquare Investment Management 13F (03/31/2026) holds: CPT $258M, UDR $282M, INVH $185M, "
        "AMH $166M, MAA $75M, EQR $68M, ESS $52M.",
        "",
        "Current market intelligence database:",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"[{row['state_code']}] {row['metro_market']} | Tickers: {row['tickers_exposed']} | "
            f"{row['category']} | {row['state_of_law']} | Risk: {row['portfolio_risk_impact']} | "
            f"Sentiment: {row['sentiment_score']:.2f}\n"
            f"  Summary: {str(row['summary_insight'])[:350]}"
        )
    lines += [
        "",
        "Answer questions concisely. Quantify NOI impacts when data is available.",
        "Format with bullet points for multi-part answers. Keep responses under 350 words unless asked for detail.",
    ]
    return "\n".join(lines)


def get_ai_response(question: str, df: pd.DataFrame) -> str:
    api_key = st.session_state.get("api_key_input", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "**API key required.** Enter your Anthropic API key in the field above the chat, "
            "or set the `ANTHROPIC_API_KEY` environment variable before launching Streamlit."
        )
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            system=build_ai_context(df, tickers=st.session_state.get("_sidebar_tickers")),
            messages=[
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.get("chat_history", [])[-6:]
                ],
                {"role": "user", "content": question},
            ],
        )
        return response.content[0].text
    except ImportError:
        return "Anthropic library missing. Run: `pip install anthropic`"
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "api_key" in err.lower() or "401" in err:
            return "**Authentication error.** Check that your API key is valid."
        return f"**Error:** {err}"


# ─── Prediction-market UI helpers (module-level so all tabs can use them) ────

def _prob_color(p):
    if p is None: return "#7A9BBE"
    return "#FF4B4B" if p >= 60 else ("#FFA500" if p >= 35 else "#21C55D")

def _prob_bar(p, color):
    pct = int(p) if p is not None else 0
    return (
        f"<div style='background:#1B3150;border-radius:3px;height:5px;margin-top:5px;'>"
        f"<div style='background:{color};width:{pct}%;height:5px;border-radius:3px;'></div></div>"
    )

def _source_header(label, url, note=""):
    return (
        f"<div style='display:flex;align-items:center;gap:10px;margin:22px 0 10px;'>"
        f"<span style='color:#E8EDF5;font-weight:700;font-size:0.95rem;'>{label}</span>"
        f"<a href='{url}' target='_blank' style='color:#4A90D9;font-size:0.78rem;'>↗ {url.split('//')[1].split('/')[0]}</a>"
        f"{'<span style=\"color:#7A9BBE;font-size:0.76rem;\">· ' + note + '</span>' if note else ''}"
        f"</div>"
    )

def _market_card(question, prob, end_date, vol_label, url, sub_label="YES implied prob"):
    color = _prob_color(prob)
    bar   = _prob_bar(prob, color)
    prob_display = f"{prob:.1f}%" if prob is not None else "N/A"
    return (
        f"<div class='intel-card' style='padding:11px 15px;margin-bottom:7px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:14px;'>"
        f"<div style='flex:1;'>"
        f"<a href='{url}' target='_blank' style='color:#C8D8EE;font-size:0.87rem;"
        f"font-weight:600;text-decoration:none;line-height:1.4;'>{question}</a>"
        f"{bar}"
        f"<div style='color:#7A9BBE;font-size:0.74rem;margin-top:4px;'>"
        f"Closes: {end_date or '—'} &nbsp;·&nbsp; {vol_label or '—'}</div>"
        f"</div>"
        f"<div style='text-align:right;white-space:nowrap;'>"
        f"<div style='font-size:1.35rem;font-weight:800;color:{color};'>{prob_display}</div>"
        f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:1px;'>{sub_label}</div>"
        f"</div></div></div>"
    )


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<div style='color:#C9A84C;font-size:1.05rem;font-weight:700;"
        "border-bottom:1px solid #1B3150;padding-bottom:10px;margin-bottom:14px;'>"
        "🏢 REIT Intelligence Engine</div>",
        unsafe_allow_html=True,
    )

    _refresh_options = {"Off": 0, "5 min": 300_000, "15 min": 900_000, "30 min": 1_800_000}
    _refresh_sel = st.selectbox(
        "Auto-Refresh", list(_refresh_options.keys()), index=1,
        help="Automatically reload all live data feeds",
    )
    _refresh_ms = _refresh_options[_refresh_sel]
    if _refresh_ms:
        _tick = st_autorefresh(interval=_refresh_ms, key="global_autorefresh")
    _last_refresh = datetime.datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f"<div style='color:#7A9BBE;font-size:0.72rem;margin-bottom:10px;'>"
        f"Last refreshed: {_last_refresh}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;'>"
        "SECTOR</div>",
        unsafe_allow_html=True,
    )
    _all_sector_names = list(REIT_SECTORS.keys())
    selected_sectors = st.multiselect(
        "Sectors",
        _all_sector_names,
        default=["Apartment"],
        help="Pick one or more sectors, then refine individual tickers below",
        label_visibility="collapsed",
    )
    _sector_tickers: list[str] = []
    for _s in (selected_sectors or _all_sector_names):
        _sector_tickers.extend(REIT_SECTORS[_s])

    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.06em;margin-top:8px;margin-bottom:4px;'>"
        "TICKERS</div>",
        unsafe_allow_html=True,
    )
    selected_tickers = st.multiselect(
        "REIT Tickers",
        options=_sector_tickers,
        default=_sector_tickers,
        format_func=lambda t: f"{t} — {TICKER_NAMES.get(t, t)}",
        help="Refine individual tickers within selected sector(s)",
        label_visibility="collapsed",
    )
    if not selected_tickers:
        selected_tickers = _sector_tickers
    st.session_state["_sidebar_tickers"] = selected_tickers

    if len(selected_tickers) > 50:
        st.info(f"{len(selected_tickers)} tickers selected — price data may load slowly.")

    all_metros = sorted(df_all["metro_market"].unique().tolist())
    selected_metros = st.multiselect(
        "Metro Market", all_metros, default=all_metros,
    )
    risk_filter = st.multiselect(
        "Risk Level", ["Critical", "Moderate", "Low/Stable"],
        default=["Critical", "Moderate", "Low/Stable"],
    )

    st.markdown("---")
    _n_sectors = len(selected_sectors) if selected_sectors else len(_all_sector_names)
    _n_tickers = len(selected_tickers)
    _n_markets = len(all_metros)
    _n_states  = df_all["state_code"].nunique()
    st.markdown(
        f"<div style='color:#7A9BBE;font-size:0.72rem;'>"
        f"CenterSquare 13F · 03/31/2026<br>"
        f"{_n_sectors} sector{'s' if _n_sectors != 1 else ''} · "
        f"{_n_tickers} ticker{'s' if _n_tickers != 1 else ''} · "
        f"{_n_markets} markets · {_n_states} states</div>",
        unsafe_allow_html=True,
    )

# ─── Apply filters ────────────────────────────────────────────────────────────

filtered_df = df_all.copy()
filtered_df = filter_by_tickers(filtered_df, selected_tickers)
if selected_metros:
    filtered_df = filtered_df[filtered_df["metro_market"].isin(selected_metros)]
if risk_filter:
    filtered_df = filtered_df[filtered_df["portfolio_risk_impact"].isin(risk_filter)]

# ─── Page header ─────────────────────────────────────────────────────────────

_header_sectors = " · ".join(selected_sectors) if selected_sectors else "All Sectors"
st.markdown(
    f"""
<div class="page-header">
  <h1>US REIT &amp; Rent Control Intelligence Engine</h1>
  <p>Institutional Legislative Risk Platform &nbsp;·&nbsp;
     {_header_sectors}
     &nbsp;·&nbsp; {len(selected_tickers)} tickers active
     &nbsp;·&nbsp; Powered by Primary Legislative Sources</p>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Metrics ribbon ───────────────────────────────────────────────────────────

active_states = filtered_df[
    filtered_df["state_of_law"].isin(["Active Enforced", "Pending Vote"])
]["state_code"].nunique()
total_states = max(filtered_df["state_code"].nunique(), 1)
exposure_pct = active_states / total_states * 100

critical_count = int((filtered_df["portfolio_risk_impact"] == "Critical").sum())
volatility_label = "HIGH VOLATILITY" if critical_count >= 4 else ("ELEVATED" if critical_count >= 2 else "CONTAINED")

ballot_active = int(
    ((filtered_df["category"] == "Ballot Initiative") &
     (filtered_df["state_of_law"] != "Defeated/Preempted")).sum()
)

avg_sentiment = filtered_df["sentiment_score"].mean() if not filtered_df.empty else 0.0
sentiment_label = "BEARISH" if avg_sentiment < -0.2 else ("BULLISH" if avg_sentiment > 0.2 else "NEUTRAL")

mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Fund Exposure Index", f"{exposure_pct:.1f}%",
           delta=f"{active_states}/{total_states} states at risk", delta_color="inverse")
mc2.metric("NOI Volatility Vector", volatility_label,
           delta=f"{critical_count} critical markets", delta_color="inverse")
mc3.metric("Active Ballot Measures", ballot_active,
           delta="Unresolved items", delta_color="off")
mc4.metric("Portfolio Sentiment", f"{avg_sentiment:+.2f}",
           delta=sentiment_label, delta_color="off")
mc5.metric("Markets Tracked", len(filtered_df),
           delta=f"of {len(df_all)} total records", delta_color="off")

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

cio_tab, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_grid = st.tabs([
    "⚡ CIO Briefing",
    "🗺️ Regulatory Heatmap",
    "📋 Portfolio Intelligence",
    "🗳️ Election & Ballot Pulse",
    "📰 News Terminal",
    "📊 Market Analysis",
    "🏙️ Nation View",
    "🔍 REIT Profiles & Comps",
    "🔌 Power & Grid",
])


# ══════════════════════════════════════════════════════════════════════════════
# CIO BRIEFING TAB — EXECUTIVE MORNING BRIEF
# ══════════════════════════════════════════════════════════════════════════════

with cio_tab:
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:10px;'>"
        f"<div style='color:#C9A84C;font-size:1.1rem;font-weight:800;letter-spacing:0.04em;'>"
        f"CIO MORNING BRIEF</div>"
        f"<div style='color:#7A9BBE;font-size:0.78rem;'>"
        f"{datetime.datetime.now().strftime('%A, %B %d %Y')} &nbsp;·&nbsp; "
        f"Live feeds refreshing every 5 min</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── KPI strip ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    crit_n  = int((df_all["portfolio_risk_impact"] == "Critical").sum())
    active_n = int((df_all["state_of_law"] == "Active Enforced").sum())
    ballot_n = int(df_all[
        (df_all["category"] == "Ballot Initiative") &
        (df_all["state_of_law"].isin(["Developing Ballot", "Pending Vote"]))
    ].shape[0])
    avg_sent_all = df_all["sentiment_score"].mean()
    states_exposed = df_all[
        df_all["state_of_law"].isin(["Active Enforced", "Pending Vote"])
    ]["state_code"].nunique()

    k1.metric("Critical Risk Items", crit_n, delta="Immediate attention", delta_color="inverse")
    k2.metric("Active Enforced Laws", active_n, delta="In effect now", delta_color="off")
    k3.metric("Active Ballot Measures", ballot_n, delta="Unresolved", delta_color="inverse")
    k4.metric("Portfolio Sentiment", f"{avg_sent_all:+.2f}",
              delta="BEARISH" if avg_sent_all < -0.2 else "NEUTRAL", delta_color="off")
    k5.metric("States w/ Active Risk", states_exposed, delta="of 50 total", delta_color="inverse")

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Critical alerts + top news ─────────────────────────────────────────────
    col_alerts, col_macro = st.columns([3, 2])

    with col_alerts:
        crit_rows = df_all[df_all["portfolio_risk_impact"] == "Critical"].sort_values("last_updated", ascending=False)
        if crit_rows.empty:
            st.markdown(
                "<div style='background:#0A2A0A;border:1px solid #21C55D;border-radius:8px;"
                "padding:16px;color:#21C55D;font-weight:700;'>✓ No Critical Items Active</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='color:#FF4B4B;font-size:0.78rem;font-weight:700;"
                "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;'>"
                f"⚠ {len(crit_rows)} CRITICAL RISK ITEMS</div>",
                unsafe_allow_html=True,
            )
            for _, row in crit_rows.iterrows():
                src_link = (f" <a href='{row['source_url']}' target='_blank' "
                            f"style='color:#C9A84C;font-size:0.72rem;'>↗ Source</a>"
                            if row.get("source_url") else "")
                st.markdown(
                    f"<div style='background:#1A0808;border-left:3px solid #FF4B4B;"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:6px;'>"
                    f"<div style='color:#E8EDF5;font-weight:700;font-size:0.87rem;"
                    f"margin-bottom:3px;'>{row['headline']}{src_link}</div>"
                    f"<div style='color:#C8D8EE;font-size:0.78rem;line-height:1.5;'>"
                    f"{str(row['summary_insight'])[:200]}…</div>"
                    f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:4px;'>"
                    f"{row['state_code']} · {row['metro_market']} · "
                    f"{row['source_name']} · {row['last_updated'][:10]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Top news
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.06em;margin:16px 0 8px;'>"
            "Latest News Headlines</div>",
            unsafe_allow_html=True,
        )
        live_news = fetch_live_news()
        if live_news.empty:
            st.markdown("<div style='color:#7A9BBE;font-size:0.82rem;'>News unavailable.</div>",
                        unsafe_allow_html=True)
        else:
            for _, nr in live_news.head(6).iterrows():
                src_link = (f"<a href='{nr['url']}' target='_blank' style='color:#C9A84C;"
                            f"font-size:0.72rem;margin-left:6px;'>↗</a>" if nr.get("url") else "")
                st.markdown(
                    f"<div style='padding:8px 0;border-bottom:1px solid #0F2035;'>"
                    f"<div style='color:#E8EDF5;font-size:0.84rem;font-weight:600;"
                    f"line-height:1.4;'>{nr['headline']}{src_link}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:2px;'>"
                    f"{nr['source_name']} · {nr['published']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Macro snapshot ─────────────────────────────────────────────────────────
    with col_macro:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;'>"
            "Macro Snapshot — Key REIT Drivers</div>",
            unsafe_allow_html=True,
        )
        fred_data = fetch_all_fred()
        fred_available = any(not df.empty for df in fred_data.values())
        if not fred_available:
            st.markdown(
                "<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                "padding:12px;color:#7A9BBE;font-size:0.80rem;'>"
                "⏳ FRED macro data loading… St. Louis Fed public API · "
                "<a href='https://fred.stlouisfed.org' target='_blank' "
                "style='color:#4A90D9;'>fred.stlouisfed.org</a></div>",
                unsafe_allow_html=True,
            )

        for sid, (label, unit, freq) in FRED_SERIES.items():
            df_fred = fred_data.get(sid, pd.DataFrame())
            if df_fred.empty:
                continue
            latest_val = df_fred["value"].iloc[-1]
            prev_val   = df_fred["value"].iloc[-2] if len(df_fred) > 1 else latest_val
            delta      = latest_val - prev_val
            delta_str  = f"{delta:+.2f}" if unit in ("%",) else f"{delta:+.1f}"
            val_str    = f"{latest_val:.2f}{unit}" if unit == "%" else f"{latest_val:,.0f}"
            delta_color = "#FF4B4B" if (delta > 0 and sid in ("FEDFUNDS", "MORTGAGE30US", "CUSR0000SAH1", "CPIAUCSL", "UNRATE")) else "#21C55D" if delta < 0 else "#7A9BBE"
            latest_date = df_fred["date"].iloc[-1].strftime("%b %Y")

            spark_fig = _sparkline(df_fred, color="#1E90FF" if delta <= 0 else "#FF4B4B")

            st.markdown(
                f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                f"padding:10px 12px;margin-bottom:8px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                f"<div>"
                f"<div style='color:#7A9BBE;font-size:0.70rem;text-transform:uppercase;"
                f"letter-spacing:0.05em;'>{label}</div>"
                f"<div style='color:#E8EDF5;font-size:1.2rem;font-weight:800;margin-top:2px;'>"
                f"{val_str}</div>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='color:{delta_color};font-size:0.80rem;font-weight:700;'>{delta_str}</div>"
                f"<div style='color:#7A9BBE;font-size:0.68rem;'>{latest_date}</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(spark_fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── Prediction market signals ──────────────────────────────────────────────
    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;'>"
        "Top Prediction Market Signals</div>",
        unsafe_allow_html=True,
    )
    pm_col1, pm_col2, pm_col3 = st.columns(3)

    # Kalshi top signals
    with pm_col1:
        st.markdown("<div style='color:#C9A84C;font-size:0.72rem;font-weight:700;margin-bottom:6px;'>KALSHI — Regulated Exchange</div>", unsafe_allow_html=True)
        kalshi_cio = fetch_kalshi_odds()
        for m in kalshi_cio[:4]:
            color = _prob_color(m["prob"])
            prob_str = f"{m['prob']:.0f}%" if m["prob"] is not None else "—"
            st.markdown(
                f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:5px;"
                f"padding:8px 10px;margin-bottom:5px;display:flex;justify-content:space-between;'>"
                f"<div style='color:#C8D8EE;font-size:0.76rem;line-height:1.4;flex:1;'>"
                f"<a href='{m['url']}' target='_blank' style='color:#C8D8EE;text-decoration:none;'>"
                f"{m['title'][:65]}</a></div>"
                f"<div style='color:{color};font-size:0.95rem;font-weight:800;margin-left:8px;white-space:nowrap;'>"
                f"{prob_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Manifold top signals
    with pm_col2:
        st.markdown("<div style='color:#4A90D9;font-size:0.72rem;font-weight:700;margin-bottom:6px;'>MANIFOLD — Housing & Macro</div>", unsafe_allow_html=True)
        mf_cio = fetch_manifold_odds()
        for m in mf_cio[:4]:
            color = _prob_color(m["prob"])
            prob_str = f"{m['prob']:.0f}%" if m["prob"] is not None else "—"
            st.markdown(
                f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:5px;"
                f"padding:8px 10px;margin-bottom:5px;display:flex;justify-content:space-between;'>"
                f"<div style='color:#C8D8EE;font-size:0.76rem;line-height:1.4;flex:1;'>"
                f"<a href='{m['url']}' target='_blank' style='color:#C8D8EE;text-decoration:none;'>"
                f"{m['question'][:65]}</a></div>"
                f"<div style='color:{color};font-size:0.95rem;font-weight:800;margin-left:8px;white-space:nowrap;'>"
                f"{prob_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # PredictIt top signals
    with pm_col3:
        st.markdown("<div style='color:#21C55D;font-size:0.72rem;font-weight:700;margin-bottom:6px;'>PREDICTIT — Elections</div>", unsafe_allow_html=True)
        pi_cio = fetch_predictit_odds()
        shown = 0
        for m in pi_cio:
            if shown >= 4:
                break
            top_c = m["contracts"][0] if m["contracts"] else None
            if not top_c:
                continue
            color = _prob_color(top_c["prob"])
            prob_str = f"{top_c['prob']:.0f}%" if top_c["prob"] is not None else "—"
            st.markdown(
                f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:5px;"
                f"padding:8px 10px;margin-bottom:5px;display:flex;justify-content:space-between;'>"
                f"<div style='color:#C8D8EE;font-size:0.76rem;line-height:1.4;flex:1;'>"
                f"<a href='{m['url']}' target='_blank' style='color:#C8D8EE;text-decoration:none;'>"
                f"{m['question'][:55]} [{top_c['name'][:15]}]</a></div>"
                f"<div style='color:{color};font-size:0.95rem;font-weight:800;margin-left:8px;white-space:nowrap;'>"
                f"{prob_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            shown += 1

    # ── Upcoming events ────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    ev_col, pi_col = st.columns([3, 2])

    with ev_col:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;'>"
            "Upcoming Events — Next 90 Days</div>",
            unsafe_allow_html=True,
        )
        today = datetime.date.today()
        cutoff = today + datetime.timedelta(days=90)
        _months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

        events_upcoming = []
        for city, info in CITY_ELECTION_CALENDAR.items():
            for el in info["elections"]:
                if el["status"] == "Upcoming":
                    date_str = el["date"]
                    try:
                        dt = datetime.datetime.strptime(date_str, "%b %d, %Y").date()
                        if today <= dt <= cutoff:
                            events_upcoming.append({
                                "date": dt, "label": f"{el['office']} — {city}, {info['state']}",
                                "note": el["note"], "risk": info["risk"],
                                "tickers": info["tickers"],
                            })
                    except ValueError:
                        pass
        for s, bs in BALLOT_SUPPLEMENTS.items():
            dl = bs.get("deadline", "") or bs.get("election_date", "")
            nm = bs.get("next_milestone", "")
            for text in [dl, nm]:
                if not text or len(text) < 6:
                    continue
                for fmt in ["%B %d, %Y", "%B %Y", "%b %Y"]:
                    try:
                        dt = datetime.datetime.strptime(text.split("—")[0].strip()[:20], fmt).date()
                        if today <= dt <= cutoff:
                            events_upcoming.append({
                                "date": dt, "label": f"Ballot: {s}",
                                "note": text, "risk": "Critical", "tickers": [],
                            })
                        break
                    except ValueError:
                        continue

        events_upcoming.sort(key=lambda x: x["date"])
        if not events_upcoming:
            st.markdown("<div style='color:#7A9BBE;font-size:0.82rem;'>No elections or ballot deadlines found in the next 90 days.</div>", unsafe_allow_html=True)
        else:
            for ev in events_upcoming[:12]:
                r_color = RISK_COLORS.get(ev["risk"], "#7A9BBE")
                days_out = (ev["date"] - today).days
                urgency = "#FF4B4B" if days_out <= 14 else ("#FFA500" if days_out <= 45 else "#7A9BBE")
                chips = ticker_chips(",".join(ev["tickers"])) if ev["tickers"] else ""
                st.markdown(
                    f"<div style='display:flex;gap:10px;align-items:flex-start;padding:7px 0;"
                    f"border-bottom:1px solid #0F2035;'>"
                    f"<div style='min-width:72px;text-align:center;background:#0A1929;"
                    f"border-radius:5px;padding:4px 6px;'>"
                    f"<div style='color:{urgency};font-size:0.85rem;font-weight:800;'>{ev['date'].strftime('%b %d')}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.65rem;'>{days_out}d away</div>"
                    f"</div>"
                    f"<div style='flex:1;'>"
                    f"<div style='color:#E8EDF5;font-size:0.83rem;font-weight:600;'>{ev['label']}</div>"
                    f"<div style='color:#C8D8EE;font-size:0.76rem;line-height:1.4;'>{ev['note'][:120]}</div>"
                    f"{chips}"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    with pi_col:
        # REIT price performance table
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;'>"
            "REIT Price Performance</div>",
            unsafe_allow_html=True,
        )
        _cio_tickers = tuple(st.session_state.get("_sidebar_tickers", list(REIT_SECTORS["Apartment"])))
        reit_info = fetch_reit_info(_cio_tickers)
        reit_prices = fetch_reit_prices(_cio_tickers)

        for ticker in _cio_tickers:
            info = reit_info.get(ticker, {})
            if not info:
                continue
            price = info.get("last_price", 0)
            yh = info.get("year_high", price)
            yl = info.get("year_low", price)
            pct_from_high = (price - yh) / yh * 100 if yh else 0
            # 1-month return
            m1_return = None
            if not reit_prices.empty and ticker in reit_prices.columns:
                col_data = reit_prices[ticker].dropna()
                if len(col_data) >= 21:
                    m1_return = (col_data.iloc[-1] / col_data.iloc[-22] - 1) * 100
            ret_str = f"{m1_return:+.1f}%" if m1_return is not None else "—"
            ret_color = "#21C55D" if (m1_return or 0) >= 0 else "#FF4B4B"
            high_pct_color = "#FF4B4B" if pct_from_high < -15 else ("#FFA500" if pct_from_high < -7 else "#21C55D")

            st.markdown(
                f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:5px;"
                f"padding:7px 10px;margin-bottom:5px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div>"
                f"<span style='color:#C9A84C;font-weight:800;font-size:0.88rem;'>{ticker}</span>"
                f"<span style='color:#7A9BBE;font-size:0.70rem;margin-left:5px;'>${price:.2f}</span>"
                f"</div>"
                f"<div style='display:flex;gap:10px;align-items:center;'>"
                f"<span style='color:{ret_color};font-size:0.80rem;font-weight:700;'>1M {ret_str}</span>"
                f"<span style='color:{high_pct_color};font-size:0.72rem;'>{pct_from_high:.1f}% vs 52W H</span>"
                f"</div>"
                f"</div>"
                f"<div style='background:#1B3150;border-radius:2px;height:3px;margin-top:5px;'>"
                f"<div style='background:#C9A84C;height:3px;border-radius:2px;"
                f"width:{max(0, (price - yl) / (yh - yl) * 100) if yh != yl else 50:.0f}%;'></div>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<span style='color:#7A9BBE;font-size:0.62rem;'>${yl:.0f} 52W L</span>"
                f"<span style='color:#7A9BBE;font-size:0.62rem;'>${yh:.0f} 52W H</span>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ALL-50-STATE CHOROPLETH
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("<div class='section-title'>Legislative Sentiment — All 50 US States</div>", unsafe_allow_html=True)

    # Build a DataFrame with ALL states, merging DB data over baseline
    db_state_agg = (
        df_all.groupby("state_code")
        .agg(
            db_sentiment=("sentiment_score", "mean"),
            market_count=("metro_market", "count"),
            critical_count=("portfolio_risk_impact", lambda x: (x == "Critical").sum()),
            active_laws=("state_of_law", lambda x: (x == "Active Enforced").sum()),
            tickers_all=("tickers_exposed", lambda x: ",".join(x)),
        )
        .reset_index()
    )

    state_frame = pd.DataFrame({"state_code": ALL_STATES})
    state_frame = state_frame.merge(db_state_agg, on="state_code", how="left")
    state_frame["sentiment_score"] = state_frame.apply(
        lambda r: r["db_sentiment"] if pd.notna(r["db_sentiment"])
        else STATE_BASELINE.get(r["state_code"], 0.0),
        axis=1,
    )
    state_frame["data_source"] = state_frame["market_count"].apply(
        lambda x: "Active Coverage" if pd.notna(x) and x > 0 else "Baseline Estimate"
    )
    state_frame["market_count"]   = state_frame["market_count"].fillna(0).astype(int)
    state_frame["critical_count"] = state_frame["critical_count"].fillna(0).astype(int)
    state_frame["active_laws"]    = state_frame["active_laws"].fillna(0).astype(int)
    state_frame["sentiment_disp"] = state_frame["sentiment_score"].round(3)

    # Highlight filtered states
    filtered_states = set(filtered_df["state_code"].unique())
    state_frame["in_filter"] = state_frame["state_code"].isin(filtered_states)

    fig_map = px.choropleth(
        state_frame,
        locations="state_code",
        locationmode="USA-states",
        color="sentiment_score",
        scope="usa",
        color_continuous_scale=[
            [0.00, "#7B0000"],
            [0.20, "#CC2200"],
            [0.35, "#8B3A00"],
            [0.50, "#1B3150"],
            [0.65, "#1E6080"],
            [0.80, "#1A7A4A"],
            [1.00, "#C9A84C"],
        ],
        range_color=[-1.0, 1.0],
        hover_name="state_code",
        hover_data={
            "sentiment_disp": True,
            "market_count": True,
            "critical_count": True,
            "active_laws": True,
            "data_source": True,
            "sentiment_score": False,
        },
        labels={
            "sentiment_disp":  "Sentiment Score",
            "market_count":    "Markets in DB",
            "critical_count":  "Critical Risk Items",
            "active_laws":     "Active Enforced Laws",
            "data_source":     "Coverage Type",
        },
    )
    fig_map.update_layout(
        template="plotly_dark",
        paper_bgcolor="#070F1D",
        plot_bgcolor="#070F1D",
        geo=dict(
            bgcolor="#070F1D", lakecolor="#070F1D",
            landcolor="#0C1929", subunitcolor="#1B3150",
            showlakes=True, showframe=False,
            coastlinecolor="#1B3150",
            showsubunits=True,
        ),
        font=dict(color="#D4DCE8", family="Inter, Segoe UI, sans-serif", size=12),
        coloraxis_colorbar=dict(
            title=dict(text="Sentiment", font=dict(color="#C9A84C", size=12)),
            tickfont=dict(color="#D4DCE8", size=11),
            bgcolor="#0C1929", bordercolor="#1B3150",
            thickness=16, len=0.75,
            tickvals=[-1.0, -0.5, 0, 0.5, 1.0],
            ticktext=["−1.0 Tenant-Favorable", "−0.5", "Neutral", "+0.5", "+1.0 Landlord-Favorable"],
        ),
        margin=dict(l=0, r=0, t=10, b=10),
        height=480,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.78rem;margin:-8px 0 16px 0;'>"
        "🔵 Dark red = tenant-favorable / high regulatory risk &nbsp;|&nbsp; "
        "Navy = neutral &nbsp;|&nbsp; Gold/Green = landlord-favorable / preempted &nbsp;|&nbsp; "
        "Hatched = active database coverage</div>",
        unsafe_allow_html=True,
    )

    col_tbl, col_chart = st.columns([3, 2])

    with col_tbl:
        st.markdown("<div class='section-title'>State Summary</div>", unsafe_allow_html=True)
        display_tbl = (
            state_frame[["state_code", "sentiment_score", "market_count", "critical_count", "data_source"]]
            .rename(columns={
                "state_code":     "State",
                "sentiment_score": "Sentiment",
                "market_count":   "Markets",
                "critical_count": "Critical",
                "data_source":    "Coverage",
            })
            .sort_values("Sentiment")
            .reset_index(drop=True)
        )
        display_tbl["Sentiment"] = display_tbl["Sentiment"].round(3)
        st.dataframe(display_tbl, use_container_width=True, hide_index=True, height=380)

    with col_chart:
        st.markdown("<div class='section-title'>Risk Distribution</div>", unsafe_allow_html=True)
        risk_counts = df_all["portfolio_risk_impact"].value_counts().reset_index()
        risk_counts.columns = ["Risk", "Count"]
        fig_donut = px.pie(
            risk_counts, names="Risk", values="Count",
            color="Risk", color_discrete_map=RISK_COLORS,
            hole=0.5, template="plotly_dark",
        )
        fig_donut.update_layout(
            paper_bgcolor="#0C1929", font=dict(color="#D4DCE8"),
            margin=dict(l=10, r=10, t=10, b=10), height=200,
            legend=dict(font=dict(color="#D4DCE8", size=12), bgcolor="#0C1929"),
            showlegend=True,
        )
        fig_donut.update_traces(textfont_color="#D4DCE8", textfont_size=13)
        st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("<div class='section-title' style='margin-top:10px;'>By Category</div>", unsafe_allow_html=True)
        cat_counts = df_all["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig_cat = px.bar(
            cat_counts, x="Count", y="Category", orientation="h",
            color="Count", color_continuous_scale=["#1B3150", "#C9A84C"],
            template="plotly_dark",
        )
        fig_cat.update_layout(
            paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
            font=dict(color="#D4DCE8", size=11),
            margin=dict(l=10, r=10, t=10, b=10), height=160,
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(gridcolor="#1B3150"),
            yaxis=dict(gridcolor="#0C1929"),
        )
        st.plotly_chart(fig_cat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<div class='section-title'>Portfolio Legislative Exposure Matrix</div>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.warning("No data matches current filters.")
    else:
        # ── Top-line charts ────────────────────────────────────────────────
        ch1, ch2, ch3 = st.columns(3)

        with ch1:
            # Count exposure per ticker
            _active_tickers = st.session_state.get("_sidebar_tickers", list(REIT_SECTORS["Apartment"]))
            ticker_exposure = {}
            for t in _active_tickers:
                cnt = filtered_df["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                ticker_exposure[t] = int(cnt)
            ticker_df = pd.DataFrame(list(ticker_exposure.items()), columns=["Ticker", "Exposure"])
            ticker_df = ticker_df.sort_values("Exposure", ascending=True)
            fig_t = px.bar(
                ticker_df, x="Exposure", y="Ticker", orientation="h",
                color="Exposure", color_continuous_scale=["#1B3150", "#C9A84C"],
                title="Legislative Items per Ticker",
                template="plotly_dark",
            )
            fig_t.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=11),
                margin=dict(l=0, r=10, t=36, b=10), height=260,
                title_font=dict(color="#C9A84C", size=12),
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(gridcolor="#1B3150"),
                yaxis=dict(gridcolor="#0C1929"),
            )
            st.plotly_chart(fig_t, use_container_width=True)

        with ch2:
            # Critical NOI items per ticker
            _active_tickers2 = st.session_state.get("_sidebar_tickers", list(REIT_SECTORS["Apartment"]))
            crit_df = filtered_df[filtered_df["portfolio_risk_impact"] == "Critical"]
            crit_exposure = {}
            for t in _active_tickers2:
                cnt = crit_df["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                crit_exposure[t] = int(cnt)
            crit_frame = pd.DataFrame(
                [(k, v) for k, v in crit_exposure.items() if v > 0],
                columns=["Ticker", "Critical Items"],
            ).sort_values("Critical Items", ascending=True)
            if crit_frame.empty:
                st.info("No critical items in current filter.")
            else:
                fig_c = px.bar(
                    crit_frame, x="Critical Items", y="Ticker", orientation="h",
                    color="Critical Items", color_continuous_scale=["#FFA500", "#FF4B4B"],
                    title="Critical Risk Exposure by Ticker",
                    template="plotly_dark",
                )
                fig_c.update_layout(
                    paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                    font=dict(color="#D4DCE8", size=11),
                    margin=dict(l=0, r=10, t=36, b=10), height=260,
                    title_font=dict(color="#C9A84C", size=12),
                    showlegend=False, coloraxis_showscale=False,
                    xaxis=dict(gridcolor="#1B3150"),
                    yaxis=dict(gridcolor="#0C1929"),
                )
                st.plotly_chart(fig_c, use_container_width=True)

        with ch3:
            fig_sent = px.bar(
                filtered_df.sort_values("sentiment_score"),
                x="sentiment_score",
                y="metro_market",
                orientation="h",
                color="sentiment_score",
                color_continuous_scale=[
                    [0.0, "#CC2200"], [0.5, "#1B3150"], [1.0, "#C9A84C"]
                ],
                range_color=[-1.0, 1.0],
                title="Market Sentiment Scores",
                template="plotly_dark",
            )
            fig_sent.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=10),
                margin=dict(l=0, r=10, t=36, b=10), height=260,
                title_font=dict(color="#C9A84C", size=12),
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(gridcolor="#1B3150", range=[-1.1, 1.1]),
                yaxis=dict(gridcolor="#0C1929"),
            )
            fig_sent.add_vline(x=0, line_color="#7A9BBE", line_dash="dash", line_width=1)
            st.plotly_chart(fig_sent, use_container_width=True)

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Legislative Exposure Detail</div>", unsafe_allow_html=True)

        # ── Matrix table ───────────────────────────────────────────────────
        col_w = [2.0, 0.6, 1.8, 1.8, 1.9, 1.3, 0.9, 0.8]
        headers = ["Metro Market", "St.", "Tickers", "Category", "Status", "Risk", "Sent.", "Audit"]

        hdr = st.columns(col_w)
        for c, h in zip(hdr, headers):
            c.markdown(f"<div class='tbl-header'>{h}</div>", unsafe_allow_html=True)

        for _, row in filtered_df.iterrows():
            rc = st.columns(col_w)
            rc[0].markdown(
                f"<div class='tbl-cell'><strong style='color:#E8EDF5;'>{row['metro_market']}</strong>"
                f"<br><span style='color:#7A9BBE;font-size:0.75rem;'>{row['source_name'][:40] if row['source_name'] else ''}</span></div>",
                unsafe_allow_html=True,
            )
            rc[1].markdown(f"<div class='tbl-cell'><strong style='color:#C9A84C;'>{row['state_code']}</strong></div>", unsafe_allow_html=True)
            rc[2].markdown(f"<div class='tbl-cell'>{ticker_chips(row['tickers_exposed'])}</div>", unsafe_allow_html=True)
            rc[3].markdown(f"<div class='tbl-cell'><span style='color:#C8D8EE;'>{row['category']}</span></div>", unsafe_allow_html=True)
            rc[4].markdown(f"<div class='tbl-cell'>{sol_badge(row['state_of_law'])}</div>", unsafe_allow_html=True)
            rc[5].markdown(f"<div class='tbl-cell'>{risk_badge(row['portfolio_risk_impact'])}</div>", unsafe_allow_html=True)
            rc[6].markdown(
                f"<div class='tbl-cell'><span style='color:{sentiment_color(row['sentiment_score'])};font-weight:700;'>"
                f"{row['sentiment_score']:+.2f}</span></div>",
                unsafe_allow_html=True,
            )
            with rc[7]:
                st.markdown("<div style='padding-top:6px;'></div>", unsafe_allow_html=True)
                if st.button("Audit", key=f"a2_{row['id']}"):
                    st.session_state["audit_row_id"] = int(row["id"])

            with st.expander(f"▸ Summary: {row['metro_market']}", expanded=False):
                ec1, ec2 = st.columns([4, 1])
                ec1.markdown(
                    f"<div style='color:#C8D8EE;font-size:0.87rem;line-height:1.7;'>{row['summary_insight']}</div>",
                    unsafe_allow_html=True,
                )
                with ec2:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.75rem;'>"
                        f"Updated:<br><span style='color:#C9A84C;'>{row['last_updated']}</span></div>",
                        unsafe_allow_html=True,
                    )
                    if row["source_url"]:
                        st.markdown(f"[🔗 Source]({row['source_url']})")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ELECTION & BALLOT PULSE
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<div class='section-title'>Election & Ballot Initiative Tracker</div>", unsafe_allow_html=True)

    ballot_df = filtered_df[
        filtered_df["category"].isin(["Ballot Initiative", "Candidate Profiling"])
    ].copy()

    all_ballot = df_all[df_all["category"].isin(["Ballot Initiative", "Candidate Profiling"])].copy()

    # ── Top KPI strip ──────────────────────────────────────────────────────
    bk1, bk2, bk3, bk4 = st.columns(4)
    bk1.metric("Ballot Items Tracked", len(all_ballot))
    bk2.metric("Active / Developing",
               int(all_ballot["state_of_law"].isin(["Developing Ballot", "Pending Vote"]).sum()))
    bk3.metric("Defeated / Preempted",
               int((all_ballot["state_of_law"] == "Defeated/Preempted").sum()))
    bk4.metric("Candidate Profiles",
               int((all_ballot["category"] == "Candidate Profiling").sum()))

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ── Status pipeline chart ─────────────────────────────────────────────
    col_pipe, col_map = st.columns([3, 2])

    with col_pipe:
        st.markdown("<div class='section-title'>Initiative Pipeline</div>", unsafe_allow_html=True)
        if all_ballot.empty:
            st.info("No ballot data.")
        else:
            status_counts = all_ballot["state_of_law"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            ordered = ["Developing Ballot", "Pending Vote", "Active Enforced", "Defeated/Preempted"]
            status_counts["Status"] = pd.Categorical(status_counts["Status"], categories=ordered, ordered=True)
            status_counts = status_counts.sort_values("Status")

            fig_pipe = px.bar(
                status_counts, x="Status", y="Count",
                color="Status", color_discrete_map=SOL_COLORS,
                template="plotly_dark",
                text="Count",
            )
            fig_pipe.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=12),
                margin=dict(l=10, r=10, t=20, b=10), height=240,
                showlegend=False,
                xaxis=dict(tickfont=dict(color="#D4DCE8", size=11), gridcolor="#1B3150"),
                yaxis=dict(tickfont=dict(color="#D4DCE8"), gridcolor="#1B3150"),
            )
            fig_pipe.update_traces(textfont=dict(color="#D4DCE8"), textposition="outside")
            st.plotly_chart(fig_pipe, use_container_width=True)

    with col_map:
        st.markdown("<div class='section-title'>Tickers at Risk</div>", unsafe_allow_html=True)
        if not all_ballot.empty:
            _active_tickers3 = st.session_state.get("_sidebar_tickers", list(REIT_SECTORS["Apartment"]))
            bt_exposure = {}
            for t in _active_tickers3:
                active_rows = all_ballot[all_ballot["state_of_law"].isin(["Developing Ballot", "Pending Vote"])]
                cnt = active_rows["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                if cnt > 0:
                    bt_exposure[t] = int(cnt)
            if bt_exposure:
                bt_df = pd.DataFrame(list(bt_exposure.items()), columns=["Ticker", "Active Initiatives"])
                fig_bt = px.bar(
                    bt_df.sort_values("Active Initiatives", ascending=True),
                    x="Active Initiatives", y="Ticker", orientation="h",
                    color="Active Initiatives",
                    color_continuous_scale=["#FFA500", "#FF4B4B"],
                    template="plotly_dark",
                )
                fig_bt.update_layout(
                    paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                    font=dict(color="#D4DCE8", size=11),
                    margin=dict(l=0, r=10, t=10, b=10), height=240,
                    showlegend=False, coloraxis_showscale=False,
                    xaxis=dict(gridcolor="#1B3150"),
                    yaxis=dict(gridcolor="#0C1929"),
                )
                st.plotly_chart(fig_bt, use_container_width=True)

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # ── Active signature campaigns ──────────────────────────────────────────
    active_ballot = all_ballot[all_ballot["state_of_law"] == "Developing Ballot"]
    if not active_ballot.empty:
        st.markdown("<div class='section-title'>Signature Collection Progress</div>", unsafe_allow_html=True)
        for _, row in active_ballot.iterrows():
            sup = BALLOT_SUPPLEMENTS.get(row["metro_market"], {})
            with st.container():
                col_info, col_progress = st.columns([2, 3])
                with col_info:
                    st.markdown(
                        f"<div class='intel-card' style='margin-bottom:0;'>"
                        f"<div style='color:#E8EDF5;font-weight:700;font-size:0.92rem;margin-bottom:6px;'>"
                        f"{row['metro_market']} ({row['state_code']})</div>"
                        f"<div style='margin-bottom:4px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                        f"<div style='color:#7A9BBE;font-size:0.80rem;margin-top:6px;'>{row['category']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_progress:
                    if "signatures_collected" in sup:
                        collected = sup["signatures_collected"]
                        required  = sup["signatures_required"]
                        pct = min(collected / required, 1.0)
                        st.markdown(
                            f"<div style='margin-top:8px;'>"
                            f"<div style='display:flex;justify-content:space-between;color:#C8D8EE;"
                            f"font-size:0.82rem;margin-bottom:6px;'>"
                            f"<span>Signatures Collected</span>"
                            f"<span><strong style='color:#C9A84C;'>{collected:,}</strong>"
                            f" / {required:,} required</span></div>",
                            unsafe_allow_html=True,
                        )
                        st.progress(pct)
                        polling  = sup.get("polling", "N/A")
                        deadline = sup.get("deadline", "N/A")
                        lit      = sup.get("litigation", "None")
                        lit_risk = sup.get("litigation_risk", "Low")
                        lit_color = {"High": "#FF4B4B", "Medium": "#FFA500", "Low": "#21C55D"}.get(lit_risk, "#7A9BBE")
                        next_ms  = sup.get("next_milestone", "")
                        st.markdown(
                            f"<div style='font-size:0.80rem;color:#C8D8EE;margin-top:4px;'>"
                            f"<span style='color:#7A9BBE;'>Polling: </span>{polling} &nbsp;·&nbsp;"
                            f"<span style='color:#7A9BBE;'>Deadline: </span>{deadline}</div>"
                            f"<div style='font-size:0.80rem;margin-top:4px;'>"
                            f"<span style='color:#7A9BBE;'>Litigation: </span>"
                            f"<span style='color:{lit_color};font-weight:600;'>[{lit_risk}] </span>"
                            f"<span style='color:#C8D8EE;'>{lit}</span></div>"
                            f"{'<div style=\"font-size:0.78rem;color:#7A9BBE;margin-top:2px;\">Next: '+next_ms+'</div>' if next_ms else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='padding-top:12px;color:#C8D8EE;font-size:0.87rem;'>{row['summary_insight'][:280]}…</div>",
                            unsafe_allow_html=True,
                        )
                st.markdown("<hr>", unsafe_allow_html=True)

    # ── Candidate profiles ─────────────────────────────────────────────────
    cand_df = all_ballot[all_ballot["category"] == "Candidate Profiling"]
    if not cand_df.empty:
        st.markdown("<div class='section-title'>Candidate Profiles & Stance Rankings</div>", unsafe_allow_html=True)
        for _, row in cand_df.iterrows():
            sup = BALLOT_SUPPLEMENTS.get(row["metro_market"], {})
            r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
            with st.expander(
                f"🗳️  {sup.get('candidate', row['metro_market'])} — {row['state_code']} — {row['state_of_law']}",
                expanded=True,
            ):
                ca, cb, cc = st.columns(3)
                ca.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val'>{sup.get('polling', 'N/A')}</div>"
                    f"<div class='stat-lbl'>Polling Position</div></div>",
                    unsafe_allow_html=True,
                )
                cb.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val'>{sup.get('election_date', row['last_updated'][:10])}</div>"
                    f"<div class='stat-lbl'>Election Date</div></div>",
                    unsafe_allow_html=True,
                )
                cc.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val' style='color:{r_color};'>{row['portfolio_risk_impact']}</div>"
                    f"<div class='stat-lbl'>Portfolio Risk</div></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                pa, pb = st.columns(2)
                with pa:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Candidate Stance</div>"
                        f"<div style='color:#C8D8EE;font-size:0.87rem;line-height:1.6;'>"
                        f"{sup.get('stance', row['summary_insight'][:300])}</div>"
                        f"<div style='margin-top:10px;color:#7A9BBE;font-size:0.78rem;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>Endorsements</div>"
                        f"<div style='color:#2ECC71;font-size:0.85rem;'>{sup.get('endorsements', 'N/A')}</div>",
                        unsafe_allow_html=True,
                    )
                with pb:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Tickers at Risk</div>"
                        f"<div style='margin-bottom:10px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Industry Opposition</div>"
                        f"<div style='color:#FF7070;font-size:0.85rem;'>{sup.get('opposition', 'N/A')}</div>"
                        f"<div style='margin-top:10px;color:#7A9BBE;font-size:0.78rem;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>"
                        f"Risk If Elected</div>"
                        f"<div style='color:#FFA500;font-size:0.85rem;'>{sup.get('risk_if_elected', 'N/A')}</div>",
                        unsafe_allow_html=True,
                    )

    # ── Pending vote items ─────────────────────────────────────────────────
    pending_df = all_ballot[all_ballot["state_of_law"] == "Pending Vote"]
    if not pending_df.empty:
        st.markdown("<div class='section-title' style='margin-top:18px;'>Pending Legislative Votes</div>", unsafe_allow_html=True)
        for _, row in pending_df.iterrows():
            st.html(
                f"<div class='intel-card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                f"<div style='flex:1;'>"
                f"<div style='color:#E8EDF5;font-weight:700;font-size:0.92rem;margin-bottom:6px;'>{row['headline']}</div>"
                f"<div style='color:#C8D8EE;font-size:0.85rem;line-height:1.65;'>{row['summary_insight'][:400]}&#8230;</div>"
                f"</div><div style='margin-left:20px;text-align:right;white-space:nowrap;'>"
                f"{risk_badge(row['portfolio_risk_impact'])}<br>"
                f"<span style='color:#7A9BBE;font-size:0.75rem;'>{row['state_code']} &middot; {row['last_updated'][:10]}</span><br>"
                f"<div style='margin-top:6px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                f"</div></div></div>"
            )


    # ── Prediction Markets ─────────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title' style='margin-top:28px;'>Prediction Market Intelligence</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Live crowd-sourced probability estimates across housing policy, macro, and elections · "
        "Refreshes every 5 min</div>",
        unsafe_allow_html=True,
    )

    # ── Manifold Markets ───────────────────────────────────────────────────────
    st.markdown(
        _source_header("Manifold Markets", "https://manifold.markets",
                       "community prediction · housing / macro / Fed"),
        unsafe_allow_html=True,
    )
    manifold_data = fetch_manifold_odds()
    if not manifold_data:
        st.info("Manifold Markets unreachable or no relevant open markets found.")
    else:
        for mkt in manifold_data:
            traders = mkt.get("traders", 0)
            vol_label = f"Vol: M${mkt['volume']:,} · {traders} traders"
            cat_chip = (
                f"<span style='background:#0F2035;color:#7A9BBE;font-size:0.70rem;"
                f"padding:1px 6px;border-radius:3px;margin-right:6px;'>{mkt['category']}</span>"
            )
            card = _market_card(
                cat_chip + mkt["question"], mkt["prob"],
                mkt["end_date"], vol_label, mkt["url"],
            )
            st.markdown(card, unsafe_allow_html=True)

    # ── PredictIt ─────────────────────────────────────────────────────────────
    st.markdown(
        _source_header("PredictIt", "https://www.predictit.org",
                       "elections · congressional control · governor races"),
        unsafe_allow_html=True,
    )
    predictit_data = fetch_predictit_odds()
    if not predictit_data:
        st.info("PredictIt unreachable or no matching markets found.")
    else:
        for mkt in predictit_data:
            st.markdown(
                f"<div class='intel-card' style='padding:11px 15px;margin-bottom:7px;'>"
                f"<a href='{mkt['url']}' target='_blank' style='color:#C8D8EE;font-size:0.87rem;"
                f"font-weight:600;text-decoration:none;'>{mkt['question']}</a>",
                unsafe_allow_html=True,
            )
            cols = st.columns(min(len(mkt["contracts"]), 4))
            for col, c in zip(cols, mkt["contracts"]):
                color = _prob_color(c["prob"])
                prob_str = f"{c['prob']:.0f}%" if c["prob"] is not None else "—"
                col.markdown(
                    f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                    f"padding:8px 10px;text-align:center;'>"
                    f"<div style='font-size:1.15rem;font-weight:800;color:{color};'>{prob_str}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.72rem;margin-top:2px;'>{c['name'][:22]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Polymarket ────────────────────────────────────────────────────────────
    st.markdown(
        _source_header("Polymarket", "https://polymarket.com",
                       "high-liquidity · housing markets appear when ballot measures gain traction"),
        unsafe_allow_html=True,
    )
    poly_markets = fetch_polymarket_odds()
    if not poly_markets:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.83rem;padding:10px 0;'>"
            "No active Polymarket markets matched housing/macro keywords right now. "
            "Polymarket covers these when ballot measures gain national traction — "
            "check back closer to November 2026.</div>",
            unsafe_allow_html=True,
        )
    else:
        for mkt in poly_markets:
            vol_label = f"Vol: ${mkt['volume']:,}" if mkt["volume"] else "—"
            st.markdown(
                _market_card(mkt["question"], mkt["prob"], mkt["end_date"],
                             vol_label, mkt["url"]),
                unsafe_allow_html=True,
            )

    # ── Metaculus link card ────────────────────────────────────────────────────
    st.markdown(
        "<div style='margin-top:18px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='intel-card' style='padding:12px 16px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;'>"
        "<div>"
        "<div style='color:#E8EDF5;font-weight:700;font-size:0.90rem;margin-bottom:4px;'>Metaculus</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;'>"
        "Researcher-grade forecasting with structured resolution criteria · "
        "Covers housing policy, Fed decisions, and macroeconomic questions · "
        "Requires free account for API access.</div>"
        "</div>"
        "<a href='https://www.metaculus.com/questions/?search=housing' target='_blank' "
        "style='color:#4A90D9;font-size:0.82rem;white-space:nowrap;margin-left:16px;'>Browse ↗</a>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # ── Kalshi ────────────────────────────────────────────────────────────────
    st.markdown(
        _source_header("Kalshi", "https://kalshi.com",
                       "regulated exchange · Fed rate · CPI · GDP · existing home sales"),
        unsafe_allow_html=True,
    )
    kalshi_data = fetch_kalshi_odds()
    if not kalshi_data:
        st.info("Kalshi unreachable or no open macro markets found.")
    else:
        current_series = None
        for mkt in kalshi_data:
            if mkt["series"] != current_series:
                current_series = mkt["series"]
                st.markdown(
                    f"<div style='color:#C9A84C;font-size:0.76rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.06em;margin:14px 0 6px;'>"
                    f"{current_series}</div>",
                    unsafe_allow_html=True,
                )
            vol_label = f"Closes: {mkt['close']}" if mkt["close"] else ""
            st.markdown(
                _market_card(mkt["title"], mkt["prob"], mkt["close"], vol_label, mkt["url"]),
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — LIVE NEWS TERMINAL
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown(
        "<div class='section-title'>Live Regulatory News Terminal</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Real-time headlines from Google News · Sorted by most recent · Click 🔍 to open Audit Panel</div>",
        unsafe_allow_html=True,
    )

    # ── Live scraped news ──────────────────────────────────────────────────────
    col_live_hdr, col_live_refresh = st.columns([6, 1])
    with col_live_hdr:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
            "<span style='background:#FF4B4B;color:#fff;font-size:0.68rem;font-weight:800;"
            "padding:3px 8px;border-radius:4px;letter-spacing:0.08em;'>● LIVE</span>"
            "<span style='color:#7A9BBE;font-size:0.80rem;'>Google News · refreshes every 5 min</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col_live_refresh:
        if st.button("↻ Refresh", key="refresh_live_news"):
            st.cache_data.clear()
            st.rerun()

    live_df = fetch_live_news()

    # Filter live news by selected tickers if a specific filter is active
    selected_tickers = st.session_state.get("_sidebar_tickers", ALL_TICKERS)
    if live_df.empty:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.84rem;padding:12px 0 20px 0;'>"
            "⚠ Could not fetch live news (check your internet connection).</div>",
            unsafe_allow_html=True,
        )
    else:
        # Filter to selected tickers when user has narrowed the filter
        active_tickers = st.session_state.get("_sidebar_tickers", ALL_TICKERS)
        if set(active_tickers) != set(ALL_TICKERS):
            ticker_set = set(active_tickers)
            live_df = live_df[
                live_df["tickers_exposed"].apply(
                    lambda c: bool(ticker_set & set(str(c).split(","))) if c else True
                )
            ]

        for _, lrow in live_df.iterrows():
            ticker_str = str(lrow["tickers_exposed"])
            chips_html = ticker_chips(ticker_str) if ticker_str else ""
            source_url = lrow.get("url", "")
            link_html = (
                f"<a href='{source_url}' target='_blank' "
                f"style='color:#C9A84C;font-size:0.75rem;text-decoration:none;margin-left:8px;'>↗ Source</a>"
                if source_url else ""
            )
            st.html(
                f"<div class='news-card' style='border-left:3px solid #1E90FF;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                f"<span style='color:#C9A84C;font-size:0.72rem;text-transform:uppercase;"
                f"font-weight:700;letter-spacing:0.07em;'>{lrow['source_name']}</span>"
                f"<span style='color:#7A9BBE;font-size:0.72rem;'>{lrow['published']}</span>"
                f"</div>"
                f"<div style='font-size:0.98rem;font-weight:700;color:#E8EDF5;"
                f"line-height:1.45;margin-bottom:8px;'>{lrow['headline']}{link_html}</div>"
                f"<div style='font-size:0.84rem;color:#A8BDD4;line-height:1.6;margin-bottom:10px;'>"
                f"{lrow['summary']}</div>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;'>"
                f"<span style='background:#0B1E33;color:#1E90FF;padding:3px 9px;border-radius:20px;"
                f"font-size:0.72rem;font-weight:700;border:1px solid #1E3A5F;'>LIVE</span>"
                f"{chips_html}"
                f"</div>"
                f"</div>"
            )

    st.markdown(
        "<hr style='border-color:#1B3150;margin:24px 0 18px 0;'>"
        "<div style='color:#7A9BBE;font-size:0.78rem;margin-bottom:14px;'>"
        "▼ &nbsp;INTELLIGENCE DATABASE — verified entries with audit trails</div>",
        unsafe_allow_html=True,
    )

    # ── DB intelligence entries ────────────────────────────────────────────────
    if filtered_df.empty:
        st.info("No news items match the current filter.")
    else:
        for _, row in filtered_df.sort_values("last_updated", ascending=False).iterrows():
            card_class = {
                "Critical":   "news-card critical",
                "Moderate":   "news-card moderate",
                "Low/Stable": "news-card stable",
            }.get(row["portfolio_risk_impact"], "news-card")

            col_card, col_btn = st.columns([16, 1])
            with col_card:
                summary_trunc = str(row["summary_insight"])[:320]
                if len(str(row["summary_insight"])) > 320:
                    summary_trunc += "&#8230;"
                st.html(
                    f'<div class="{card_class}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<span style="color:#C9A84C;font-size:0.72rem;text-transform:uppercase;font-weight:700;letter-spacing:0.07em;">{row["source_name"]}</span>'
                    f'<span style="color:#7A9BBE;font-size:0.72rem;">{row["last_updated"]}</span>'
                    f'</div>'
                    f'<div style="font-size:1.0rem;font-weight:700;color:#E8EDF5;line-height:1.45;margin-bottom:10px;">{row["headline"]}</div>'
                    f'<div style="font-size:0.86rem;color:#A8BDD4;line-height:1.65;margin-bottom:12px;">{summary_trunc}</div>'
                    f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
                    f'{sent_badge(row["sentiment_score"])}'
                    f'{risk_badge(row["portfolio_risk_impact"])}'
                    f'{ticker_chips(row["tickers_exposed"])}'
                    f'<span style="background:#0C1929;color:#7A9BBE;padding:3px 10px;border-radius:20px;font-size:0.75rem;">'
                    f'{row["state_code"]} &middot; {row["metro_market"]}'
                    f'</span>'
                    f'</div>'
                    f'</div>'
                )
            with col_btn:
                st.markdown("<div style='height:52px;'></div>", unsafe_allow_html=True)
                if st.button("🔍", key=f"a4_{row['id']}", help="Open audit trail"):
                    st.session_state["audit_row_id"] = int(row["id"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MARKET-BY-MARKET ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("<div class='section-title'>Market-by-Market Legislative Analysis</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.82rem;margin-bottom:18px;'>"
        "Comprehensive analysis per market with sentiment assessment, legislative context, "
        "portfolio impact, and primary source citations.</div>",
        unsafe_allow_html=True,
    )

    # Group by state for organized display
    if df_all.empty:
        st.warning("No data loaded.")
    else:
        ma_search = st.text_input(
            "Search markets...",
            placeholder="e.g. California, CSR, Algorithmic, Critical",
            label_visibility="collapsed",
        )

        ma_df = df_all.copy()
        if ma_search.strip():
            q = ma_search.strip().lower()
            mask = (
                ma_df["metro_market"].str.lower().str.contains(q, na=False) |
                ma_df["state_code"].str.lower().str.contains(q, na=False) |
                ma_df["tickers_exposed"].str.lower().str.contains(q, na=False) |
                ma_df["category"].str.lower().str.contains(q, na=False) |
                ma_df["portfolio_risk_impact"].str.lower().str.contains(q, na=False) |
                ma_df["summary_insight"].str.lower().str.contains(q, na=False)
            )
            ma_df = ma_df[mask]

        if ma_df.empty:
            st.info(f"No results for '{ma_search}'")
        else:
            # Sort: Critical first, then by state
            risk_order = {"Critical": 0, "Moderate": 1, "Low/Stable": 2}
            ma_df["_risk_ord"] = ma_df["portfolio_risk_impact"].map(risk_order).fillna(3)
            ma_df = ma_df.sort_values(["_risk_ord", "state_code", "metro_market"])

            states_in_df = ma_df["state_code"].unique()

            for state in states_in_df:
                state_rows = ma_df[ma_df["state_code"] == state]
                avg_sent = state_rows["sentiment_score"].mean()
                risk_summary = state_rows["portfolio_risk_impact"].value_counts().to_dict()
                risk_display = " · ".join(
                    f"<span style='color:{RISK_COLORS.get(k, '#7A9BBE')};font-weight:700;'>{v} {k}</span>"
                    for k, v in risk_summary.items()
                )
                sent_clr = sentiment_color(avg_sent)

                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:12px;margin:20px 0 10px 0;"
                    f"border-top:1px solid #1B3150;padding-top:16px;'>"
                    f"<span style='color:#C9A84C;font-size:1.3rem;font-weight:800;'>{state}</span>"
                    f"<span style='color:#D4DCE8;font-size:0.85rem;'>{len(state_rows)} market{'s' if len(state_rows)>1 else ''}</span>"
                    f"<span style='color:{sent_clr};font-size:0.85rem;font-weight:700;'>Avg Sentiment: {avg_sent:+.2f}</span>"
                    f"<span style='font-size:0.82rem;'>{risk_display}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                for _, row in state_rows.iterrows():
                    r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
                    s_color = sentiment_color(row["sentiment_score"])

                    # Sentiment gauge (simple visual bar)
                    gauge_pct = int((row["sentiment_score"] + 1.0) / 2.0 * 100)
                    gauge_color = s_color

                    source_link = (
                        f'<a href="{row["source_url"]}" target="_blank" '
                        f'style="color:#C9A84C;font-size:0.78rem;font-weight:600;text-decoration:none;">'
                        f'&#128279; View Primary Source</a>'
                        if row["source_url"] else ""
                    )
                    card_html = (
                        f'<div class="market-card">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">'
                        f'<div>'
                        f'<div style="color:#E8EDF5;font-size:1.0rem;font-weight:700;margin-bottom:4px;">{row["metro_market"]}</div>'
                        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px;">'
                        f'{sol_badge(row["state_of_law"])}'
                        f'{risk_badge(row["portfolio_risk_impact"])}'
                        f'<span style="color:#7A9BBE;font-size:0.78rem;">{row["category"]}</span>'
                        f'</div>'
                        f'<div>{ticker_chips(row["tickers_exposed"])}</div>'
                        f'</div>'
                        f'<div style="text-align:right;min-width:140px;">'
                        f'<div style="color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Sentiment Score</div>'
                        f'<div style="font-size:1.6rem;font-weight:700;color:{s_color};">{row["sentiment_score"]:+.2f}</div>'
                        f'<div style="background:#1B3150;border-radius:99px;height:6px;margin-top:6px;width:130px;">'
                        f'<div style="background:{gauge_color};border-radius:99px;height:6px;width:{gauge_pct}%;"></div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;color:#7A9BBE;font-size:0.68rem;margin-top:2px;">'
                        f'<span>&#8722;1.0</span><span>+1.0</span>'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                        f'<div style="color:#C8D8EE;font-size:0.87rem;line-height:1.70;margin-bottom:14px;">{row["summary_insight"]}</div>'
                        f'<div style="background:#060D1A;border-left:3px solid #C9A84C;border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;">'
                        f'<div style="color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;font-weight:700;letter-spacing:0.06em;margin-bottom:6px;">Verbatim Legislative Text</div>'
                        f'<div style="color:#B8CCE4;font-size:0.84rem;font-style:italic;line-height:1.7;">'
                        f'&#8220;{row["exact_text_quote"]}&#8221;'
                        f'</div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
                        f'<div style="font-size:0.78rem;">'
                        f'<span style="color:#7A9BBE;">Source: </span>'
                        f'<span style="color:#C9A84C;font-weight:600;">{row["source_name"]}</span>'
                        f'</div>'
                        f'<div style="display:flex;gap:12px;align-items:center;">'
                        f'<span style="color:#7A9BBE;font-size:0.75rem;">Updated: {row["last_updated"][:10]}</span>'
                        f'{source_link}'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )
                    st.html(card_html)

                    mc1c, mc2c = st.columns([12, 1])
                    with mc2c:
                        if st.button("Audit", key=f"a5_{row['id']}"):
                            st.session_state["audit_row_id"] = int(row["id"])


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT ENGINE — Sidebar
# ══════════════════════════════════════════════════════════════════════════════

def render_audit_panel(df: pd.DataFrame) -> None:
    audit_id = st.session_state.get("audit_row_id")
    if audit_id is None:
        return
    row_matches = df[df["id"] == audit_id]
    if row_matches.empty:
        st.sidebar.warning("Audit target not found.")
        return
    row = row_matches.iloc[0]
    r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
    s_color = sentiment_color(row["sentiment_score"])

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='color:#C9A84C;font-weight:700;font-size:0.9rem;"
        "border-bottom:1px solid #1B3150;padding-bottom:8px;margin-bottom:12px;'>"
        "🔍 Audit Verification Panel</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:2px;'>Verified Source</div>"
        f"<div style='color:#E8EDF5;font-weight:600;font-size:0.88rem;margin-bottom:10px;'>"
        f"{row['source_name']}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:4px;'>Live Source Link</div>",
        unsafe_allow_html=True,
    )
    if row["source_url"]:
        st.sidebar.markdown(f"[🔗 Open Primary Source →]({row['source_url']})")
    else:
        st.sidebar.markdown("_No URL recorded_")

    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-top:10px;margin-bottom:2px;'>"
        "Verification Timestamp</div>"
        f"<code style='color:#C9A84C;font-size:0.82rem;'>{row['last_updated']}</code>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<div style='background:#060D1A;border:1px solid #1B3150;border-radius:8px;"
        f"padding:12px;font-size:0.82rem;margin:10px 0;'>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Market: </span>"
        f"<span style='color:#E8EDF5;font-weight:600;'>{row['metro_market']} ({row['state_code']})</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Tickers: </span>"
        f"<span style='color:#C9A84C;font-weight:700;'>{row['tickers_exposed']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Category: </span>"
        f"<span style='color:#C8D8EE;'>{row['category']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Status: </span>"
        f"<span style='color:{SOL_COLORS.get(row['state_of_law'], '#7A9BBE')};font-weight:600;'>"
        f"{row['state_of_law']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Risk: </span>"
        f"<span style='color:{r_color};font-weight:700;'>{row['portfolio_risk_impact']}</span></div>"
        f"<div><span style='color:#7A9BBE;'>Sentiment: </span>"
        f"<span style='color:{s_color};font-weight:700;'>{row['sentiment_score']:+.3f}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:4px;'>"
        "Verbatim Source Text Used by AI</div>",
        unsafe_allow_html=True,
    )
    quote = row["exact_text_quote"] if row["exact_text_quote"] else "_No verbatim extract recorded._"
    st.sidebar.markdown(
        f"<div class='audit-quote'>&ldquo;{quote}&rdquo;</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin:8px 0 2px 0;'>Processed Headline</div>"
        f"<div style='color:#C8D8EE;font-size:0.84rem;font-style:italic;line-height:1.6;'>"
        f"{row['headline']}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("✕ Close Audit Panel", key="clear_audit"):
        del st.session_state["audit_row_id"]
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — NATION VIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown(
        "<div class='section-title'>Nation View — City & State Election Intelligence</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Upcoming elections across all REIT-relevant markets, organized by city. "
        "Covers mayors, governors, state legislators, and ballot measures that drive rent-control risk.</div>",
        unsafe_allow_html=True,
    )

    # ── Risk legend + filter ───────────────────────────────────────────────────
    nv_col_filter, nv_col_legend = st.columns([3, 2])
    with nv_col_filter:
        nv_risk_filter = st.multiselect(
            "Filter by Risk Level",
            ["Critical", "Moderate", "Low/Stable"],
            default=["Critical", "Moderate", "Low/Stable"],
            key="nv_risk",
        )
    with nv_col_legend:
        st.markdown(
            "<div style='display:flex;gap:16px;padding-top:28px;flex-wrap:wrap;'>"
            "<span style='color:#FF4B4B;font-size:0.80rem;font-weight:700;'>● Critical</span>"
            "<span style='color:#FFA500;font-size:0.80rem;font-weight:700;'>● Moderate</span>"
            "<span style='color:#21C55D;font-size:0.80rem;font-weight:700;'>● Low/Stable</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Governor races 2026 strip ───────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>2026 Gubernatorial Races — State-Level REIT Policy Risk</div>",
        unsafe_allow_html=True,
    )
    gov_risk_filter = [r for r in nv_risk_filter]
    gov_rows = [(state, info) for state, info in GOVERNOR_RACES_2026.items()
                if info["risk"] in gov_risk_filter]
    if gov_rows:
        for i in range(0, len(gov_rows), 3):
            chunk = gov_rows[i:i+3]
            cols = st.columns(len(chunk))
            for col, (state, info) in zip(cols, chunk):
                r_color = RISK_COLORS.get(info["risk"], "#7A9BBE")
                col.markdown(
                    f"<div class='intel-card' style='padding:12px 14px;height:100%;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                    f"<span style='color:#C9A84C;font-size:1.1rem;font-weight:800;'>{state}</span>"
                    f"<span style='color:{r_color};font-size:0.72rem;font-weight:700;'>{info['risk']}</span>"
                    f"</div>"
                    f"<div style='color:#E8EDF5;font-size:0.80rem;font-weight:600;margin-bottom:6px;'>"
                    f"{info['candidates']}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.75rem;line-height:1.5;'>{info['note']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    # ── City-by-city election calendar ─────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>City Election Calendar — Mayor, Council & Local Ballot</div>",
        unsafe_allow_html=True,
    )

    filtered_cities = {
        city: info for city, info in CITY_ELECTION_CALENDAR.items()
        if info["risk"] in nv_risk_filter
    }
    risk_sort = {"Critical": 0, "Moderate": 1, "Low/Stable": 2}
    sorted_cities = sorted(filtered_cities.items(), key=lambda x: risk_sort.get(x[1]["risk"], 3))

    for city, info in sorted_cities:
        r_color = RISK_COLORS.get(info["risk"], "#7A9BBE")
        sol_color = SOL_COLORS.get(info["rent_control_law"], "#7A9BBE")

        with st.expander(
            f"{city}, {info['state']}  —  {info['risk']}  —  {info['rent_control_law']}",
            expanded=(info["risk"] == "Critical"),
        ):
            hdr_col, tickers_col = st.columns([3, 2])
            with hdr_col:
                st.markdown(
                    f"<div style='color:{r_color};font-size:0.78rem;font-weight:700;margin-bottom:6px;'>"
                    f"{info['policy_note']}</div>",
                    unsafe_allow_html=True,
                )
            with tickers_col:
                st.markdown(
                    "<div style='color:#7A9BBE;font-size:0.73rem;margin-bottom:4px;'>Tickers Exposed</div>"
                    + ticker_chips(",".join(info["tickers"])),
                    unsafe_allow_html=True,
                )

            for election in info["elections"]:
                status_color = {"Completed": "#21C55D", "Upcoming": "#FFA500"}.get(
                    election["status"], "#7A9BBE"
                )
                st.markdown(
                    f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                    f"padding:10px 14px;margin-bottom:8px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                    f"<span style='color:#E8EDF5;font-weight:700;font-size:0.88rem;'>{election['office']}</span>"
                    f"<div style='display:flex;gap:10px;align-items:center;'>"
                    f"<span style='color:#7A9BBE;font-size:0.78rem;'>{election['date']}</span>"
                    f"<span style='color:{status_color};font-size:0.72rem;font-weight:700;'>"
                    f"{election['status'].upper()}</span>"
                    f"</div></div>"
                    f"<div style='color:#C8D8EE;font-size:0.82rem;line-height:1.55;'>{election['note']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Macro calendar (Kalshi) ────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title' style='margin-top:28px;'>Macro Event Calendar — Kalshi Market Odds</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:14px;'>"
        "Fed rate decisions, CPI prints, GDP releases, and home sales data — the macro drivers of REIT valuations.</div>",
        unsafe_allow_html=True,
    )
    kalshi_nation = fetch_kalshi_odds()
    if not kalshi_nation:
        st.info("Kalshi unreachable.")
    else:
        nv_series = None
        for mkt in kalshi_nation:
            if mkt["series"] != nv_series:
                nv_series = mkt["series"]
                st.markdown(
                    f"<div style='color:#C9A84C;font-size:0.78rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.06em;margin:16px 0 6px;'>"
                    f"{nv_series}</div>",
                    unsafe_allow_html=True,
                )
            color = _prob_color(mkt["prob"])
            prob_str = f"{mkt['prob']:.1f}%" if mkt["prob"] is not None else "—"
            st.markdown(
                f"<div class='intel-card' style='padding:10px 14px;margin-bottom:6px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div style='flex:1;'>"
                f"<a href='{mkt['url']}' target='_blank' style='color:#C8D8EE;font-size:0.85rem;"
                f"font-weight:600;text-decoration:none;'>{mkt['title']}</a>"
                f"<div style='color:#7A9BBE;font-size:0.73rem;margin-top:3px;'>Closes: {mkt['close'] or '—'}</div>"
                f"</div>"
                f"<div style='color:{color};font-size:1.3rem;font-weight:800;margin-left:16px;white-space:nowrap;'>"
                f"{prob_str}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — REIT PROFILES & COMPS
# ══════════════════════════════════════════════════════════════════════════════

with tab7:
    st.markdown(
        "<div class='section-title'>REIT Profiles & Comparison</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Search any tracked ticker to see all exposure, risk items, and prediction market data. "
        "Select two tickers to compare side-by-side.</div>",
        unsafe_allow_html=True,
    )

    rp_mode = st.radio(
        "Mode", ["Single Ticker Profile", "Side-by-Side Comparison"],
        horizontal=True, label_visibility="collapsed", key="rp_mode",
    )

    def _ticker_profile(ticker: str, df: pd.DataFrame, col=None):
        ctx = col if col else st
        name = TICKER_NAMES.get(ticker, ticker)
        rows = df[df["tickers_exposed"].str.contains(ticker, na=False)].copy()
        rows["_risk_ord"] = rows["portfolio_risk_impact"].map(
            {"Critical": 0, "Moderate": 1, "Low/Stable": 2}
        ).fillna(3)
        rows = rows.sort_values(["_risk_ord", "state_code"])

        critical = int((rows["portfolio_risk_impact"] == "Critical").sum())
        moderate = int((rows["portfolio_risk_impact"] == "Moderate").sum())
        stable   = int((rows["portfolio_risk_impact"] == "Low/Stable").sum())
        avg_sent = rows["sentiment_score"].mean() if not rows.empty else 0.0
        states   = sorted(rows["state_code"].unique().tolist())

        ctx.markdown(
            f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:8px;"
            f"padding:14px 18px;margin-bottom:16px;'>"
            f"<div style='color:#C9A84C;font-size:1.3rem;font-weight:800;'>{ticker}</div>"
            f"<div style='color:#7A9BBE;font-size:0.82rem;margin-top:2px;'>{name}</div>"
            f"<div style='display:flex;gap:20px;margin-top:12px;flex-wrap:wrap;'>"
            f"<div><div style='color:#FF4B4B;font-size:1.4rem;font-weight:800;'>{critical}</div>"
            f"<div style='color:#7A9BBE;font-size:0.72rem;'>Critical Items</div></div>"
            f"<div><div style='color:#FFA500;font-size:1.4rem;font-weight:800;'>{moderate}</div>"
            f"<div style='color:#7A9BBE;font-size:0.72rem;'>Moderate Items</div></div>"
            f"<div><div style='color:#21C55D;font-size:1.4rem;font-weight:800;'>{stable}</div>"
            f"<div style='color:#7A9BBE;font-size:0.72rem;'>Stable Items</div></div>"
            f"<div><div style='color:{sentiment_color(avg_sent)};font-size:1.4rem;font-weight:800;'>"
            f"{avg_sent:+.2f}</div>"
            f"<div style='color:#7A9BBE;font-size:0.72rem;'>Avg Sentiment</div></div>"
            f"<div><div style='color:#C8D8EE;font-size:1.0rem;font-weight:700;margin-top:4px;'>"
            f"{', '.join(states) if states else 'N/A'}</div>"
            f"<div style='color:#7A9BBE;font-size:0.72rem;'>States Tracked</div></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        # Risk breakdown bar
        total = critical + moderate + stable
        if total > 0:
            crit_pct = critical / total * 100
            mod_pct  = moderate / total * 100
            stab_pct = stable   / total * 100
            ctx.markdown(
                f"<div style='margin-bottom:14px;'>"
                f"<div style='color:#7A9BBE;font-size:0.72rem;margin-bottom:4px;'>Risk Distribution</div>"
                f"<div style='display:flex;border-radius:4px;overflow:hidden;height:10px;'>"
                f"<div style='background:#FF4B4B;width:{crit_pct:.1f}%;'></div>"
                f"<div style='background:#FFA500;width:{mod_pct:.1f}%;'></div>"
                f"<div style='background:#21C55D;width:{stab_pct:.1f}%;'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        # Category breakdown
        if not rows.empty:
            cat_counts = rows["category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig_cat = px.bar(
                cat_counts, x="Count", y="Category", orientation="h",
                color="Count", color_continuous_scale=["#1E90FF", "#FF4B4B"],
                template="plotly_dark",
            )
            fig_cat.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=11),
                margin=dict(l=0, r=10, t=10, b=10), height=200,
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(gridcolor="#1B3150"),
                yaxis=dict(gridcolor="#0C1929", title=""),
            )
            ctx.plotly_chart(fig_cat, use_container_width=True)

        # 1-Year price chart
        prices_df = fetch_reit_prices()
        if not prices_df.empty and ticker in prices_df.columns:
            price_series = prices_df[ticker].dropna().reset_index()
            price_series.columns = ["date", "value"]
            info_d = fetch_reit_info().get(ticker, {})
            current_p = info_d.get("last_price")
            start_p   = price_series["value"].iloc[0] if not price_series.empty else None
            ytd_ret   = (current_p / start_p - 1) * 100 if current_p and start_p else None
            line_color = "#21C55D" if (ytd_ret or 0) >= 0 else "#FF4B4B"

            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(
                x=price_series["date"], y=price_series["value"],
                mode="lines", line=dict(color=line_color, width=2),
                fill="tozeroy",
                fillcolor=line_color.replace("#", "rgba(").replace("FF4B4B","255,75,75,0.08)").replace("21C55D","33,197,93,0.08)"),
                hovertemplate="%{x|%b %d %Y}: $%{y:.2f}<extra></extra>",
                name=ticker,
            ))
            ret_label = f"{ytd_ret:+.1f}% (1Y)" if ytd_ret is not None else ""
            fig_price.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=11),
                margin=dict(l=10, r=10, t=26, b=10), height=180,
                showlegend=False,
                title=dict(text=f"{ticker} — 1 Year Price  {ret_label}",
                           font=dict(color="#7A9BBE", size=11), x=0),
                xaxis=dict(gridcolor="#1B3150", tickfont=dict(color="#7A9BBE", size=10)),
                yaxis=dict(gridcolor="#1B3150", tickfont=dict(color="#7A9BBE", size=10),
                           tickprefix="$"),
            )
            ctx.plotly_chart(fig_price, use_container_width=True,
                             config={"displayModeBar": False})

        # All tracked items
        ctx.markdown(
            f"<div style='color:#7A9BBE;font-size:0.73rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.05em;margin:10px 0 8px;'>All Tracked Intelligence Items</div>",
            unsafe_allow_html=True,
        )
        for _, row in rows.iterrows():
            r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
            ctx.markdown(
                f"<div class='intel-card' style='padding:10px 14px;margin-bottom:6px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:12px;'>"
                f"<div style='flex:1;'>"
                f"<div style='color:#E8EDF5;font-size:0.86rem;font-weight:600;margin-bottom:4px;'>"
                f"{row['headline']}</div>"
                f"<div style='color:#C8D8EE;font-size:0.78rem;line-height:1.5;'>"
                f"{str(row['summary_insight'])[:280]}…</div>"
                f"<div style='color:#7A9BBE;font-size:0.72rem;margin-top:4px;'>"
                f"{row['state_code']} · {row['metro_market']} · {row['category']} · {row['last_updated'][:10]}</div>"
                f"</div>"
                f"<div style='text-align:right;white-space:nowrap;'>"
                f"{risk_badge(row['portfolio_risk_impact'])}<br>"
                f"{sol_badge(row['state_of_law'])}"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )

        # Prediction markets mentioning this ticker's key states
        ticker_states = set(rows["state_code"].unique()) if not rows.empty else set()
        manifold_hits = [
            m for m in fetch_manifold_odds()
            if any(st_name.lower() in m["question"].lower()
                   for st_name in list(ticker_states)[:5])
               or ticker.lower() in m["question"].lower()
        ]
        if manifold_hits:
            ctx.markdown(
                "<div style='color:#7A9BBE;font-size:0.73rem;font-weight:700;text-transform:uppercase;"
                "letter-spacing:0.05em;margin:14px 0 6px;'>Related Prediction Markets (Manifold)</div>",
                unsafe_allow_html=True,
            )
            for mkt in manifold_hits[:4]:
                ctx.markdown(
                    _market_card(mkt["question"], mkt["prob"], mkt["end_date"],
                                 f"Vol M${mkt['volume']:,}", mkt["url"]),
                    unsafe_allow_html=True,
                )

    # ── Single profile ─────────────────────────────────────────────────────────
    _profile_tickers = st.session_state.get("_sidebar_tickers", ALL_TICKERS)
    if rp_mode == "Single Ticker Profile":
        selected = st.selectbox(
            "Select Ticker", _profile_tickers,
            format_func=lambda t: f"{t} — {TICKER_NAMES.get(t, t)}",
            key="rp_single",
        )
        _ticker_profile(selected, df_all)

    # ── Side-by-side comparison ────────────────────────────────────────────────
    else:
        cc1, cc2 = st.columns(2)
        with cc1:
            t1 = st.selectbox(
                "Ticker A", _profile_tickers,
                format_func=lambda t: f"{t} — {TICKER_NAMES.get(t, t)}",
                key="rp_comp_a", index=0,
            )
        with cc2:
            t2 = st.selectbox(
                "Ticker B", _profile_tickers,
                format_func=lambda t: f"{t} — {TICKER_NAMES.get(t, t)}",
                key="rp_comp_b", index=min(1, len(_profile_tickers) - 1),
            )

        if t1 == t2:
            st.warning("Select two different tickers to compare.")
        else:
            left, right = st.columns(2)
            _ticker_profile(t1, df_all, col=left)
            _ticker_profile(t2, df_all, col=right)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — POWER & GRID TRACKER
# ══════════════════════════════════════════════════════════════════════════════

with tab_grid:
    st.markdown(
        "<div class='section-title'>⚡ State Power & Grid Intelligence</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Monitor grid operator constraints, legislative moratoriums, ratepayer protection bills, "
        "and live utility news across all 50 US states. Updated every 5 minutes. "
        "Sourced from FERC filings, state PUC dockets, and live RSS feeds.</div>",
        unsafe_allow_html=True,
    )

    # ── Section A: Global Metrics ─────────────────────────────────────────────
    _pg_moratoriums = sum(1 for s in POWER_GRID_STATES.values() if s["moratorium"])
    _pg_ratepayer   = sum(1 for s in POWER_GRID_STATES.values() if s["ratepayer_bill"])
    _pg_high_risk   = sum(1 for s in POWER_GRID_STATES.values() if s["risk_level"] == "High")

    gm1, gm2, gm3 = st.columns(3)
    gm1.metric("⛔ Active Moratoriums", _pg_moratoriums,
               help="States with active data center construction moratoriums")
    gm2.metric("⚖️ Ratepayer Bill States", _pg_ratepayer,
               help="States with active ratepayer protection bills requiring tech companies to fund grid upgrades")
    gm3.metric("🔴 High-Risk States", _pg_high_risk,
               help="States with elevated legislative or grid capacity risk for data center operators")

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    # ── Section B: State Selector ─────────────────────────────────────────────
    _pg_risk_order = {"High": 0, "Moderate": 1, "Low": 2}
    _pg_state_options = sorted(
        POWER_GRID_STATES.keys(),
        key=lambda k: (_pg_risk_order.get(POWER_GRID_STATES[k]["risk_level"], 3), k),
    )

    _pg_sel = st.selectbox(
        "Select a State to Inspect",
        options=_pg_state_options,
        format_func=lambda k: f"{POWER_GRID_STATES[k]['name']} ({k})  [{POWER_GRID_STATES[k]['risk_level']} Risk]",
        key="grid_state_select",
    )

    _gs = POWER_GRID_STATES[_pg_sel]
    _gs_risk_color = {"High": "#FF4B4B", "Moderate": "#FFA500", "Low": "#21C55D"}.get(_gs["risk_level"], "#7A9BBE")
    _gs_risk_css   = {"High": "risk-critical", "Moderate": "risk-moderate", "Low": "risk-low"}.get(_gs["risk_level"], "risk-low")

    # State summary card
    _moratorium_badge = (
        "<br><span style=\"color:#FF4B4B;font-size:0.72rem;margin-top:6px;display:inline-block;\">⛔ MORATORIUM ACTIVE</span>"
        if _gs["moratorium"] else ""
    )
    _ratepayer_badge = (
        "<br><span style=\"color:#FFA500;font-size:0.72rem;margin-top:6px;display:inline-block;\">⚖️ RATEPAYER BILL</span>"
        if _gs["ratepayer_bill"] else ""
    )
    _hub_badge = (
        "<br><span style=\"color:#C9A84C;font-size:0.72rem;margin-top:6px;display:inline-block;\">🏢 DC HUB STATE</span>"
        if _gs["dc_hub"] else ""
    )

    st.markdown(
        f"<div style='background:linear-gradient(140deg,#0B1A2D 0%,#0F2035 100%);"
        f"border:1px solid #1D3450;border-left:4px solid {_gs_risk_color};"
        f"border-radius:12px;padding:18px 24px;margin-bottom:18px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div>"
        f"<div style='color:#C9A84C;font-size:1.15rem;font-weight:800;'>{_gs['name']} ({_pg_sel})</div>"
        f"<div style='color:#7A9BBE;font-size:0.82rem;margin-top:4px;'>Grid Operator: "
        f"<span style='color:#C8D8EE;font-weight:600;'>{_gs['grid_operator']}</span></div>"
        f"</div>"
        f"<div style='text-align:right;'>"
        f"<span class='risk-tag {_gs_risk_css}'>{_gs['risk_level']} Risk</span>"
        f"{_moratorium_badge}{_ratepayer_badge}{_hub_badge}"
        f"</div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Section C: Four Expanders ─────────────────────────────────────────────

    with st.expander("🟢 Grid Supply & Capacity Outlook", expanded=True):
        _exp_left, _exp_right = st.columns([3, 1])
        with _exp_left:
            st.markdown(
                f"<div style='color:#C8D8EE;font-size:0.90rem;line-height:1.80;'>{_gs['power_outlook']}</div>",
                unsafe_allow_html=True,
            )
        with _exp_right:
            _rv_map = {"High": 3, "Moderate": 2, "Low": 1}
            _rv = _rv_map.get(_gs["risk_level"], 1)
            _risk_fig = go.Figure(go.Bar(
                x=["Risk Score"], y=[_rv],
                marker_color=_gs_risk_color,
                text=[_gs["risk_level"]], textposition="inside",
                textfont=dict(color="#FFFFFF", size=12, family="Inter"),
            ))
            _risk_fig.update_layout(
                paper_bgcolor="#0B1A2D", plot_bgcolor="#0B1A2D",
                margin=dict(l=10, r=10, t=10, b=10), height=110,
                showlegend=False,
                yaxis=dict(range=[0, 3.5], visible=False),
                xaxis=dict(visible=False),
            )
            st.plotly_chart(_risk_fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                f"<div style='text-align:center;margin-top:-8px;'>"
                f"<div style='color:#7A9BBE;font-size:0.70rem;text-transform:uppercase;letter-spacing:0.07em;'>Grid Operator</div>"
                f"<div style='color:#C9A84C;font-size:0.80rem;font-weight:700;margin-top:3px;'>{_gs['grid_operator']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with st.expander("📜 Legislative Climate", expanded=False):
        st.markdown(
            f"<div style='color:#C8D8EE;font-size:0.90rem;line-height:1.80;margin-bottom:14px;'>"
            f"{_gs['legislative_status']}</div>",
            unsafe_allow_html=True,
        )
        _badge_html = ""
        if _gs["moratorium"]:
            _badge_html += "<span class='risk-tag risk-critical' style='margin-right:8px;'>⛔ Moratorium Active</span>"
        if _gs["ratepayer_bill"]:
            _badge_html += "<span class='risk-tag risk-moderate' style='margin-right:8px;'>⚖️ Ratepayer Bill Active</span>"
        if _gs["dc_hub"]:
            _badge_html += "<span class='ticker-chip' style='margin-right:8px;'>🏢 DC Hub State</span>"
        if not _badge_html:
            _badge_html = "<span class='risk-tag risk-low'>✓ No Active Restrictions</span>"
        st.markdown(f"<div style='margin-top:6px;'>{_badge_html}</div>", unsafe_allow_html=True)

    with st.expander("📢 Live Industry News", expanded=False):
        _gn_df = fetch_grid_news()
        if _gn_df.empty:
            st.markdown(
                "<div style='color:#7A9BBE;font-size:0.85rem;padding:12px;'>No grid news available at this time.</div>",
                unsafe_allow_html=True,
            )
        else:
            _state_news = _gn_df[
                (_gn_df["state"] == _pg_sel) | (_gn_df["state"] == "")
            ].head(8)
            if _state_news.empty:
                _state_news = _gn_df.head(5)
            for _, _nr in _state_news.iterrows():
                _read_link = (
                    f" <a href='{_nr['url']}' target='_blank' style='color:#C9A84C;"
                    f"font-size:0.72rem;text-decoration:none;'>↗ Read</a>"
                    if _nr.get("url") else ""
                )
                _st_tag = (
                    f" <span style='background:#1A2D40;color:#7A9BBE;padding:2px 7px;"
                    f"border-radius:10px;font-size:0.68rem;'>{_nr['state']}</span>"
                    if _nr.get("state") else ""
                )
                st.markdown(
                    f"<div style='padding:10px 0;border-bottom:1px solid #0F2035;'>"
                    f"<div style='color:#E8EDF5;font-size:0.85rem;font-weight:600;line-height:1.45;'>"
                    f"{_nr['headline']}{_read_link}{_st_tag}</div>"
                    f"<div style='color:#C8D8EE;font-size:0.78rem;margin-top:4px;line-height:1.5;'>"
                    f"{str(_nr.get('summary',''))[:200]}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:3px;'>"
                    f"{_nr.get('source_name','')} · {_nr.get('published','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    with st.expander("💼 Impact on Listed REITs", expanded=False):
        _key_reits = _gs.get("key_reits", [])
        if not _key_reits:
            st.markdown(
                "<div style='color:#7A9BBE;font-size:0.85rem;padding:12px;'>"
                "No listed REIT exposure tracked for this state.</div>",
                unsafe_allow_html=True,
            )
        else:
            _reit_info_data = fetch_reit_info(tuple(_key_reits))
            for _ticker in _key_reits:
                _t_name = TICKER_NAMES.get(_ticker, _ticker)
                _t_info = _reit_info_data.get(_ticker, {})
                _t_price = _t_info.get("last_price")
                _t_yh    = _t_info.get("year_high")
                _t_yl    = _t_info.get("year_low")
                _narrative = GRID_REIT_NARRATIVES.get(
                    (_pg_sel, _ticker),
                    f"{_t_name} has operations in {_gs['name']}. Monitor grid risk level "
                    f"({_gs['risk_level']}) and any legislative changes that may affect "
                    f"power costs or development timelines.",
                )
                _price_html = ""
                if _t_price and _t_yh and _t_yl and _t_yh != _t_yl:
                    _pct_from_high = (_t_price - _t_yh) / _t_yh * 100
                    _bar_pct = max(0, min(100, (_t_price - _t_yl) / (_t_yh - _t_yl) * 100))
                    _price_html = (
                        f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                        f"padding:8px 12px;margin-top:10px;'>"
                        f"<div style='display:flex;justify-content:space-between;'>"
                        f"<span style='color:#C9A84C;font-weight:800;font-size:0.88rem;'>{_ticker}</span>"
                        f"<span style='color:#C8D8EE;font-size:0.85rem;'>${_t_price:.2f}</span>"
                        f"</div>"
                        f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:2px;'>"
                        f"{_pct_from_high:.1f}% vs 52W High · "
                        f"52W Range: ${_t_yl:.0f}–${_t_yh:.0f}</div>"
                        f"<div style='background:#1B3150;border-radius:2px;height:3px;margin-top:6px;'>"
                        f"<div style='background:#C9A84C;height:3px;border-radius:2px;width:{_bar_pct:.0f}%;'></div>"
                        f"</div></div>"
                    )
                st.markdown(
                    f"<div class='intel-card' style='padding:14px 18px;margin-bottom:10px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<div><span class='ticker-chip'>{_ticker}</span>"
                    f"<span style='color:#7A9BBE;font-size:0.80rem;margin-left:8px;'>{_t_name}</span></div>"
                    f"<span class='risk-tag {_gs_risk_css}'>{_gs['risk_level']}</span>"
                    f"</div>"
                    f"<div style='color:#C8D8EE;font-size:0.87rem;line-height:1.70;margin-top:10px;'>"
                    f"{_narrative}</div>"
                    f"{_price_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Section D: 50-State Risk Overview Table ───────────────────────────────
    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>All 50 States — Power & Grid Risk Overview</div>", unsafe_allow_html=True)

    _overview_rows = []
    for _abbr, _sd in POWER_GRID_STATES.items():
        _overview_rows.append({
            "State": f"{_sd['name']} ({_abbr})",
            "Grid Operator": _sd["grid_operator"],
            "Risk Level": _sd["risk_level"],
            "Moratorium": "Yes" if _sd["moratorium"] else "—",
            "DC Hub": "Yes" if _sd["dc_hub"] else "—",
            "Ratepayer Bill": "Yes" if _sd["ratepayer_bill"] else "—",
        })

    _ov_df = pd.DataFrame(_overview_rows)
    _ov_df["_sort"] = _ov_df["Risk Level"].map({"High": 0, "Moderate": 1, "Low": 2}).fillna(3)
    _ov_df = _ov_df.sort_values(["_sort", "State"]).drop(columns=["_sort"]).reset_index(drop=True)

    st.dataframe(
        _ov_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "State":          st.column_config.TextColumn("State", width="medium"),
            "Grid Operator":  st.column_config.TextColumn("Grid Operator", width="medium"),
            "Risk Level":     st.column_config.TextColumn("Risk Level", width="small"),
            "Moratorium":     st.column_config.TextColumn("Moratorium", width="small"),
            "DC Hub":         st.column_config.TextColumn("DC Hub", width="small"),
            "Ratepayer Bill": st.column_config.TextColumn("Ratepayer Bill", width="small"),
        },
    )


render_audit_panel(df_all)


# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT OVERLAY — floating widget injected into parent DOM
# Calls Anthropic API directly from the browser using the
# anthropic-dangerous-direct-browser-access header (CORS-enabled by Anthropic).
# API key is stored only in the user's browser localStorage — never sent to
# the Python/Streamlit server.
# ══════════════════════════════════════════════════════════════════════════════

components.html("""
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
(function() {
    var pd = window.parent.document;
    if (pd.getElementById('reit-ai-fab')) return; // already injected

    /* ── Styles ── */
    var style = pd.createElement('style');
    style.textContent = [
        "@keyframes reit-glow{0%,100%{box-shadow:0 0 8px 3px rgba(0,255,136,.75),0 4px 24px rgba(0,0,0,.5)}50%{box-shadow:0 0 26px 10px rgba(0,255,136,.35),0 4px 24px rgba(0,0,0,.5)}}",
        "#reit-ai-fab{position:fixed;bottom:28px;right:28px;z-index:100000;width:62px;height:62px;border-radius:50%;border:2.5px solid rgba(0,255,136,.65);background:linear-gradient(135deg,#00FF88 0%,#00BB55 100%);cursor:pointer;font-size:27px;display:flex;align-items:center;justify-content:center;animation:reit-glow 2.6s ease-in-out infinite;transition:transform .2s;font-family:sans-serif;line-height:1;outline:none;}",
        "#reit-ai-fab:hover{transform:scale(1.13);}",
        "#reit-chat-panel{position:fixed;bottom:104px;right:28px;z-index:99999;width:400px;max-height:570px;background:#F2F5F9;border-radius:20px;box-shadow:0 14px 55px rgba(0,0,0,.45),0 0 0 1px rgba(0,0,0,.08);display:none;flex-direction:column;overflow:hidden;font-family:'Inter','Segoe UI',sans-serif;}",
        "#reit-chat-panel.reit-open{display:flex;}",
        ".reit-hdr{background:#0F1E35;padding:14px 18px;display:flex;align-items:center;gap:11px;flex-shrink:0;}",
        ".reit-hdr-icon{font-size:1.5rem;line-height:1;}",
        ".reit-hdr-title{color:#fff;font-size:.95rem;font-weight:700;}",
        ".reit-hdr-sub{color:#7A9BBE;font-size:.73rem;margin-top:1px;}",
        ".reit-live{margin-left:auto;background:#001A0D;color:#00FF88;border:1px solid rgba(0,255,136,.35);border-radius:20px;padding:3px 9px;font-size:.68rem;font-weight:700;letter-spacing:.07em;}",
        ".reit-close{background:none;border:none;color:#7A9BBE;font-size:18px;cursor:pointer;padding:2px 4px;line-height:1;margin-left:8px;}",
        ".reit-close:hover{color:#fff;}",
        ".reit-msgs{flex:1;overflow-y:auto;padding:14px 14px 6px 14px;display:flex;flex-direction:column;gap:10px;background:#F2F5F9;}",
        ".reit-bubble{max-width:86%;border-radius:14px;padding:10px 14px;font-size:.87rem;line-height:1.57;word-break:break-word;}",
        ".reit-bubble.user{background:#0F1E35;color:#E8F0FA;margin-left:auto;border-bottom-right-radius:4px;}",
        ".reit-bubble.ai{background:#fff;color:#1A202C;border:1px solid #E2E8F0;margin-right:auto;border-bottom-left-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.06);}",
        ".reit-bubble.typing{background:#fff;color:#9AABB8;border:1px solid #E2E8F0;margin-right:auto;font-style:italic;font-size:.82rem;}",
        ".reit-welcome{text-align:center;color:#718096;font-size:.82rem;padding:20px 16px 8px;line-height:1.6;}",
        ".reit-form{padding:12px 14px 14px;background:#fff;border-top:1px solid #E8ECF0;flex-shrink:0;}",
        ".reit-api-wrap{position:relative;margin-bottom:9px;}",
        ".reit-api-in{width:100%;padding:8px 12px;border:1.5px solid #D1D9E2;border-radius:10px;font-size:.80rem;color:#1A202C;background:#F8FAFB;box-sizing:border-box;outline:none;}",
        ".reit-api-in:focus{border-color:#00BB55;}",
        ".reit-row{display:flex;gap:8px;}",
        ".reit-msg-in{flex:1;padding:9px 14px;border:1.5px solid #D1D9E2;border-radius:10px;font-size:.88rem;color:#1A202C;background:#fff;outline:none;}",
        ".reit-msg-in:focus{border-color:#00BB55;box-shadow:0 0 0 2px rgba(0,187,85,.12);}",
        ".reit-send{padding:9px 18px;background:#00BB55;color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:.88rem;font-weight:600;flex-shrink:0;transition:background .15s;}",
        ".reit-send:hover{background:#009944;}",
        ".reit-send:disabled{background:#A8D8B8;cursor:not-allowed;}",
        ".reit-clear{display:block;width:100%;margin-top:8px;padding:5px;background:none;border:none;color:#A0AEC0;font-size:.75rem;cursor:pointer;text-align:center;}",
        ".reit-clear:hover{color:#718096;}",
        ".reit-bubble.ai h1,.reit-bubble.ai h2,.reit-bubble.ai h3{color:#0F1E35;font-size:.93rem;font-weight:700;margin:.7em 0 .3em;border-bottom:1px solid #E2E8F0;padding-bottom:3px;}",
        ".reit-bubble.ai h3{border-bottom:none;font-size:.88rem;color:#2D3748;}",
        ".reit-bubble.ai p{margin:.35em 0;font-size:.87rem;color:#1A202C;line-height:1.58;}",
        ".reit-bubble.ai ul,.reit-bubble.ai ol{margin:.35em 0 .35em 1.1em;padding:0;font-size:.87rem;color:#1A202C;}",
        ".reit-bubble.ai li{margin:.18em 0;}",
        ".reit-bubble.ai strong{font-weight:700;color:#0F1E35;}",
        ".reit-bubble.ai code{background:#EEF2F7;color:#2D3748;padding:1px 5px;border-radius:4px;font-size:.82rem;font-family:monospace;}",
        ".reit-bubble.ai table{border-collapse:collapse;width:100%;margin:.5em 0;font-size:.82rem;}",
        ".reit-bubble.ai th{background:#E8ECF2;color:#0F1E35;padding:5px 10px;text-align:left;font-weight:700;border:1px solid #D1D9E2;}",
        ".reit-bubble.ai td{padding:5px 10px;border:1px solid #E2E8F0;color:#2D3748;vertical-align:top;}",
        ".reit-bubble.ai tr:nth-child(even) td{background:#F7F9FC;}"
    ].join('');
    pd.head.appendChild(style);

    /* ── State ── */
    var history = [];
    var savedKey = '';
    try { savedKey = localStorage.getItem('reit_ai_key') || ''; } catch(e){}

    /* ── FAB ── */
    var fab = pd.createElement('button');
    fab.id = 'reit-ai-fab';
    fab.title = 'AI Research Assistant';
    fab.textContent = '🤖'; // 🤖
    pd.body.appendChild(fab);

    /* ── Panel markup ── */
    var panel = pd.createElement('div');
    panel.id = 'reit-chat-panel';
    panel.innerHTML =
        '<div class="reit-hdr">' +
          '<span class="reit-hdr-icon">🤖</span>' +
          '<div><div class="reit-hdr-title">AI Research Assistant</div>' +
          '<div class="reit-hdr-sub">REIT Legislative Intelligence</div></div>' +
          '<span class="reit-live">LIVE</span>' +
          '<button class="reit-close" id="reit-close" title="Close">✕</button>' +
        '</div>' +
        '<div class="reit-msgs" id="reit-msgs">' +
          '<div class="reit-welcome">Ask me about rent control exposure, ballot initiatives,<br>NOI impact, or specific ticker risk profiles.</div>' +
        '</div>' +
        '<div class="reit-form">' +
          '<div class="reit-api-wrap">' +
            '<input class="reit-api-in" id="reit-api-key" type="password" placeholder="🔑 Anthropic API key (sk-ant-...)" />' +
          '</div>' +
          '<div class="reit-row">' +
            '<input class="reit-msg-in" id="reit-msg-in" type="text" placeholder="Ask about REIT exposure…" />' +
            '<button class="reit-send" id="reit-send">Send</button>' +
          '</div>' +
          '<button class="reit-clear" id="reit-clear-btn">Clear conversation</button>' +
        '</div>';
    pd.body.appendChild(panel);

    if (savedKey) pd.getElementById('reit-api-key').value = savedKey;

    /* ── Toggle open/close ── */
    fab.onclick = function() { panel.classList.toggle('reit-open'); };
    pd.getElementById('reit-close').onclick = function() { panel.classList.remove('reit-open'); };

    /* ── Add bubble ── */
    function bubble(role, text) {
        var msgs = pd.getElementById('reit-msgs');
        var d = pd.createElement('div');
        d.className = 'reit-bubble ' + role;
        if (role === 'ai' && window.marked) {
            d.innerHTML = window.marked.parse(text);
        } else {
            d.textContent = text;
        }
        msgs.appendChild(d);
        msgs.scrollTop = msgs.scrollHeight;
        return d;
    }

    /* ── Clear ── */
    pd.getElementById('reit-clear-btn').onclick = function() {
        history = [];
        var msgs = pd.getElementById('reit-msgs');
        msgs.innerHTML = '<div class="reit-welcome">Conversation cleared. Ask me anything about REIT legislative risk.</div>';
    };

    /* ── Send ── */
    function send() {
        var keyEl = pd.getElementById('reit-api-key');
        var msgEl = pd.getElementById('reit-msg-in');
        var sendBtn = pd.getElementById('reit-send');
        var key = keyEl.value.trim();
        var msg = msgEl.value.trim();
        if (!msg) return;
        if (!key) { keyEl.focus(); keyEl.style.borderColor = '#E53E3E'; setTimeout(function(){ keyEl.style.borderColor=''; }, 1500); return; }
        try { localStorage.setItem('reit_ai_key', key); } catch(e) {}

        msgEl.value = '';
        history.push({ role: 'user', content: msg });
        bubble('user', msg);
        var typing = bubble('typing', 'Analyzing…');
        sendBtn.disabled = true;

        var sys = 'You are an expert REIT analyst specializing in US legislative and regulatory risk. ' +
            'You cover 9 tracked tickers: AVB (AvalonBay), EQR (Equity Residential), ESS (Essex Property), ' +
            'MAA (Mid-America Apartment), CPT (Camden Property), UDR, INVH (Invitation Homes), ' +
            'AMH (American Homes 4 Rent), CSR (Centerspace - upper Midwest multifamily). ' +
            'CenterSquare Investment Management holds: UDR $282M, CPT $258M, INVH $185M, AMH $166M, MAA $75M, EQR $68M, ESS $52M. ' +
            'Be concise, analytical, and use specific figures where available.';

        fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'anthropic-dangerous-direct-browser-access': 'true'
            },
            body: JSON.stringify({
                model: 'claude-haiku-4-5-20251001',
                max_tokens: 700,
                system: sys,
                messages: history.slice(-8)
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            typing.remove();
            sendBtn.disabled = false;
            if (data.error) {
                bubble('ai', 'Error: ' + (data.error.message || JSON.stringify(data.error)));
            } else {
                var text = data.content && data.content[0] ? data.content[0].text : '(no response)';
                history.push({ role: 'assistant', content: text });
                // Wait for marked.js if still loading from CDN
                if (window.marked) {
                    bubble('ai', text);
                } else {
                    var wait = setInterval(function() {
                        if (window.marked) { clearInterval(wait); bubble('ai', text); }
                    }, 50);
                    setTimeout(function() { clearInterval(wait); bubble('ai', text); }, 3000);
                }
            }
        })
        .catch(function(err) {
            typing.remove();
            sendBtn.disabled = false;
            bubble('ai', 'Network error: ' + err.message + '. Make sure your API key is valid.');
        });
    }

    pd.getElementById('reit-send').onclick = send;
    pd.getElementById('reit-msg-in').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });

})();
</script>
""", height=0)
