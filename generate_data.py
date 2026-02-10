"""
Generate comprehensive synthetic analytics dataset for Voice-to-Data demo.

Produces 8 weeks of daily data across 9 tables covering:
- Product engagement (DAU, sessions, duration)
- Revenue & churn (MRR, ARR, churn rate, NRR)
- Feature usage & adoption
- Funnel conversion
- User acquisition (signups, CAC, channels)
- Support tickets
- NPS scores
- Geographic breakdown
- A/B test results

Built-in narratives:
- Overall engagement drops ~3% in the most recent week
- Mobile session duration drops ~8% (app update on Tuesday)
- Free tier onboarding completion drops ~12%
- Feature X adoption drops ~5%
- Enterprise churn spikes in current week
- Mobile acquisition cost rises
- NPS dips for free tier
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

random.seed(42)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engagement.db")

PLATFORMS = ["web", "mobile", "tablet"]
SEGMENTS = ["free", "pro", "enterprise"]
FEATURES = ["Feature X", "Feature Y", "Feature Z", "Search", "Dashboard", "Export", "Notifications", "Analytics", "Integrations", "API"]
FUNNEL_STEPS = ["signup", "onboarding", "activation", "retention"]
CHANNELS = ["organic", "paid_search", "paid_social", "referral", "email", "direct"]
REGIONS = ["north_america", "europe", "asia_pacific", "latin_america"]
TICKET_CATEGORIES = ["bug", "feature_request", "billing", "onboarding_help", "performance", "account"]

END_DATE = datetime(2026, 2, 8)
START_DATE = END_DATE - timedelta(weeks=8) + timedelta(days=1)


def is_drop_week(date):
    return date >= (END_DATE - timedelta(days=6))


def jitter(value, pct=0.03):
    return value * (1 + random.uniform(-pct, pct))


# ── Table 1: daily_metrics ──────────────────────────────────────────────────

def generate_daily_metrics(cursor):
    cursor.execute("""
        CREATE TABLE daily_metrics (
            date TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            dau INTEGER NOT NULL,
            wau INTEGER NOT NULL,
            mau INTEGER NOT NULL,
            session_duration_avg REAL NOT NULL,
            sessions_per_user REAL NOT NULL,
            bounce_rate REAL NOT NULL,
            pages_per_session REAL NOT NULL,
            PRIMARY KEY (date, platform, segment)
        )
    """)

    BASE_DAU = {
        ("web", "free"): 18000, ("web", "pro"): 8000, ("web", "enterprise"): 3500,
        ("mobile", "free"): 12000, ("mobile", "pro"): 5000, ("mobile", "enterprise"): 1500,
        ("tablet", "free"): 1200, ("tablet", "pro"): 500, ("tablet", "enterprise"): 300,
    }
    BASE_DUR = {"web": 5.8, "mobile": 6.2, "tablet": 4.5}
    BASE_SPU = {"web": 2.3, "mobile": 3.1, "tablet": 1.8}
    BASE_BOUNCE = {"web": 0.35, "mobile": 0.28, "tablet": 0.40}
    BASE_PPS = {"web": 4.2, "mobile": 3.8, "tablet": 3.1}

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for platform in PLATFORMS:
            for segment in SEGMENTS:
                base_dau = BASE_DAU[(platform, segment)]
                if current.weekday() >= 5:
                    base_dau = int(base_dau * 0.7)

                dau = int(jitter(base_dau))
                duration = round(jitter(BASE_DUR[platform]), 2)
                spu = round(jitter(BASE_SPU[platform]), 2)
                bounce = round(jitter(BASE_BOUNCE[platform]), 4)
                pps = round(jitter(BASE_PPS[platform]), 2)

                if is_drop_week(current):
                    if platform == "mobile":
                        duration = round(duration * 0.92, 2)
                        bounce = round(bounce * 1.08, 4)
                    if segment == "free" and platform == "mobile":
                        dau = int(dau * 0.95)
                    dau = int(dau * 0.98)
                    pps = round(pps * 0.97, 2)

                wau = int(dau * 5.5)
                mau = int(dau * 22)
                rows.append((current.strftime("%Y-%m-%d"), platform, segment,
                             dau, wau, mau, duration, spu, bounce, pps))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO daily_metrics VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 2: feature_usage ──────────────────────────────────────────────────

def generate_feature_usage(cursor):
    cursor.execute("""
        CREATE TABLE feature_usage (
            date TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            adoption_rate REAL NOT NULL,
            sessions_with_feature INTEGER NOT NULL,
            drop_off_rate REAL NOT NULL,
            avg_time_in_feature REAL NOT NULL,
            PRIMARY KEY (date, feature_name, platform, segment)
        )
    """)

    BASE_ADOPTION = {
        "Feature X": 0.34, "Feature Y": 0.52, "Feature Z": 0.18,
        "Search": 0.71, "Dashboard": 0.65, "Export": 0.22,
        "Notifications": 0.58, "Analytics": 0.45, "Integrations": 0.15, "API": 0.12,
    }
    BASE_DROPOFF = {
        "Feature X": 0.15, "Feature Y": 0.10, "Feature Z": 0.25,
        "Search": 0.05, "Dashboard": 0.08, "Export": 0.20,
        "Notifications": 0.07, "Analytics": 0.12, "Integrations": 0.30, "API": 0.18,
    }
    BASE_TIME = {
        "Feature X": 3.2, "Feature Y": 2.1, "Feature Z": 1.5,
        "Search": 0.8, "Dashboard": 5.5, "Export": 1.2,
        "Notifications": 0.5, "Analytics": 4.8, "Integrations": 6.2, "API": 2.0,
    }
    BASE_DAU = {
        ("web", "free"): 18000, ("web", "pro"): 8000, ("web", "enterprise"): 3500,
        ("mobile", "free"): 12000, ("mobile", "pro"): 5000, ("mobile", "enterprise"): 1500,
        ("tablet", "free"): 1200, ("tablet", "pro"): 500, ("tablet", "enterprise"): 300,
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for feature in FEATURES:
            for platform in PLATFORMS:
                for segment in SEGMENTS:
                    adoption = BASE_ADOPTION[feature]
                    if segment == "pro": adoption *= 1.15
                    elif segment == "enterprise": adoption *= 1.25

                    adoption = round(jitter(min(adoption, 0.95)), 4)
                    dropoff = round(jitter(BASE_DROPOFF[feature]), 4)
                    sessions = int(jitter(BASE_DAU[(platform, segment)] * adoption * 0.5))
                    avg_time = round(jitter(BASE_TIME[feature]), 2)

                    if is_drop_week(current) and feature == "Feature X":
                        adoption = round(adoption * 0.95, 4)
                        sessions = int(sessions * 0.95)
                        dropoff = round(dropoff * 1.10, 4)

                    if is_drop_week(current) and feature == "Notifications" and platform == "mobile":
                        adoption = round(adoption * 0.90, 4)

                    rows.append((current.strftime("%Y-%m-%d"), feature, platform, segment,
                                 adoption, sessions, dropoff, avg_time))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO feature_usage VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 3: funnel_metrics ─────────────────────────────────────────────────

def generate_funnel_metrics(cursor):
    cursor.execute("""
        CREATE TABLE funnel_metrics (
            date TEXT NOT NULL,
            funnel_step TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            conversion_rate REAL NOT NULL,
            users_count INTEGER NOT NULL,
            PRIMARY KEY (date, funnel_step, platform, segment)
        )
    """)

    BASE_CONV = {"signup": 0.85, "onboarding": 0.68, "activation": 0.55, "retention": 0.42}
    BASE_DAU = {
        ("web", "free"): 18000, ("web", "pro"): 8000, ("web", "enterprise"): 3500,
        ("mobile", "free"): 12000, ("mobile", "pro"): 5000, ("mobile", "enterprise"): 1500,
        ("tablet", "free"): 1200, ("tablet", "pro"): 500, ("tablet", "enterprise"): 300,
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for step in FUNNEL_STEPS:
            for platform in PLATFORMS:
                for segment in SEGMENTS:
                    conv = BASE_CONV[step]
                    if segment == "enterprise": conv *= 1.10
                    elif segment == "pro": conv *= 1.05

                    conv = round(jitter(min(conv, 0.98)), 4)
                    users = int(jitter(BASE_DAU[(platform, segment)] * conv * 0.3))

                    if is_drop_week(current) and step == "onboarding" and segment == "free":
                        conv = round(conv * 0.88, 4)
                        users = int(users * 0.88)
                    if is_drop_week(current) and step == "activation":
                        conv = round(conv * 0.97, 4)

                    rows.append((current.strftime("%Y-%m-%d"), step, platform, segment, conv, users))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO funnel_metrics VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 4: revenue ────────────────────────────────────────────────────────

def generate_revenue(cursor):
    cursor.execute("""
        CREATE TABLE revenue (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            mrr REAL NOT NULL,
            arr REAL NOT NULL,
            new_mrr REAL NOT NULL,
            churned_mrr REAL NOT NULL,
            expansion_mrr REAL NOT NULL,
            paying_customers INTEGER NOT NULL,
            arpu REAL NOT NULL,
            PRIMARY KEY (date, segment)
        )
    """)

    BASE = {
        "free": {"mrr": 0, "customers": 31200, "arpu": 0},
        "pro": {"mrr": 285000, "customers": 13500, "arpu": 21.11},
        "enterprise": {"mrr": 520000, "customers": 5300, "arpu": 98.11},
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for segment in SEGMENTS:
            b = BASE[segment]
            mrr = round(jitter(b["mrr"]), 2)
            customers = int(jitter(b["customers"]))
            arpu = round(jitter(b["arpu"]), 2) if b["arpu"] > 0 else 0
            new_mrr = round(jitter(mrr * 0.05), 2) if mrr > 0 else 0
            churned_mrr = round(jitter(mrr * 0.02), 2) if mrr > 0 else 0
            expansion = round(jitter(mrr * 0.03), 2) if mrr > 0 else 0

            if is_drop_week(current) and segment == "enterprise":
                churned_mrr = round(churned_mrr * 1.45, 2)  # enterprise churn spike
                customers = int(customers * 0.97)

            if is_drop_week(current) and segment == "pro":
                new_mrr = round(new_mrr * 0.90, 2)

            arr = round(mrr * 12, 2)
            rows.append((current.strftime("%Y-%m-%d"), segment,
                         mrr, arr, new_mrr, churned_mrr, expansion, customers, arpu))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO revenue VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 5: churn ──────────────────────────────────────────────────────────

def generate_churn(cursor):
    cursor.execute("""
        CREATE TABLE churn (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            churn_rate REAL NOT NULL,
            churned_users INTEGER NOT NULL,
            net_revenue_retention REAL NOT NULL,
            gross_revenue_retention REAL NOT NULL,
            PRIMARY KEY (date, segment, platform)
        )
    """)

    BASE_CHURN = {"free": 0.08, "pro": 0.03, "enterprise": 0.015}
    BASE_NRR = {"free": 0.0, "pro": 1.08, "enterprise": 1.15}
    BASE_GRR = {"free": 0.92, "pro": 0.97, "enterprise": 0.985}
    BASE_USERS = {
        ("free", "web"): 18000, ("free", "mobile"): 12000, ("free", "tablet"): 1200,
        ("pro", "web"): 8000, ("pro", "mobile"): 5000, ("pro", "tablet"): 500,
        ("enterprise", "web"): 3500, ("enterprise", "mobile"): 1500, ("enterprise", "tablet"): 300,
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for segment in SEGMENTS:
            for platform in PLATFORMS:
                churn = round(jitter(BASE_CHURN[segment]), 4)
                users = int(jitter(BASE_USERS[(segment, platform)] * churn))
                nrr = round(jitter(BASE_NRR[segment]), 4) if BASE_NRR[segment] > 0 else 0
                grr = round(jitter(BASE_GRR[segment]), 4)

                if is_drop_week(current):
                    if segment == "enterprise":
                        churn = round(churn * 1.40, 4)
                        users = int(users * 1.40)
                        nrr = round(nrr * 0.95, 4)
                        grr = round(grr * 0.96, 4)
                    if segment == "free" and platform == "mobile":
                        churn = round(churn * 1.15, 4)

                rows.append((current.strftime("%Y-%m-%d"), segment, platform,
                             churn, users, nrr, grr))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO churn VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 6: acquisition ────────────────────────────────────────────────────

def generate_acquisition(cursor):
    cursor.execute("""
        CREATE TABLE acquisition (
            date TEXT NOT NULL,
            channel TEXT NOT NULL,
            platform TEXT NOT NULL,
            new_signups INTEGER NOT NULL,
            cac REAL NOT NULL,
            ltv REAL NOT NULL,
            ltv_cac_ratio REAL NOT NULL,
            spend REAL NOT NULL,
            PRIMARY KEY (date, channel, platform)
        )
    """)

    BASE_SIGNUPS = {
        ("organic", "web"): 450, ("organic", "mobile"): 320, ("organic", "tablet"): 40,
        ("paid_search", "web"): 280, ("paid_search", "mobile"): 150, ("paid_search", "tablet"): 20,
        ("paid_social", "web"): 180, ("paid_social", "mobile"): 250, ("paid_social", "tablet"): 30,
        ("referral", "web"): 120, ("referral", "mobile"): 90, ("referral", "tablet"): 15,
        ("email", "web"): 95, ("email", "mobile"): 60, ("email", "tablet"): 10,
        ("direct", "web"): 200, ("direct", "mobile"): 110, ("direct", "tablet"): 25,
    }
    BASE_CAC = {
        "organic": 5.0, "paid_search": 28.0, "paid_social": 22.0,
        "referral": 12.0, "email": 8.0, "direct": 3.0,
    }
    BASE_LTV = {
        "organic": 85.0, "paid_search": 72.0, "paid_social": 65.0,
        "referral": 95.0, "email": 78.0, "direct": 90.0,
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for channel in CHANNELS:
            for platform in PLATFORMS:
                signups = int(jitter(BASE_SIGNUPS.get((channel, platform), 50)))
                cac = round(jitter(BASE_CAC[channel]), 2)
                ltv = round(jitter(BASE_LTV[channel]), 2)

                if current.weekday() >= 5:
                    signups = int(signups * 0.6)

                if is_drop_week(current):
                    if platform == "mobile":
                        cac = round(cac * 1.20, 2)  # mobile CAC increases
                        signups = int(signups * 0.90)
                    if channel == "paid_social":
                        cac = round(cac * 1.15, 2)

                spend = round(signups * cac, 2)
                ltv_cac = round(ltv / cac, 2) if cac > 0 else 0

                rows.append((current.strftime("%Y-%m-%d"), channel, platform,
                             signups, cac, ltv, ltv_cac, spend))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO acquisition VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 7: support_tickets ────────────────────────────────────────────────

def generate_support(cursor):
    cursor.execute("""
        CREATE TABLE support_tickets (
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            tickets_opened INTEGER NOT NULL,
            tickets_resolved INTEGER NOT NULL,
            avg_resolution_hours REAL NOT NULL,
            csat_score REAL NOT NULL,
            PRIMARY KEY (date, category, segment, platform)
        )
    """)

    BASE_TICKETS = {
        "bug": 15, "feature_request": 8, "billing": 5,
        "onboarding_help": 12, "performance": 6, "account": 4,
    }
    BASE_RESOLUTION = {
        "bug": 18.0, "feature_request": 48.0, "billing": 4.0,
        "onboarding_help": 8.0, "performance": 24.0, "account": 2.0,
    }
    BASE_CSAT = {
        "bug": 3.2, "feature_request": 3.8, "billing": 4.1,
        "onboarding_help": 3.9, "performance": 3.0, "account": 4.3,
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for cat in TICKET_CATEGORIES:
            for segment in SEGMENTS:
                for platform in PLATFORMS:
                    opened = int(jitter(BASE_TICKETS[cat], 0.15))
                    if segment == "enterprise": opened = int(opened * 0.5)
                    elif segment == "free": opened = int(opened * 1.5)

                    resolved = int(opened * jitter(0.85, 0.05))
                    res_hours = round(jitter(BASE_RESOLUTION[cat]), 1)
                    csat = round(min(jitter(BASE_CSAT[cat], 0.05), 5.0), 2)

                    if is_drop_week(current):
                        if cat == "bug" and platform == "mobile":
                            opened = int(opened * 1.60)  # bug tickets spike on mobile
                            csat = round(csat * 0.85, 2)
                        if cat == "onboarding_help" and segment == "free":
                            opened = int(opened * 1.35)
                        if cat == "performance":
                            opened = int(opened * 1.20)
                            res_hours = round(res_hours * 1.30, 1)

                    rows.append((current.strftime("%Y-%m-%d"), cat, segment, platform,
                                 opened, resolved, res_hours, csat))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO support_tickets VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 8: nps_scores ─────────────────────────────────────────────────────

def generate_nps(cursor):
    cursor.execute("""
        CREATE TABLE nps_scores (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            nps_score INTEGER NOT NULL,
            promoters_pct REAL NOT NULL,
            passives_pct REAL NOT NULL,
            detractors_pct REAL NOT NULL,
            responses INTEGER NOT NULL,
            PRIMARY KEY (date, segment, platform)
        )
    """)

    BASE_NPS = {"free": 28, "pro": 45, "enterprise": 62}

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for segment in SEGMENTS:
            for platform in PLATFORMS:
                nps = int(jitter(BASE_NPS[segment], 0.08))
                responses = int(jitter({"free": 200, "pro": 80, "enterprise": 30}[segment], 0.10))

                if is_drop_week(current):
                    if segment == "free":
                        nps = int(nps * 0.80)  # NPS drops for free tier
                    if platform == "mobile":
                        nps = int(nps * 0.90)

                nps = max(-100, min(100, nps))
                promoters = round(min(0.95, (50 + nps / 2) / 100), 4)
                detractors = round(max(0.02, (50 - nps / 2) / 100 * 0.6), 4)
                passives = round(max(0.0, 1.0 - promoters - detractors), 4)

                rows.append((current.strftime("%Y-%m-%d"), segment, platform,
                             nps, promoters, passives, detractors, responses))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO nps_scores VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Table 9: geo_metrics ────────────────────────────────────────────────────

def generate_geo(cursor):
    cursor.execute("""
        CREATE TABLE geo_metrics (
            date TEXT NOT NULL,
            region TEXT NOT NULL,
            segment TEXT NOT NULL,
            dau INTEGER NOT NULL,
            revenue REAL NOT NULL,
            churn_rate REAL NOT NULL,
            avg_session_duration REAL NOT NULL,
            PRIMARY KEY (date, region, segment)
        )
    """)

    BASE = {
        ("north_america", "free"): {"dau": 15000, "rev": 0, "churn": 0.07, "dur": 6.0},
        ("north_america", "pro"): {"dau": 6500, "rev": 140000, "churn": 0.025, "dur": 5.8},
        ("north_america", "enterprise"): {"dau": 2800, "rev": 280000, "churn": 0.012, "dur": 5.5},
        ("europe", "free"): {"dau": 10000, "rev": 0, "churn": 0.06, "dur": 5.5},
        ("europe", "pro"): {"dau": 4200, "rev": 90000, "churn": 0.028, "dur": 5.3},
        ("europe", "enterprise"): {"dau": 1500, "rev": 150000, "churn": 0.014, "dur": 5.0},
        ("asia_pacific", "free"): {"dau": 5000, "rev": 0, "churn": 0.09, "dur": 4.8},
        ("asia_pacific", "pro"): {"dau": 2000, "rev": 42000, "churn": 0.035, "dur": 4.5},
        ("asia_pacific", "enterprise"): {"dau": 600, "rev": 60000, "churn": 0.018, "dur": 4.2},
        ("latin_america", "free"): {"dau": 2200, "rev": 0, "churn": 0.10, "dur": 4.5},
        ("latin_america", "pro"): {"dau": 800, "rev": 18000, "churn": 0.04, "dur": 4.2},
        ("latin_america", "enterprise"): {"dau": 200, "rev": 25000, "churn": 0.02, "dur": 4.0},
    }

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for region in REGIONS:
            for segment in SEGMENTS:
                b = BASE[(region, segment)]
                dau = int(jitter(b["dau"]))
                rev = round(jitter(b["rev"]), 2) if b["rev"] > 0 else 0
                churn = round(jitter(b["churn"]), 4)
                dur = round(jitter(b["dur"]), 2)

                if current.weekday() >= 5:
                    dau = int(dau * 0.7)

                if is_drop_week(current):
                    dau = int(dau * 0.97)
                    if region == "asia_pacific":
                        churn = round(churn * 1.25, 4)  # APAC churn spike
                        dau = int(dau * 0.95)
                    if segment == "enterprise":
                        churn = round(churn * 1.30, 4)

                rows.append((current.strftime("%Y-%m-%d"), region, segment,
                             dau, rev, churn, dur))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO geo_metrics VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    generators = [
        ("daily_metrics", generate_daily_metrics),
        ("feature_usage", generate_feature_usage),
        ("funnel_metrics", generate_funnel_metrics),
        ("revenue", generate_revenue),
        ("churn", generate_churn),
        ("acquisition", generate_acquisition),
        ("support_tickets", generate_support),
        ("nps_scores", generate_nps),
        ("geo_metrics", generate_geo),
    ]

    total = 0
    for name, gen_fn in generators:
        n = gen_fn(cursor)
        print(f"  {name}: {n:,} rows")
        total += n

    conn.commit()
    print(f"\n  TOTAL: {total:,} rows")
    print(f"  Database: {DB_PATH}")

    # Validation
    print("\n--- Validation ---")
    for label, sql in [
        ("DAU drop", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, SUM(dau)
            FROM daily_metrics WHERE date >= '2026-01-26' GROUP BY w
        """),
        ("Mobile duration", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(session_duration_avg),2)
            FROM daily_metrics WHERE date >= '2026-01-26' AND platform='mobile' GROUP BY w
        """),
        ("Free onboarding", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(conversion_rate),4)
            FROM funnel_metrics WHERE date >= '2026-01-26' AND funnel_step='onboarding' AND segment='free' GROUP BY w
        """),
        ("Enterprise churn", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(churn_rate),4)
            FROM churn WHERE date >= '2026-01-26' AND segment='enterprise' GROUP BY w
        """),
        ("Enterprise churned MRR", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(churned_mrr),2)
            FROM revenue WHERE date >= '2026-01-26' AND segment='enterprise' GROUP BY w
        """),
        ("Mobile CAC (paid_search)", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(cac),2)
            FROM acquisition WHERE date >= '2026-01-26' AND platform='mobile' AND channel='paid_search' GROUP BY w
        """),
        ("Free NPS", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, ROUND(AVG(nps_score),1)
            FROM nps_scores WHERE date >= '2026-01-26' AND segment='free' GROUP BY w
        """),
        ("Mobile bug tickets", """
            SELECT CASE WHEN date >= '2026-02-02' THEN 'curr' ELSE 'prev' END w, SUM(tickets_opened)
            FROM support_tickets WHERE date >= '2026-01-26' AND category='bug' AND platform='mobile' GROUP BY w
        """),
    ]:
        results = cursor.execute(sql).fetchall()
        vals = {r[0]: r[1] for r in results}
        prev, curr = vals.get("prev", 0), vals.get("curr", 0)
        if prev and prev != 0:
            delta = (curr - prev) / prev * 100
            print(f"  {label}: {prev} → {curr} ({delta:+.1f}%)")
        else:
            print(f"  {label}: {prev} → {curr}")

    conn.close()


if __name__ == "__main__":
    main()
