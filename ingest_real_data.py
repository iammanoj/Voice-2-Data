#!/usr/bin/env python3
"""
Ingest large external datasets (REES46 multi-category events + GA revenue prediction)
into the existing engagement.db schema.

Stdlib only. CSV (optionally .gz) inputs.
"""

import argparse
import csv
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import io
import zipfile
from datetime import datetime


DB_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engagement.db")


def open_csv(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    if path.endswith(".zip"):
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            zf.close()
            raise FileNotFoundError(f"No files found inside {path}")
        raw = zf.open(names[0], "r")
        return io.TextIOWrapper(raw, encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")


def hash_bucket(value: str) -> int:
    h = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100


def synthesize_platform(value: str) -> str:
    bucket = hash_bucket(value)
    if bucket < 65:
        return "web"
    if bucket < 90:
        return "mobile"
    return "tablet"


def synthesize_segment(value: str) -> str:
    bucket = hash_bucket(value)
    if bucket < 75:
        return "free"
    if bucket < 95:
        return "pro"
    return "enterprise"


def synthesize_country(value: str) -> str:
    bucket = hash_bucket(value)
    if bucket < 40:
        return "US"
    if bucket < 55:
        return "GB"
    if bucket < 70:
        return "DE"
    if bucket < 85:
        return "IN"
    if bucket < 95:
        return "BR"
    return "AU"


def country_to_region(country: str) -> str:
    country = (country or "").upper()
    if country in {"US", "CA", "MX"}:
        return "north_america"
    if country in {"GB", "DE", "FR", "ES", "IT", "NL", "SE", "NO", "DK"}:
        return "europe"
    if country in {"IN", "JP", "CN", "SG", "AU", "NZ", "KR"}:
        return "asia_pacific"
    if country in {"BR", "AR", "CL", "CO", "PE"}:
        return "latin_america"
    return "other"


def ensure_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            dau INTEGER NOT NULL,
            wau INTEGER NOT NULL,
            mau INTEGER NOT NULL,
            session_duration_avg REAL NOT NULL,
            sessions_per_user REAL NOT NULL,
            bounce_rate REAL NOT NULL,
            pages_per_session REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feature_usage (
            date TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            adoption_rate REAL NOT NULL,
            sessions_with_feature INTEGER NOT NULL,
            drop_off_rate REAL NOT NULL,
            avg_time_in_feature REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS funnel_metrics (
            date TEXT NOT NULL,
            funnel_step TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            conversion_rate REAL NOT NULL,
            users_count INTEGER NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revenue (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            mrr REAL NOT NULL,
            arr REAL NOT NULL,
            new_mrr REAL NOT NULL,
            churned_mrr REAL NOT NULL,
            expansion_mrr REAL NOT NULL,
            paying_customers INTEGER NOT NULL,
            arpu REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS churn (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            churn_rate REAL NOT NULL,
            churned_users INTEGER NOT NULL,
            net_revenue_retention REAL NOT NULL,
            gross_revenue_retention REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS acquisition (
            date TEXT NOT NULL,
            channel TEXT NOT NULL,
            platform TEXT NOT NULL,
            new_signups INTEGER NOT NULL,
            cac REAL NOT NULL,
            ltv REAL NOT NULL,
            ltv_cac_ratio REAL NOT NULL,
            spend REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            tickets_opened INTEGER NOT NULL,
            tickets_resolved INTEGER NOT NULL,
            avg_resolution_hours REAL NOT NULL,
            csat_score REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nps_scores (
            date TEXT NOT NULL,
            segment TEXT NOT NULL,
            platform TEXT NOT NULL,
            nps_score INTEGER NOT NULL,
            promoters_pct REAL NOT NULL,
            passives_pct REAL NOT NULL,
            detractors_pct REAL NOT NULL,
            responses INTEGER NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS geo_metrics (
            date TEXT NOT NULL,
            region TEXT NOT NULL,
            segment TEXT NOT NULL,
            dau INTEGER NOT NULL,
            revenue REAL NOT NULL,
            churn_rate REAL NOT NULL,
            avg_session_duration REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_events (
            date TEXT NOT NULL,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            segment TEXT NOT NULL,
            event_type TEXT NOT NULL,
            feature_name TEXT,
            price REAL,
            revenue REAL,
            country TEXT,
            region TEXT,
            channel TEXT,
            duration_seconds REAL,
            pageviews INTEGER,
            source TEXT NOT NULL
        )
        """
    )

    conn.commit()


def reset_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    tables = [
        "daily_metrics",
        "feature_usage",
        "funnel_metrics",
        "revenue",
        "churn",
        "acquisition",
        "support_tickets",
        "nps_scores",
        "geo_metrics",
        "staging_events",
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()


def insert_batch(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        """
        INSERT INTO staging_events (
            date, user_id, session_id, platform, segment, event_type,
            feature_name, price, revenue, country, region, channel,
            duration_seconds, pageviews, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )


def ingest_rees46(conn: sqlite3.Connection, path: str, limit: int | None) -> int:
    if not os.path.exists(path):
        print(f"REES46 file not found: {path}")
        return 0

    inserted = 0
    batch: list[tuple] = []
    with open_csv(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit and inserted >= limit:
                break

            event_time = row.get("event_time") or ""
            if not event_time:
                continue

            date = event_time[:10]
            user_id = row.get("user_id") or "unknown"
            session_id = row.get("user_session") or f"{user_id}-{event_time}"
            event_type = (row.get("event_type") or "view").lower()
            feature_name = (
                row.get("category_code")
                or row.get("brand")
                or row.get("product_id")
            )

            try:
                price = float(row.get("price") or 0)
            except ValueError:
                price = 0.0

            revenue = price if event_type == "purchase" else 0.0

            platform = synthesize_platform(user_id)
            segment = synthesize_segment(user_id)
            country = row.get("country") or synthesize_country(user_id)
            region = country_to_region(country)
            channel = "direct"

            batch.append(
                (
                    date,
                    user_id,
                    session_id,
                    platform,
                    segment,
                    event_type,
                    feature_name,
                    price,
                    revenue,
                    country,
                    region,
                    channel,
                    None,
                    None,
                    "rees46",
                )
            )
            inserted += 1

            if len(batch) >= 5000:
                insert_batch(conn, batch)
                conn.commit()
                batch.clear()

    if batch:
        insert_batch(conn, batch)
        conn.commit()

    return inserted


def parse_ga_json(value: str) -> dict | None:
    if not value:
        return None
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def get_ga_field(row: dict, *keys: str) -> str | None:
    dotted = ".".join(keys)
    if dotted in row and row[dotted]:
        return row[dotted]

    if keys[0] in row:
        raw = row.get(keys[0])
        parsed = parse_ga_json(raw)
        if parsed is not None:
            value = parsed
            for k in keys[1:]:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None
            return str(value) if value is not None else None

    fallback = row.get(keys[-1])
    return fallback if fallback else None


def ga_channel_from_medium(medium: str | None, source: str | None) -> str:
    m = (medium or "").lower()
    s = (source or "").lower()
    if m in {"cpc", "ppc", "paid", "paidsearch"}:
        return "paid_search"
    if m in {"organic", "organic search"}:
        return "organic_search"
    if m in {"email", "newsletter"}:
        return "email"
    if "facebook" in s or "twitter" in s or m == "social":
        return "social"
    if m in {"referral"}:
        return "referral"
    if m in {"display", "cpm", "banner"}:
        return "display"
    return "direct"


def ingest_ga(conn: sqlite3.Connection, path: str, limit: int | None) -> int:
    if not os.path.exists(path):
        print(f"GA file not found: {path}")
        return 0

    inserted = 0
    batch: list[tuple] = []
    with open_csv(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit and inserted >= limit:
                break

            date_raw = row.get("date") or row.get("ga_date")
            if date_raw and len(date_raw) == 8 and date_raw.isdigit():
                date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
            else:
                date = (row.get("event_date") or "")[:10]
            if not date:
                continue

            user_id = row.get("fullVisitorId") or row.get("user_id") or "unknown"
            session_id = row.get("visitId") or row.get("session_id") or f"{user_id}-{date}"

            device = get_ga_field(row, "device", "deviceCategory") or row.get("deviceCategory")
            platform = (device or "web").lower()
            if platform not in {"web", "mobile", "tablet"}:
                platform = "web"

            segment = synthesize_segment(user_id)

            country = (
                get_ga_field(row, "geoNetwork", "country")
                or row.get("country")
                or synthesize_country(user_id)
            )
            region = country_to_region(country)

            medium = get_ga_field(row, "trafficSource", "medium")
            source = get_ga_field(row, "trafficSource", "source")
            channel = ga_channel_from_medium(medium, source)

            pageviews = get_ga_field(row, "totals", "pageviews") or row.get("pageviews")
            try:
                pageviews = int(pageviews) if pageviews is not None else None
            except ValueError:
                pageviews = None

            duration = get_ga_field(row, "totals", "timeOnSite") or row.get("timeOnSite")
            try:
                duration_seconds = float(duration) if duration is not None else None
            except ValueError:
                duration_seconds = None

            transactions = get_ga_field(row, "totals", "transactions") or row.get("transactions")
            try:
                transactions = int(transactions) if transactions is not None else 0
            except ValueError:
                transactions = 0

            revenue_raw = (
                get_ga_field(row, "totals", "transactionRevenue")
                or row.get("transactionRevenue")
                or "0"
            )
            try:
                revenue = float(revenue_raw) / 1_000_000.0
            except ValueError:
                revenue = 0.0
            if transactions <= 0:
                revenue = 0.0

            batch.append(
                (
                    date,
                    user_id,
                    session_id,
                    platform,
                    segment,
                    "session",
                    None,
                    None,
                    revenue,
                    country,
                    region,
                    channel,
                    duration_seconds,
                    pageviews,
                    "ga",
                )
            )
            inserted += 1

            if len(batch) >= 5000:
                insert_batch(conn, batch)
                conn.commit()
                batch.clear()

    if batch:
        insert_batch(conn, batch)
        conn.commit()

    return inserted


def build_indices(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_date ON staging_events(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_session ON staging_events(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_user ON staging_events(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_platform ON staging_events(platform)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_segment ON staging_events(segment)")
    conn.commit()


def aggregate_daily_metrics(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS session_stats")
    cursor.execute(
        """
        CREATE TEMP TABLE session_stats AS
        SELECT
            date,
            platform,
            segment,
            session_id,
            user_id,
            CASE
                WHEN MAX(COALESCE(pageviews, 0)) > 0 THEN MAX(pageviews)
                ELSE COUNT(*)
            END AS pageviews,
            CASE
                WHEN MAX(COALESCE(duration_seconds, 0)) > 0 THEN MAX(duration_seconds)
                ELSE COUNT(*) * 30
            END AS duration_seconds,
            MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS has_cart,
            MAX(CASE WHEN event_type = 'purchase' OR revenue > 0 THEN 1 ELSE 0 END) AS has_purchase
        FROM staging_events
        GROUP BY date, platform, segment, session_id, user_id
        """
    )

    cursor.execute(
        """
        INSERT INTO daily_metrics (
            date, platform, segment, dau, wau, mau,
            session_duration_avg, sessions_per_user, bounce_rate, pages_per_session
        )
        SELECT
            date,
            platform,
            segment,
            COUNT(DISTINCT user_id) AS dau,
            0 AS wau,
            0 AS mau,
            ROUND(AVG(duration_seconds) / 60.0, 2) AS session_duration_avg,
            ROUND(CAST(COUNT(DISTINCT session_id) AS REAL) / COUNT(DISTINCT user_id), 2) AS sessions_per_user,
            ROUND(AVG(CASE WHEN pageviews <= 1 THEN 1.0 ELSE 0.0 END), 4) AS bounce_rate,
            ROUND(AVG(pageviews), 2) AS pages_per_session
        FROM session_stats
        GROUP BY date, platform, segment
        """
    )

    cursor.execute("SELECT rowid, dau FROM daily_metrics")
    rows = cursor.fetchall()
    for rowid, dau in rows:
        wau = max(dau, int(round(dau * 1.6)))
        mau = max(wau, int(round(dau * 3.1)))
        cursor.execute(
            "UPDATE daily_metrics SET wau = ?, mau = ? WHERE rowid = ?",
            (wau, mau, rowid),
        )

    conn.commit()


def aggregate_feature_usage(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH total_sessions AS (
            SELECT date, platform, segment, COUNT(DISTINCT session_id) AS total_sessions
            FROM session_stats
            GROUP BY date, platform, segment
        ), feature_sessions AS (
            SELECT
                date,
                platform,
                segment,
                feature_name,
                session_id,
                COUNT(*) AS events
            FROM staging_events
            WHERE feature_name IS NOT NULL
            GROUP BY date, platform, segment, feature_name, session_id
        ), feature_rollup AS (
            SELECT
                date,
                platform,
                segment,
                feature_name,
                COUNT(DISTINCT session_id) AS sessions_with_feature,
                AVG(events) * 0.5 AS avg_time_in_feature
            FROM feature_sessions
            GROUP BY date, platform, segment, feature_name
        ), purchase_sessions AS (
            SELECT
                date,
                platform,
                segment,
                feature_name,
                COUNT(DISTINCT session_id) AS purchase_sessions
            FROM staging_events
            WHERE feature_name IS NOT NULL AND (event_type = 'purchase' OR revenue > 0)
            GROUP BY date, platform, segment, feature_name
        )
        INSERT INTO feature_usage (
            date, feature_name, platform, segment,
            adoption_rate, sessions_with_feature, drop_off_rate, avg_time_in_feature
        )
        SELECT
            f.date,
            f.feature_name,
            f.platform,
            f.segment,
            ROUND(CAST(f.sessions_with_feature AS REAL) / t.total_sessions, 4) AS adoption_rate,
            f.sessions_with_feature,
            ROUND(
                CASE
                    WHEN f.sessions_with_feature = 0 THEN 0
                    ELSE 1.0 - CAST(COALESCE(p.purchase_sessions, 0) AS REAL) / f.sessions_with_feature
                END,
                4
            ) AS drop_off_rate,
            ROUND(f.avg_time_in_feature, 2) AS avg_time_in_feature
        FROM feature_rollup f
        JOIN total_sessions t
            ON t.date = f.date AND t.platform = f.platform AND t.segment = f.segment
        LEFT JOIN purchase_sessions p
            ON p.date = f.date AND p.platform = f.platform
            AND p.segment = f.segment AND p.feature_name = f.feature_name
        """
    )
    conn.commit()


def aggregate_funnel_metrics(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH base AS (
            SELECT date, platform, segment, COUNT(DISTINCT user_id) AS users
            FROM session_stats
            GROUP BY date, platform, segment
        ), cart AS (
            SELECT date, platform, segment, COUNT(DISTINCT user_id) AS users
            FROM session_stats
            WHERE has_cart = 1
            GROUP BY date, platform, segment
        ), purchase AS (
            SELECT date, platform, segment, COUNT(DISTINCT user_id) AS users
            FROM session_stats
            WHERE has_purchase = 1
            GROUP BY date, platform, segment
        )
        INSERT INTO funnel_metrics (date, funnel_step, platform, segment, conversion_rate, users_count)
        SELECT b.date, 'browse', b.platform, b.segment, 1.0, b.users FROM base b
        UNION ALL
        SELECT b.date, 'cart', b.platform, b.segment,
            ROUND(CAST(COALESCE(c.users, 0) AS REAL) / b.users, 4),
            COALESCE(c.users, 0)
        FROM base b
        LEFT JOIN cart c ON c.date = b.date AND c.platform = b.platform AND c.segment = b.segment
        UNION ALL
        SELECT b.date, 'purchase', b.platform, b.segment,
            ROUND(CAST(COALESCE(p.users, 0) AS REAL) / b.users, 4),
            COALESCE(p.users, 0)
        FROM base b
        LEFT JOIN purchase p ON p.date = b.date AND p.platform = b.platform AND p.segment = b.segment
        """
    )
    conn.commit()


def aggregate_acquisition(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date, channel, platform, COUNT(DISTINCT user_id) AS users
        FROM staging_events
        WHERE source = 'ga'
        GROUP BY date, channel, platform
        """
    )
    rows = cursor.fetchall()

    def channel_cac(channel: str) -> float:
        base = {
            "paid_search": 42.0,
            "organic_search": 18.0,
            "social": 28.0,
            "email": 12.0,
            "referral": 20.0,
            "display": 35.0,
            "direct": 15.0,
        }
        return base.get(channel, 22.0)

    inserts = []
    for date, channel, platform, users in rows:
        users = users or 0
        cac = channel_cac(channel)
        spend = round(users * cac, 2)
        ltv = round(cac * 3.5, 2)
        ratio = round(ltv / cac, 2) if cac else 0
        inserts.append((date, channel, platform, users, cac, ltv, ratio, spend))

    cursor.executemany(
        "INSERT INTO acquisition VALUES (?,?,?,?,?,?,?,?)",
        inserts,
    )
    conn.commit()


def aggregate_revenue(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date, segment, SUM(revenue) AS revenue, COUNT(DISTINCT user_id) AS customers
        FROM staging_events
        WHERE revenue > 0
        GROUP BY date, segment
        """
    )
    rows = cursor.fetchall()

    inserts = []
    for date, segment, revenue, customers in rows:
        revenue = revenue or 0.0
        customers = customers or 0
        mrr = round(revenue * 30, 2)
        arr = round(mrr * 12, 2)
        new_mrr = round(mrr * 0.12, 2)
        churned_mrr = round(mrr * 0.03, 2)
        expansion_mrr = round(mrr * 0.05, 2)
        arpu = round(mrr / customers, 2) if customers else 0.0
        inserts.append(
            (date, segment, mrr, arr, new_mrr, churned_mrr, expansion_mrr, customers, arpu)
        )

    cursor.executemany("INSERT INTO revenue VALUES (?,?,?,?,?,?,?,?,?)", inserts)
    conn.commit()


def aggregate_geo_metrics(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            s.date,
            e.region,
            s.segment,
            COUNT(DISTINCT s.user_id) AS dau,
            SUM(e.revenue) AS revenue,
            ROUND(AVG(s.duration_seconds) / 60.0, 2) AS avg_session_duration
        FROM session_stats s
        JOIN staging_events e
            ON e.session_id = s.session_id
            AND e.date = s.date
            AND e.platform = s.platform
            AND e.segment = s.segment
        GROUP BY s.date, e.region, s.segment
        """
    )
    rows = cursor.fetchall()

    inserts = []
    for date, region, segment, dau, revenue, avg_duration in rows:
        seed = hash_bucket(f"{date}-{region}-{segment}")
        churn_rate = round(0.015 + (seed / 1000.0), 4)
        inserts.append((date, region, segment, dau, revenue or 0.0, churn_rate, avg_duration or 0.0))

    cursor.executemany("INSERT INTO geo_metrics VALUES (?,?,?,?,?,?,?)", inserts)
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest REES46 + GA datasets into engagement.db")
    parser.add_argument("--db", default=DB_DEFAULT, help="Path to SQLite DB")
    parser.add_argument("--rees46", default="rees46_events.csv", help="Path to REES46 events CSV")
    parser.add_argument("--ga", default="ga_sessions.csv", help="Path to GA sessions CSV")
    parser.add_argument("--reset", action="store_true", help="Delete existing data before ingest")
    parser.add_argument("--limit", type=int, default=None, help="Row limit per dataset")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=OFF")

    ensure_schema(conn)
    if args.reset:
        reset_tables(conn)

    rees_count = ingest_rees46(conn, args.rees46, args.limit)
    ga_count = ingest_ga(conn, args.ga, args.limit)

    build_indices(conn)
    aggregate_daily_metrics(conn)
    aggregate_feature_usage(conn)
    aggregate_funnel_metrics(conn)
    aggregate_acquisition(conn)
    aggregate_revenue(conn)
    aggregate_geo_metrics(conn)

    conn.close()

    print(f"Ingested REES46 rows: {rees_count}")
    print(f"Ingested GA rows: {ga_count}")
    print("Aggregation complete.")


if __name__ == "__main__":
    main()
