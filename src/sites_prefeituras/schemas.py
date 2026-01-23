"""Ibis schema definitions for append-only database tables.

Design Principles:
- All tables are APPEND-ONLY (no updates or deletes)
- Each record has a version timestamp for tracking changes
- Views provide the "current" state by selecting latest version per entity
- This enables full audit trail and time-travel queries
"""

import ibis
from ibis import Schema
from ibis.expr import datatypes as dt

# ============================================================================
# Table Schemas (Append-Only)
# ============================================================================

# Audits table - naturally append-only (each audit is a point-in-time snapshot)
AUDITS_SCHEMA = Schema(
    {
        "id": dt.Int64(nullable=False),
        "url": dt.String(nullable=False),
        "timestamp": dt.Timestamp(nullable=False),
        "mobile_result": dt.JSON(nullable=True),
        "desktop_result": dt.JSON(nullable=True),
        "error_message": dt.String(nullable=True),
        "retry_count": dt.Int64(nullable=True),
        "created_at": dt.Timestamp(nullable=True),
    }
)

# Audit summaries - naturally append-only (derived from audits)
AUDIT_SUMMARIES_SCHEMA = Schema(
    {
        "id": dt.Int64(nullable=False),
        "url": dt.String(nullable=False),
        "timestamp": dt.Timestamp(nullable=False),
        # Lighthouse Scores (0-1 normalized)
        "mobile_performance": dt.Float64(nullable=True),
        "mobile_accessibility": dt.Float64(nullable=True),
        "mobile_best_practices": dt.Float64(nullable=True),
        "mobile_seo": dt.Float64(nullable=True),
        "desktop_performance": dt.Float64(nullable=True),
        "desktop_accessibility": dt.Float64(nullable=True),
        "desktop_best_practices": dt.Float64(nullable=True),
        "desktop_seo": dt.Float64(nullable=True),
        # Core Web Vitals
        "mobile_fcp": dt.Float64(nullable=True),
        "mobile_lcp": dt.Float64(nullable=True),
        "mobile_cls": dt.Float64(nullable=True),
        "mobile_fid": dt.Float64(nullable=True),
        "desktop_fcp": dt.Float64(nullable=True),
        "desktop_lcp": dt.Float64(nullable=True),
        "desktop_cls": dt.Float64(nullable=True),
        "desktop_fid": dt.Float64(nullable=True),
        # Status
        "has_errors": dt.Boolean(nullable=True),
        "error_message": dt.String(nullable=True),
        "created_at": dt.Timestamp(nullable=True),
    }
)

# Quarantine table - append-only with versioning
# Each status change creates a new record; views show current state
QUARANTINE_SCHEMA = Schema(
    {
        "id": dt.Int64(nullable=False),
        "url": dt.String(nullable=False),
        "first_failure": dt.Timestamp(nullable=False),
        "last_failure": dt.Timestamp(nullable=False),
        "consecutive_failures": dt.Int64(nullable=True),
        "last_error_message": dt.String(nullable=True),
        "status": dt.String(nullable=True),
        "notes": dt.String(nullable=True),
        "version": dt.Int64(nullable=False),  # Version number for this URL
        "valid_from": dt.Timestamp(nullable=False),  # When this version became valid
        "created_at": dt.Timestamp(nullable=True),
    }
)


# ============================================================================
# Table Creation DDL (for Ibis with DuckDB backend)
# ============================================================================


def create_tables(con: ibis.BaseBackend) -> None:
    """Create all append-only tables using raw DDL via Ibis connection.

    All tables are append-only:
    - audits: naturally append-only (each audit is a snapshot)
    - audit_summaries: naturally append-only (derived from audits)
    - quarantine: versioned append-only (new row for each status change)

    Views provide "current state" by selecting latest version per entity.
    """
    # Create audits table (append-only by design)
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY,
            url VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            mobile_result JSON,
            desktop_result JSON,
            error_message VARCHAR,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create audit_summaries table (append-only by design)
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS audit_summaries (
            id INTEGER PRIMARY KEY,
            url VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            mobile_performance DOUBLE,
            mobile_accessibility DOUBLE,
            mobile_best_practices DOUBLE,
            mobile_seo DOUBLE,
            desktop_performance DOUBLE,
            desktop_accessibility DOUBLE,
            desktop_best_practices DOUBLE,
            desktop_seo DOUBLE,
            mobile_fcp DOUBLE,
            mobile_lcp DOUBLE,
            mobile_cls DOUBLE,
            mobile_fid DOUBLE,
            desktop_fcp DOUBLE,
            desktop_lcp DOUBLE,
            desktop_cls DOUBLE,
            desktop_fid DOUBLE,
            has_errors BOOLEAN DEFAULT FALSE,
            error_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create quarantine table (append-only with versioning)
    # Each status change or update creates a new row with incremented version
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS quarantine (
            id INTEGER PRIMARY KEY,
            url VARCHAR NOT NULL,
            first_failure TIMESTAMP NOT NULL,
            last_failure TIMESTAMP NOT NULL,
            consecutive_failures INTEGER DEFAULT 1,
            last_error_message VARCHAR,
            status VARCHAR DEFAULT 'quarantined',
            notes VARCHAR,
            version INTEGER DEFAULT 1,
            valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create view for current quarantine state (latest version per URL)
    con.raw_sql("DROP VIEW IF EXISTS quarantine_current")
    con.raw_sql("""
        CREATE VIEW quarantine_current AS
        SELECT
            q.id,
            q.url,
            q.first_failure,
            q.last_failure,
            q.consecutive_failures,
            q.last_error_message,
            q.status,
            q.notes,
            q.version,
            q.valid_from,
            q.created_at
        FROM quarantine q
        INNER JOIN (
            SELECT url, MAX(version) as max_version
            FROM quarantine
            GROUP BY url
        ) latest ON q.url = latest.url AND q.version = latest.max_version
    """)

    # Create indexes for performance
    con.raw_sql("CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url)")
    con.raw_sql("CREATE INDEX IF NOT EXISTS idx_audits_timestamp ON audits(timestamp)")
    con.raw_sql("CREATE INDEX IF NOT EXISTS idx_summaries_url ON audit_summaries(url)")
    con.raw_sql("CREATE INDEX IF NOT EXISTS idx_quarantine_url ON quarantine(url)")
    con.raw_sql(
        "CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine(status)"
    )
    con.raw_sql(
        "CREATE INDEX IF NOT EXISTS idx_quarantine_version ON quarantine(url, version)"
    )


def get_table(con: ibis.BaseBackend, table_name: str) -> ibis.Table:
    """Get an Ibis table reference by name."""
    return con.table(table_name)


def table_exists(con: ibis.BaseBackend, table_name: str) -> bool:
    """Check if a table exists in the database."""
    return table_name in con.list_tables()
