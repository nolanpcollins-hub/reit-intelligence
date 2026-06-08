"""
db_seeder.py
Instantiates market_intelligence.db and populates it with institutional-grade
placeholder data reflecting the 2026 US multifamily legislative landscape.
Covers 24 markets across 20+ states.
Run: python db_seeder.py   (re-run any time for a clean rebuild)
"""

import os
import sqlite3

DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_intelligence.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def read_schema() -> str:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return f.read()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def setup_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP INDEX IF EXISTS idx_mi_state_category")
    conn.execute("DROP INDEX IF EXISTS idx_mi_tickers")
    conn.execute("DROP INDEX IF EXISTS idx_mi_risk")
    conn.execute("DROP TABLE IF EXISTS market_intelligence")
    conn.executescript(read_schema())
    conn.commit()


SEED_DATA = [

    # ══════════════════════════════════════════════════════════════════════════
    # CALIFORNIA — Critical legislative risk: algorithmic bans + rent caps
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Los Angeles",
        "state_code":            "CA",
        "tickers_exposed":       "ESS,AVB,EQR",
        "category":              "Algorithmic Pricing Ban",
        "state_of_law":          "Active Enforced",
        "headline":              "California AB 1418 Takes Effect: Algorithmic Lease-Pricing Software Banned Statewide",
        "summary_insight":       (
            "California's AB 1418 prohibits any landlord or property management firm from deploying "
            "third-party algorithmic rent-optimization software that ingests nonpublic competitor "
            "occupancy data. ESS, AVB, and EQR each disclosed heavy reliance on RealPage LRO and "
            "Yardi Lease Analytics in their 2025 10-K risk factors. Transition to compliant pricing "
            "models is estimated to compress same-store NOI growth by 80–120 bps in California "
            "submarkets through FY2026. Essex Property Trust management has indicated it expects to "
            "incur $3.2M in one-time transition costs related to repricing systems."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.85,
        "source_name":           "California Legislative Information",
        "source_url":            "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB1418",
        "exact_text_quote":      (
            "No landlord or landlord's agent shall use, subscribe to, or contract with any algorithmic "
            "device that uses nonpublic occupancy, pricing, or availability data from any other residential "
            "rental property to set, recommend, or approve any rental rate for a residential dwelling unit. "
            "Violations are subject to a civil penalty of $10,000 per unit per violation per calendar year."
        ),
        "last_updated":          "2026-01-15 08:00:00",
    },
    {
        "metro_market":          "San Francisco Bay Area",
        "state_code":            "CA",
        "tickers_exposed":       "ESS,AVB",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "AB 1482 Rent Cap Ceiling Remains at 5% + CPI for 2026; Essex and AvalonBay Disclose Exposure",
        "summary_insight":       (
            "California's AB 1482 Tenant Protection Act caps annual rent increases at the lower of 5% plus "
            "local CPI or 10% for covered multifamily units. With Bay Area CPI running at 3.2% for 2025, "
            "the effective cap is 8.2% — well below the 12–15% rent growth Essex achieved pre-regulation. "
            "ESS disclosed in its Q3 2025 10-Q that approximately 68% of its California portfolio falls "
            "under AB 1482 coverage. AvalonBay estimates 44% of its 6,200 CA units are covered. "
            "Both REITs have flagged this as a multi-year headwind to West Coast NOI growth."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.78,
        "source_name":           "California Legislative Information / Essex Property Trust SEC 10-Q",
        "source_url":            "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=201920200AB1482",
        "exact_text_quote":      (
            "An owner of residential real property shall not, over the course of any 12-month period, "
            "increase the gross rental rate for a dwelling or a unit more than 5 percent plus the percentage "
            "change in the cost of living, or 10 percent, whichever is lower, of the lowest gross rental "
            "rate charged for that dwelling or unit at any time during the 12 months prior to the effective "
            "date of the increase."
        ),
        "last_updated":          "2026-02-01 09:30:00",
    },
    {
        "metro_market":          "Statewide California",
        "state_code":            "CA",
        "tickers_exposed":       "ESS,AVB,EQR",
        "category":              "Algorithmic Pricing Ban",
        "state_of_law":          "Pending Vote",
        "headline":              "California SB 33 Expands Algorithmic Ban to Include In-House Revenue Management Systems",
        "summary_insight":       (
            "A proposed expansion of the algorithmic pricing prohibition, SB 33, targets not only "
            "third-party SaaS platforms but also proprietary in-house revenue management tools built on "
            "market-comparable data feeds. Essex Property Trust operates a proprietary pricing engine for "
            "its 245-property California portfolio that could fall within the bill's scope. Senate Judiciary "
            "Committee vote expected Q3 2026. Legal counsel across all three REITs has flagged material "
            "compliance risk. ESS CEO Angela Kleiman stated on Q4 2025 earnings call that the company is "
            "'carefully monitoring SB 33 with outside counsel.' Estimated compliance cost: $7–12M industry-wide."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.72,
        "source_name":           "California Senate Judiciary Committee",
        "source_url":            "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB33",
        "exact_text_quote":      (
            "The prohibition set forth in Section 1947.15 of the Civil Code shall apply equally to any pricing "
            "recommendation system developed or operated internally by a landlord, property management company, "
            "or their affiliates, where such system incorporates market-rate data, occupancy rates, or lease "
            "expiration schedules derived from nonpublic data obtained from third-party residential rental "
            "properties within the same metropolitan statistical area."
        ),
        "last_updated":          "2026-03-10 11:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MASSACHUSETTS — Local option rent stabilization debates
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Boston",
        "state_code":            "MA",
        "tickers_exposed":       "AVB,EQR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Pending Vote",
        "headline":              "Massachusetts H.1304 Local Option Rent Stabilization Bill Advances to Senate Ways & Means",
        "summary_insight":       (
            "H.1304 would allow municipalities with populations exceeding 50,000 to enact local rent "
            "stabilization ordinances capping annual increases at CPI + 3%. Boston, Cambridge, Somerville, "
            "and Brookline are all expected to adopt stabilization regimes immediately upon passage. "
            "AvalonBay's Boston portfolio comprises 4,800 units across 18 communities; EQR holds 2,100 units. "
            "Combined potential NOI impact estimated at $18–22M annually under a 5% effective cap scenario "
            "versus current 9–11% renewal rent growth. The Senate Ways & Means Committee is expected to "
            "mark up the bill in June 2026 with a floor vote possible in the fall session."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.55,
        "source_name":           "Massachusetts General Court",
        "source_url":            "https://malegislature.gov/Bills/194/H1304",
        "exact_text_quote":      (
            "Any city or town with a population greater than 50,000 persons may, by ordinance or by-law "
            "duly adopted by its legislative body and approved by its chief executive officer, establish a "
            "rent stabilization program governing the rents charged for residential tenancies within its "
            "jurisdiction, provided that no such program shall limit annual rent increases to less than the "
            "local Consumer Price Index plus three percentage points."
        ),
        "last_updated":          "2026-02-20 14:00:00",
    },
    {
        "metro_market":          "Cambridge",
        "state_code":            "MA",
        "tickers_exposed":       "AVB,EQR",
        "category":              "Ballot Initiative",
        "state_of_law":          "Developing Ballot",
        "headline":              "Cambridge Tenants Union Files 8,400 Signatures for 6% Annual Rent Cap Ballot Question",
        "summary_insight":       (
            "The Cambridge Rent Equity Coalition filed 8,400 certified signatures — exceeding the 5,000 "
            "threshold — for a November 2026 ballot measure capping annual rent increases at 6% or CPI, "
            "whichever is lower. Cambridge accounts for approximately 1,200 of AvalonBay's Boston-area units. "
            "Legal challenges to the initiative's compliance with the state's Home Rule Amendment are already "
            "being prepared by the Greater Boston Real Estate Board, creating litigation-driven uncertainty. "
            "Industry opponents are also challenging the ballot title at the Cambridge Election Commission, "
            "a process that could delay the measure by 60–90 days."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.48,
        "source_name":           "Cambridge Election Commission / Cambridge Rent Equity Coalition",
        "source_url":            "https://www.cambridgema.gov/Departments/electioncommission",
        "exact_text_quote":      (
            "We the undersigned registered voters of Cambridge hereby petition for the following measure: "
            "'Shall the City of Cambridge enact an ordinance limiting annual rent increases for residential "
            "tenancies to six percent (6%) or the change in the Consumer Price Index for the "
            "Boston-Cambridge-Newton metropolitan area, whichever is lower, with exceptions for substantial "
            "rehabilitation and newly constructed units occupied for the first fifteen years following "
            "issuance of certificate of occupancy?'"
        ),
        "last_updated":          "2026-04-05 16:30:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TEXAS — Sun Belt preemption; landlord-favorable
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Dallas-Fort Worth",
        "state_code":            "TX",
        "tickers_exposed":       "MAA,CPT",
        "category":              "Ballot Initiative",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Texas SB 1100 Statewide Rent Control Preemption Signed into Law; DFW Operators Insulated",
        "summary_insight":       (
            "Governor Abbott signed SB 1100 in June 2024, codifying a permanent statewide preemption of all "
            "municipal rent control ordinances. Dallas, Austin, and Houston city councils had previously "
            "explored rent stabilization pilot programs. The preemption law removes legislative risk from "
            "MAA's 14,200-unit Texas portfolio and CPT's 6,800 DFW units through at least 2028. Sun Belt "
            "supply additions of 48,000 units in DFW through 2026 remain the primary NOI headwind — not "
            "regulation. Both MAA and CPT have guided toward DFW as a key 2026–2027 recovery market as "
            "new supply absorption improves concession burn-off."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.72,
        "source_name":           "Texas Legislature Online",
        "source_url":            "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=88R&Bill=SB1100",
        "exact_text_quote":      (
            "A municipality or county may not adopt or enforce an ordinance, order, rule, or regulation that "
            "controls the price at which residential rental property may be offered for lease or rent. Any "
            "ordinance, order, rule, or regulation that violates this section is void and unenforceable. "
            "This section applies to any action taken by a political subdivision on or after the effective "
            "date of this Act, and to any action taken before the effective date that has not been fully performed."
        ),
        "last_updated":          "2025-08-12 10:00:00",
    },
    {
        "metro_market":          "Houston",
        "state_code":            "TX",
        "tickers_exposed":       "MAA,CPT,UDR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Houston City Council Rent Stabilization Pilot Withdrawn Following State Preemption Challenge",
        "summary_insight":       (
            "A Houston City Council proposal to implement a 90-day emergency rent freeze was withdrawn by the "
            "Mayor's office in Q1 2025 after the Texas AG issued a formal opinion citing SB 1100 preemption. "
            "MAA operates 4,100 units in the Greater Houston MSA. The stable regulatory backdrop supports "
            "robust NOI growth as Houston continues to absorb post-Hurricane Beryl rebuilding demand through "
            "2026. CPT's Camden portfolio in Houston (3,200 units) also benefits from the preemption clarity. "
            "UDR has 1,800 Houston units and cited preemption security in its 2025 investor day materials."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.65,
        "source_name":           "City of Houston Office of the Mayor / Texas Attorney General Opinion GA-1011",
        "source_url":            "https://www.texasattorneygeneral.gov/sites/default/files/opinion-files/opinion/2025/ga-1011.pdf",
        "exact_text_quote":      (
            "It is my opinion that the proposed Houston City Code amendment establishing a temporary rent "
            "stabilization mechanism for residential tenancies in declared emergency zones is preempted by "
            "Section 214.902 of the Texas Local Government Code, as amended by the 88th Legislature, and is "
            "therefore void and without legal effect. Municipal home-rule authority does not extend to the "
            "regulation of residential rental prices."
        ),
        "last_updated":          "2025-10-30 09:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # FLORIDA — Sun Belt preemption upheld; highly favorable
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Tampa Bay",
        "state_code":            "FL",
        "tickers_exposed":       "MAA,CPT,UDR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Florida Rent Stabilization Preemption Upheld by 11th Circuit; MAA and CPT Sun Belt Thesis Intact",
        "summary_insight":       (
            "Florida's long-standing rent control preemption statute (Fla. Stat. §125.0103 and §166.043) was "
            "upheld in full by the 11th Circuit Court of Appeals in February 2025, rejecting Orange County's "
            "voter-approved emergency rent stabilization ordinance. The ruling provides durable protection for "
            "MAA's 18,400-unit Florida portfolio and CPT's 5,600 Tampa/Orlando units. Favorable regulatory "
            "environment combines with 6–8% YoY rent growth and declining new supply pipeline to support the "
            "Sun Belt REIT investment thesis. CPT guided for Tampa Bay and Orlando to be its top two NOI "
            "growth markets in 2026, citing the preemption ruling as a key strategic anchor."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.80,
        "source_name":           "U.S. Court of Appeals, 11th Circuit",
        "source_url":            "https://media.ca11.uscourts.gov/opinions/pub/files/202311893.pdf",
        "exact_text_quote":      (
            "Florida Statutes Section 125.0103 expressly and specifically prohibits counties from enacting "
            "rent control ordinances except upon a finding of a housing emergency so grave as to constitute "
            "a serious menace to the general public. The Orange County ordinance, enacted by referendum, does "
            "not satisfy the statutory prerequisites and is preempted by state law. The district court's "
            "judgment granting summary judgment to the landlord-appellees is AFFIRMED."
        ),
        "last_updated":          "2025-11-05 11:30:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEW YORK — Active rent stabilization; chronic risk for AVB/EQR
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "New York City",
        "state_code":            "NY",
        "tickers_exposed":       "AVB,EQR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "NYC Rent Guidelines Board Sets 2026 Stabilized Renewal Cap at 3.5%; AvalonBay and EQR Disclose Impact",
        "summary_insight":       (
            "The NYC Rent Guidelines Board voted 5-4 to set a 3.5% one-year renewal increase cap for "
            "rent-stabilized apartments for lease years commencing October 2026 through September 2027. "
            "AvalonBay's NYC portfolio includes approximately 2,400 rent-stabilized units following legacy "
            "acquisitions. EQR holds 1,800 stabilized units across its Manhattan and Brooklyn properties. "
            "The 3.5% cap compares unfavorably against AvalonBay's blended market-rate renewal growth of "
            "7.2% for Q1 2026. Combined NOI impact estimated at $8.4M annually for both REITs under the "
            "3.5% cap versus the prior 5.0% guideline."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.62,
        "source_name":           "NYC Rent Guidelines Board",
        "source_url":            "https://rentguidelinesboard.cityofnewyork.us/resources/press-releases/",
        "exact_text_quote":      (
            "The New York City Rent Guidelines Board, pursuant to Section 26-510 of the New York City "
            "Administrative Code, hereby orders that the maximum rate of increase for renewal leases for "
            "housing accommodations subject to the Rent Stabilization Law of 1969 shall be: (1) For a "
            "one-year lease commencing on or after October 1, 2026 and on or before September 30, 2027: "
            "three and one-half percent (3.5%)."
        ),
        "last_updated":          "2026-05-28 18:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # WASHINGTON — Algorithmic pricing ban moving through legislature
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Seattle",
        "state_code":            "WA",
        "tickers_exposed":       "ESS,AVB",
        "category":              "Algorithmic Pricing Ban",
        "state_of_law":          "Pending Vote",
        "headline":              "Washington HB 2114 Algorithmic Pricing Prohibition Passes House 62-36; Senate Vote Imminent",
        "summary_insight":       (
            "Washington's HB 2114, modeled closely on California AB 1418, passed the state House 62-36 in "
            "March 2026. The bill prohibits use of algorithmic rent-setting tools using competitor data and "
            "mandates disclosure of any revenue management software used to price units. Essex Property Trust "
            "disclosed in its Q4 2025 earnings call that ~22% of its Seattle-area portfolio (~3,100 units) "
            "currently utilizes pricing software potentially covered by the bill's scope. AvalonBay Seattle "
            "(2,400 units) is similarly exposed. Senate Labor & Commerce Committee hearing scheduled for "
            "June 15, 2026, with floor vote expected within 30 days of favorable committee report."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.52,
        "source_name":           "Washington State Legislature",
        "source_url":            "https://app.leg.wa.gov/billsummary?BillNumber=2114&Year=2025&Initiative=false",
        "exact_text_quote":      (
            "A landlord or property manager of a residential rental property shall not use any software, "
            "algorithm, or automated tool to set, recommend, or approve rental rates if such software, "
            "algorithm, or tool relies in any part upon nonpublic data concerning rents charged, occupancy "
            "rates, lease terms, or availability of other residential rental properties within the same "
            "county or metropolitan statistical area."
        ),
        "last_updated":          "2026-03-22 13:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ARIZONA — Ballot initiative targeting preemption repeal
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Phoenix",
        "state_code":            "AZ",
        "tickers_exposed":       "MAA,CPT,AMH",
        "category":              "Ballot Initiative",
        "state_of_law":          "Developing Ballot",
        "headline":              "Arizona Renters United Files for 2026 Ballot Measure to Repeal State Rent Control Preemption",
        "summary_insight":       (
            "Arizona Renters United has collected 142,000 of 237,645 signatures required for a November 2026 "
            "initiative to repeal Arizona Revised Statutes §33-1329, which currently preempts all local rent "
            "control. The group needs 237,645 valid signatures by July 3, 2026. MAA has 8,200 units in the "
            "Phoenix MSA; CPT has 4,100; AMH has 3,400 single-family rentals. Polling shows 54% voter support "
            "for allowing local stabilization. Industry lobby AMA is funding legal challenges to the "
            "initiative's title and summary, which could invalidate signatures already collected."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.38,
        "source_name":           "Arizona Secretary of State / Arizona Renters United",
        "source_url":            "https://azsos.gov/elections/initiative-referendum-and-recall",
        "exact_text_quote":      (
            "The People of Arizona hereby propose the following initiative measure to be submitted directly "
            "to the voters: Section 1. Arizona Revised Statutes Section 33-1329 is hereby repealed in its "
            "entirety. Section 2. This act shall be known as the 'Arizona Local Rent Stabilization Authority "
            "Act' and shall take effect upon approval by a majority of qualified voters casting ballots at "
            "the next general election at which this measure is submitted."
        ),
        "last_updated":          "2026-04-18 10:30:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COLORADO — Local option bill threatening CSR/UDR/CPT exposure
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Denver",
        "state_code":            "CO",
        "tickers_exposed":       "UDR,CPT,CSR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Pending Vote",
        "headline":              "Colorado HB 24-1322 Local Rent Stabilization Authority Reintroduced; Denver Operators on Alert",
        "summary_insight":       (
            "Colorado HB 24-1322, which would allow municipalities to enact rent stabilization ordinances "
            "capped at CPI + 3%, was reintroduced in the 2026 legislative session following a narrow defeat "
            "in 2025. Denver currently has a 9-member task force preparing a draft stabilization ordinance "
            "contingent on state authorization. UDR has 3,800 Denver units; CPT 2,900; and CSR (Centerspace) "
            "is divesting one Denver community as part of its 2026 portfolio rationalization. Industry groups "
            "have endorsed a compromise 'anti-gouging' bill capping increases at 7% as an alternative. "
            "Senate floor vote now expected in the June 2026 special session after Democratic leadership "
            "added three additional co-sponsors in May."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.42,
        "source_name":           "Colorado General Assembly",
        "source_url":            "https://leg.colorado.gov/bills/hb24-1322",
        "exact_text_quote":      (
            "A statutory city, city and county, or home rule municipality may adopt an ordinance or resolution "
            "establishing a residential rent stabilization program for any residential dwelling unit that has "
            "been occupied for residential purposes for two or more years; provided, that no such program "
            "shall limit annual rent increases to an amount less than three percent above the Denver-Aurora-"
            "Lakewood metropolitan statistical area Consumer Price Index for All Urban Consumers, as published "
            "by the United States Bureau of Labor Statistics."
        ),
        "last_updated":          "2026-02-14 08:30:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GEORGIA — Candidate profiling; Atlanta mayoral race
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Atlanta",
        "state_code":            "GA",
        "tickers_exposed":       "MAA,CPT,INVH",
        "category":              "Candidate Profiling",
        "state_of_law":          "Developing Ballot",
        "headline":              "Atlanta Mayor's Race: Front-Runner Endorses Rent Stabilization Study Commission",
        "summary_insight":       (
            "Atlanta mayoral candidate Councilwoman Keisha Dorsey, leading polls at 38%, has endorsed "
            "creation of a city-funded Rent Stabilization Study Commission with a mandate to report findings "
            "by Q2 2027. Georgia state law currently preempts rent control (O.C.G.A. §44-7-19), but the "
            "study commission is viewed as a precursor to a state legislative preemption repeal effort. "
            "MAA has 9,200 units in the Atlanta MSA; INVH 4,800 SFR homes; CPT 3,100 units. General election "
            "is November 3, 2026. Regulatory risk remains low/stable absent a change in state law, but the "
            "political trajectory warrants close monitoring through Q4 2026."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       -0.22,
        "source_name":           "Atlanta Journal-Constitution / Candidate Policy Platform",
        "source_url":            "https://www.ajc.com/news/atlanta-news/atlanta-mayor-race-2026-rent-stabilization/",
        "exact_text_quote":      (
            "If elected, I will in my first 100 days establish by executive order an Atlanta Rent "
            "Stabilization Study Commission, comprising tenants, housing advocates, property owners, and "
            "economists, with a mandate to study the feasibility, design, and economic impact of rent "
            "stabilization in Atlanta and to report its findings and recommendations to the Mayor and "
            "City Council no later than June 30, 2027. — Councilwoman Keisha Dorsey, Campaign Housing "
            "Platform, March 2026."
        ),
        "last_updated":          "2026-03-30 17:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MINNESOTA — CSR Centerspace core market; state rent cap framework
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Minneapolis-Saint Paul",
        "state_code":            "MN",
        "tickers_exposed":       "CSR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Pending Vote",
        "headline":              "Minnesota SF 2222 Statewide Rent Stabilization Framework Advances; Centerspace (CSR) Flags Material Risk",
        "summary_insight":       (
            "Minnesota SF 2222 would establish a statewide rent stabilization framework capping annual "
            "increases at the lower of 3% or CPI for all residential tenancies in cities with populations "
            "above 20,000. Centerspace (CSR), which operates 4,200 apartments across Minneapolis, Saint Paul, "
            "and suburban Twin Cities, disclosed in its Q1 2026 earnings call that passage of SF 2222 would "
            "represent a 'material adverse change' to projected 2026–2027 same-store revenue growth of "
            "4.5–5.0%. The bill is co-sponsored by 22 DFL senators and awaits a Senate floor vote expected "
            "in the June 2026 special session. Governor Walz has not committed to signing the bill."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.58,
        "source_name":           "Minnesota Legislature / Centerspace Q1 2026 Earnings Call Transcript",
        "source_url":            "https://www.revisor.mn.gov/bills/bill.php?f=SF2222&y=2026&ssn=0&b=senate",
        "exact_text_quote":      (
            "No landlord of a residential premises located within a city having a population of 20,000 or "
            "more persons shall increase the rent charged to a tenant in any 12-month period by an amount "
            "that exceeds the lesser of three percent (3%) or the percentage change in the Consumer Price "
            "Index for All Urban Consumers, Minneapolis-St. Paul-Bloomington, MN-WI, as most recently "
            "published by the United States Bureau of Labor Statistics."
        ),
        "last_updated":          "2026-05-10 14:30:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ILLINOIS — Chicago algorithmic pricing and ETOD zoning pressure
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Chicago",
        "state_code":            "IL",
        "tickers_exposed":       "EQR,AVB,UDR",
        "category":              "Algorithmic Pricing Ban",
        "state_of_law":          "Pending Vote",
        "headline":              "Chicago City Council Introduces Revenue Management Software Transparency Ordinance; Vote Q3 2026",
        "summary_insight":       (
            "The Chicago City Council's Housing Committee advanced an ordinance requiring landlords with 50+ "
            "units to publicly disclose their revenue management software vendors and annual pricing "
            "methodologies. The ordinance stops short of an outright ban but is widely viewed as a precursor "
            "to full prohibition. EQR operates 8,400 units in the Chicago MSA, representing approximately "
            "9% of its total portfolio. AVB has 2,200 Chicagoland units. Mayor Brandon Johnson has publicly "
            "endorsed the ordinance and hinted at supporting a full ban if disclosures reveal anti-competitive "
            "behavior. Vote expected by September 2026."
        ),
        "portfolio_risk_impact": "Moderate",
        "sentiment_score":       -0.35,
        "source_name":           "Chicago City Council Housing Committee / Chicago Tribune",
        "source_url":            "https://chicityclerk.s3.amazonaws.com/s3fs-public/document_uploads/ordinances/2026/",
        "exact_text_quote":      (
            "Every owner of a covered residential building shall, on or before March 1 of each calendar year, "
            "file with the Department of Housing a written disclosure identifying: (1) the name and version of "
            "any software used to establish, adjust, or recommend rental rates for units within the building; "
            "(2) the name of the software vendor or developer; (3) a description of the data inputs used by "
            "such software, including whether data from other residential properties is incorporated. Failure "
            "to file constitutes a violation subject to a fine of $500 per day per unit."
        ),
        "last_updated":          "2026-04-25 10:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEW JERSEY — Active rent stabilization; multi-city enforcement
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Jersey City / Newark",
        "state_code":            "NJ",
        "tickers_exposed":       "AVB,EQR,UDR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "New Jersey's Expanded Rent Control Network Now Covers 103 Municipalities; AVB Newark Portfolio Impacted",
        "summary_insight":       (
            "New Jersey's rent stabilization framework now covers 103 municipalities following 2025 "
            "legislative amendments that lowered the population threshold for eligibility. Jersey City "
            "(3.5% cap) and Newark (2.5% cap) are the most impactful for institutional REITs. AvalonBay "
            "operates 3,600 stabilized or stabilization-eligible units across its NJ portfolio, representing "
            "17% of its Northeast book. EQR has 2,100 NJ units. The New Jersey Association of Realtors "
            "estimates that stabilization reduces market-rate conversion opportunity by 40% in covered "
            "municipalities, creating a long-term structural NOI drag."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.60,
        "source_name":           "New Jersey Legislature / NJ DCA Division of Housing",
        "source_url":            "https://www.njleg.state.nj.us/Bills/2026/A0500/324_I1.HTM",
        "exact_text_quote":      (
            "The rent control ordinance of the City of Jersey City, as amended, limits annual rent increases "
            "for covered dwelling units to the lesser of: (a) 3.5%; or (b) the percentage increase in the "
            "Consumer Price Index for the New York-Newark-Jersey City metropolitan area as published by the "
            "Bureau of Labor Statistics for the preceding calendar year. No owner shall collect rent in "
            "excess of the maximum rent as established herein, regardless of vacancy status."
        ),
        "last_updated":          "2026-01-30 09:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # OREGON — Statewide rent cap; active enforced
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Portland",
        "state_code":            "OR",
        "tickers_exposed":       "ESS,AVB",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "Oregon SB 608 Statewide Rent Cap Adjusted for 2026: Effective Cap is 8.2% for Covered Units",
        "summary_insight":       (
            "Oregon's statewide rent stabilization law (SB 608), the first of its kind in the US when enacted "
            "in 2019, continues as the operational framework for Portland multifamily. For 2026, the effective "
            "cap is 7% + CPI, calculated at 8.2% based on Oregon CPI of 1.2%. ESS (Essex Property Trust) "
            "holds 3,400 Portland-area units and has disclosed that approximately 61% are covered under SB "
            "608's criteria (buildings 15+ years old). AvalonBay has 1,800 Portland units at 58% coverage. "
            "Portland's market-rate renewal growth has averaged 10.4% in H1 2026, making the cap a meaningful "
            "constraint. Essex cited the cap as a $4.1M annual NOI headwind for the Portland submarket."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.58,
        "source_name":           "Oregon Legislative Assembly / Oregon Revised Statutes §90.323",
        "source_url":            "https://www.oregonlegislature.gov/bills_laws/ors/ors090.html",
        "exact_text_quote":      (
            "A landlord may not increase the rent charged to a tenant for a dwelling unit during any "
            "12-month period by more than 7% plus the consumer price index, where the consumer price index "
            "is the applicable index for the calendar year in which the rent increase takes effect. A "
            "landlord may carry forward any unused rent increase for the immediately preceding calendar year. "
            "This section does not apply to a dwelling unit for which the certificate of occupancy was issued "
            "less than 15 years before the date of the notice of the rent increase."
        ),
        "last_updated":          "2026-01-05 08:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MARYLAND — Montgomery County active stabilization
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Washington DC Metro / Montgomery County",
        "state_code":            "MD",
        "tickers_exposed":       "AVB,EQR,UDR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "Montgomery County Rent Stabilization Ordinance Sets 3.0% Cap for 2026; DC Suburb REITs Cite Headwind",
        "summary_insight":       (
            "Montgomery County's Rent Stabilization Law (MC Bill 15-22) set a 3.0% maximum annual increase "
            "for 2026 for residential units in buildings with 5+ units. The county encompasses approximately "
            "330,000 rental units — one of the largest regulated markets in the Mid-Atlantic. AvalonBay "
            "holds 4,200 units across 14 Montgomery County communities. EQR has 2,800 units; UDR has 1,600. "
            "The 3.0% cap compares against blended market renewal rate of 6.8% for Q1 2026, representing "
            "a $12.4M combined NOI gap for the three REITs against an unconstrained scenario."
        ),
        "portfolio_risk_impact": "Critical",
        "sentiment_score":       -0.55,
        "source_name":           "Montgomery County Office of Landlord-Tenant Affairs",
        "source_url":            "https://www.montgomerycountymd.gov/OLTD/RentStabilization.html",
        "exact_text_quote":      (
            "Pursuant to Chapter 29A of the Montgomery County Code, no landlord shall increase the rent "
            "charged for a rental unit by more than the allowable annual rent increase, which for the period "
            "January 1, 2026 through December 31, 2026, shall not exceed three percent (3.0%) of the rent "
            "charged to the tenant on December 31 of the previous year. This limitation applies to all "
            "covered residential rental units within Montgomery County regardless of the length of tenancy."
        ),
        "last_updated":          "2025-12-20 10:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HAWAII — Maui County emergency rent cap; limited REIT exposure
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Maui County",
        "state_code":            "HI",
        "tickers_exposed":       "UDR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Active Enforced",
        "headline":              "Maui County Emergency Rent Freeze Extended Through December 2026 Following Wildfire Displacement Crisis",
        "summary_insight":       (
            "Maui County's emergency rent freeze, originally enacted post-Lahaina wildfire, was extended "
            "through December 31, 2026 by County Council vote. The freeze prohibits any rent increases "
            "on residential units in designated wildfire-impacted zones. UDR has a small presence in the "
            "Honolulu MSA (620 units) with no direct Maui exposure, but has flagged Hawaii generally as "
            "a legislative risk watch state. The Hawaii Legislature is simultaneously considering a statewide "
            "rent stabilization framework (HB 1460) that would apply to all islands, which would represent "
            "a material escalation of legislative risk for any REIT with Oahu exposure."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       -0.30,
        "source_name":           "Maui County Council / Hawaii State Legislature",
        "source_url":            "https://www.mauicounty.gov/DocumentCenter/View/135829",
        "exact_text_quote":      (
            "The Maui County Council hereby extends the moratorium on rent increases for residential "
            "dwelling units located within the designated wildfire emergency relief zones through and "
            "including December 31, 2026. No landlord within the designated zones shall increase the "
            "monthly rental charge above the amount charged as of July 31, 2023, until the moratorium "
            "expires or is lifted by subsequent Council action."
        ),
        "last_updated":          "2026-03-15 14:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEVADA — Supply-driven favorable; no rent control
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Las Vegas",
        "state_code":            "NV",
        "tickers_exposed":       "MAA,CPT,AMH",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Nevada SB 205 Rent Control Preemption Reaffirmed; Las Vegas Operators Benefit from Supply Absorption",
        "summary_insight":       (
            "Nevada's NRS §118B.220 preempts all local rent control ordinances. The 2025 Nevada Legislature "
            "considered but did not advance a bill to authorize local stabilization. Las Vegas remains one "
            "of the most favorable large-market regulatory environments for multifamily REIT operations. "
            "MAA's 4,800 Las Vegas units are positioned to benefit as the record 2024–2025 new supply wave "
            "of 22,000 units is absorbed — the market is expected to return to sub-5% vacancy by Q3 2026. "
            "CPT (2,600 units) and AMH (3,100 SFR homes) also benefit from the preemption certainty."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.62,
        "source_name":           "Nevada Legislature / Nevada Revised Statutes §118B.220",
        "source_url":            "https://www.leg.state.nv.us/NRS/NRS-118B.html#NRS118BSec220",
        "exact_text_quote":      (
            "A local government shall not enact, maintain or enforce any ordinance or regulation that "
            "controls the amount of rent charged for private residential property. As used in this section, "
            "'local government' means a county, incorporated city or town, unincorporated town or any other "
            "political subdivision of this State. Any ordinance or regulation in conflict with this section "
            "is void and unenforceable."
        ),
        "last_updated":          "2025-09-10 11:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEBRASKA — CSR Centerspace preemption territory; landlord-favorable
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Omaha",
        "state_code":            "NE",
        "tickers_exposed":       "CSR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Nebraska Rent Control Preemption (LB 1050) Remains in Force; CSR Centerspace Omaha Portfolio Insulated",
        "summary_insight":       (
            "Nebraska LB 1050, enacted in 2023, explicitly prohibits cities and counties from imposing rent "
            "control or rent stabilization requirements on private residential properties. Centerspace (CSR) "
            "operates 980 units across two communities in the Omaha MSA. The preemption law provides durable "
            "regulatory certainty for CSR's Nebraska operations. Nebraska's market fundamentals are "
            "favorable — Omaha multifamily vacancy was 4.8% as of Q1 2026 and effective rent growth is "
            "running at +5.2% YoY, well above the Midwest average. CSR noted Nebraska in its 2025 Annual "
            "Report as among its most stable regulatory environments."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.58,
        "source_name":           "Nebraska Legislature / Nebraska Revised Statutes §76-1481",
        "source_url":            "https://nebraskalegislature.gov/laws/statutes.php?statute=76-1481",
        "exact_text_quote":      (
            "A political subdivision shall not enact any ordinance, regulation, or resolution that "
            "establishes, continues, or enforces rent control or rent stabilization applicable to "
            "residential rental property. Any ordinance, regulation, or resolution that violates this "
            "section is void and unenforceable. Nothing in this section shall be construed to prohibit "
            "a political subdivision from regulating the habitability of residential rental property."
        ),
        "last_updated":          "2025-07-20 10:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NORTH DAKOTA — CSR core market; strong preemption
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Fargo",
        "state_code":            "ND",
        "tickers_exposed":       "CSR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "North Dakota Affirms No Local Rent Control Authority; CSR Centerspace Fargo Operations Unimpeded",
        "summary_insight":       (
            "North Dakota does not have an explicit statewide preemption statute, but the state's strong "
            "private property rights tradition and the lack of any enabling legislation means local rent "
            "control is functionally preempted. Centerspace exited the Bismarck market in 2026 as part of "
            "its portfolio rationalization but retains a 1,200-unit presence in the Fargo-West Fargo MSA. "
            "The ND Legislature's Property Rights Committee has consistently blocked rent stabilization "
            "measures over the past decade. CSR CEO Anne Olson cited Fargo as a 'strong rent growth market "
            "with minimal legislative overhang' at the Q1 2026 investor day."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.55,
        "source_name":           "Centerspace (CSR) Q1 2026 Investor Day / North Dakota Legislative Council",
        "source_url":            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000798359&type=10-K",
        "exact_text_quote":      (
            "In North Dakota, there are no state or local rent stabilization or rent control laws applicable "
            "to our apartment communities. We believe the regulatory and legislative environment in our North "
            "Dakota markets presents a lower risk of rent restriction legislation compared to coastal markets. "
            "However, we cannot assure you that such legislation will not be enacted in the future. "
            "— Centerspace 2025 Annual Report, Risk Factors, p. 28."
        ),
        "last_updated":          "2026-02-28 09:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MONTANA — CSR Billings market; favorable regulation
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Billings",
        "state_code":            "MT",
        "tickers_exposed":       "CSR",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Montana SB 245 Codifies Statewide Rent Control Prohibition; CSR Billings Portfolio Protected",
        "summary_insight":       (
            "Montana Governor Greg Gianforte signed SB 245 in April 2025, codifying a statewide prohibition "
            "on municipal rent control ordinances. Centerspace (CSR) operates 820 units in the Billings MSA "
            "across three communities. The legislation eliminates the regulatory risk that had emerged from "
            "Billings City Council discussions in late 2024. Montana multifamily fundamentals are supported "
            "by energy sector employment and population inflows from western states. CSR's Montana portfolio "
            "generated 5.9% same-store NOI growth in 2025, the highest of any state in its portfolio, "
            "benefiting from tight supply and zero regulatory constraint."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.62,
        "source_name":           "Montana Legislature / Montana Code Annotated §70-24-417",
        "source_url":            "https://leg.mt.gov/bills/2025/billpdf/SB0245.pdf",
        "exact_text_quote":      (
            "A county, city, town, or other local government unit may not enact or enforce any ordinance, "
            "resolution, or regulation that controls rents, rental rates, or the amount of increases in "
            "rent for private residential property. Any such ordinance, resolution, or regulation is "
            "preempted by state law and is void. This section does not impair the right of any local "
            "government to regulate landlord-tenant relationships in other respects consistent with "
            "Title 70, chapter 24."
        ),
        "last_updated":          "2025-05-30 10:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # UTAH — CSR Salt Lake market; preemption confirmed
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Salt Lake City",
        "state_code":            "UT",
        "tickers_exposed":       "CSR,MAA",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "Utah Reaffirms Rent Control Preemption; Salt Lake City Operators Face Supply Not Regulation",
        "summary_insight":       (
            "Utah Code §57-25-101 prohibits all state and local rent control ordinances, and the 2026 "
            "Legislature showed no appetite for modification. Centerspace (CSR) holds 1,400 units in the "
            "Salt Lake City and Provo-Orem markets; MAA has 3,200 Utah units. The primary market risk is "
            "supply-driven — Salt Lake City absorbed 9,800 new units in 2025 alone, temporarily widening "
            "vacancy to 8.4%. However, the regulatory preemption means operators retain full pricing "
            "flexibility as supply normalizes. Both CSR and MAA have guided for Utah to be among their "
            "strongest recovery markets in H2 2026 and 2027."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.48,
        "source_name":           "Utah Legislature / Utah Code §57-25-101",
        "source_url":            "https://le.utah.gov/xcode/Title57/Chapter25/57-25.html",
        "exact_text_quote":      (
            "A local government may not adopt or enforce an ordinance or regulation that restricts the "
            "amount a landlord charges for rent. This section does not prohibit a local government from "
            "providing voluntary incentives to landlords to limit rent increases or from requiring that "
            "a landlord include certain terms in a lease. For purposes of this section, 'local government' "
            "means a county, a municipality, or a special service district."
        ),
        "last_updated":          "2026-01-20 12:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # VIRGINIA — Richmond exploring local option; state preemption in force
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Richmond / Northern Virginia",
        "state_code":            "VA",
        "tickers_exposed":       "AVB,EQR,UDR",
        "category":              "Candidate Profiling",
        "state_of_law":          "Developing Ballot",
        "headline":              "Virginia HB 1827 Local Rent Stabilization Authority Failed 2025; Richmond City Council Pursues 2026 Study",
        "summary_insight":       (
            "Virginia HB 1827, which would have authorized localities to enact rent stabilization ordinances, "
            "failed in the House Counties, Cities & Towns Committee in January 2025 on an 11-9 party-line "
            "vote. The Richmond City Council passed a non-binding resolution in March 2026 calling for a "
            "comprehensive rent stabilization study, to be completed by January 2027. Northern Virginia "
            "remains the primary REIT concentration — AVB holds 8,200 units across Fairfax, Arlington, "
            "and Alexandria; EQR has 4,100; UDR has 2,800. The preemption regime is secure through 2026 "
            "but the political trajectory in Richmond and Northern Virginia warrants monitoring heading "
            "into the 2027 Virginia legislative session."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.15,
        "source_name":           "Virginia Legislative Information System / Richmond Times-Dispatch",
        "source_url":            "https://lis.virginia.gov/cgi-bin/legp604.exe?251+sum+HB1827",
        "exact_text_quote":      (
            "The bill to authorize any locality to adopt a residential rent stabilization ordinance failed "
            "in the House Counties, Cities & Towns Committee by an 11-9 vote. Committee members opposing the "
            "bill cited concerns about the impact on housing supply, noting that economic studies have "
            "consistently shown that rent control leads to reduced rental housing stock over time. The "
            "bill may be reintroduced in the 2026 session. — Virginia House of Delegates, Committee "
            "Report, January 22, 2025."
        ),
        "last_updated":          "2026-03-05 10:00:00",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NORTH CAROLINA — Sun Belt preemption; strong REIT-favorable backdrop
    # ══════════════════════════════════════════════════════════════════════════
    {
        "metro_market":          "Charlotte / Raleigh",
        "state_code":            "NC",
        "tickers_exposed":       "MAA,CPT,INVH",
        "category":              "Traditional Rent Cap",
        "state_of_law":          "Defeated/Preempted",
        "headline":              "North Carolina Statewide Rent Control Prohibition Confirmed; Charlotte and Raleigh Operators Unimpeded",
        "summary_insight":       (
            "North Carolina General Statutes §42-14.1 prohibits all local government rent control. "
            "Charlotte and Raleigh rank among the fastest-growing multifamily markets in the US, with "
            "combined new supply absorption of 28,000 units expected through 2026. MAA has 12,400 NC units "
            "(its second largest state concentration); CPT has 7,200; INVH has 4,100 SFR homes. The "
            "preemption is constitutionally entrenched and has survived multiple legal challenges. Both "
            "MAA and CPT have identified the Carolinas as their highest-conviction NOI growth region for "
            "2026–2027 as new supply absorption approaches equilibrium by Q3 2026."
        ),
        "portfolio_risk_impact": "Low/Stable",
        "sentiment_score":       0.68,
        "source_name":           "North Carolina General Statutes §42-14.1",
        "source_url":            "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_42/GS_42-14.1.html",
        "exact_text_quote":      (
            "No county or city shall enact, maintain, or enforce any ordinance or resolution which "
            "regulates the amount of rent to be charged for privately owned, single-family or multiple "
            "unit residential or commercial rental property. This section shall not apply to rental "
            "property owned or operated by any county or city."
        ),
        "last_updated":          "2025-06-15 09:00:00",
    },

]


def seed(conn: sqlite3.Connection) -> int:
    insert_sql = """
        INSERT INTO market_intelligence (
            metro_market, state_code, tickers_exposed, category, state_of_law,
            headline, summary_insight, portfolio_risk_impact, sentiment_score,
            source_name, source_url, exact_text_quote, last_updated
        ) VALUES (
            :metro_market, :state_code, :tickers_exposed, :category, :state_of_law,
            :headline, :summary_insight, :portfolio_risk_impact, :sentiment_score,
            :source_name, :source_url, :exact_text_quote, :last_updated
        )
    """
    conn.executemany(insert_sql, SEED_DATA)
    conn.commit()
    return len(SEED_DATA)


def main() -> None:
    print(f"Database : {DB_PATH}")
    print(f"Schema   : {SCHEMA_PATH}")
    conn = get_connection()
    try:
        print("Dropping and recreating table...")
        setup_table(conn)
        count = seed(conn)
        print(f"Seeded {count} rows successfully.")

        row = conn.execute("SELECT COUNT(*) FROM market_intelligence").fetchone()
        print(f"Row count confirmed: {row[0]}")

        states = conn.execute(
            "SELECT state_code, COUNT(*) as n FROM market_intelligence "
            "GROUP BY state_code ORDER BY n DESC"
        ).fetchall()
        print(f"\nRows by state ({len(states)} states covered):")
        for s in states:
            print(f"  {s[0]:4s}  {s[1]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
