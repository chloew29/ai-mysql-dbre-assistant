"""
MySQL DBRE Health Report
Checks: replication health, replica safety, table growth, slow query patterns.
Run: python monitoring/generate_health_report.py
"""
import pymysql
from datetime import datetime

PRIMARY = dict(host="127.0.0.1", port=3306, user="root",
               password="rootpass", database="ecommerce_ops")
REPLICA = dict(host="127.0.0.1", port=3307, user="root",
               password="rootpass", database="ecommerce_ops")

LAG_WARN_SECONDS = 5
issues = []          # collected problems for the summary


def connect(cfg):
    return pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)


def check_replication():
    """IO/SQL threads + lag, queried from the replica."""
    lines = ["## 1. Replication Health (replica)"]
    with connect(REPLICA) as conn, conn.cursor() as cur:
        cur.execute("SHOW REPLICA STATUS")
        row = cur.fetchone()
        if not row:
            issues.append("Replication is NOT configured on the replica")
            lines.append("- [CRIT] No replication status found")
            return lines
        io, sql = row["Replica_IO_Running"], row["Replica_SQL_Running"]
        lag = row["Seconds_Behind_Source"]
        for name, val in (("IO thread", io), ("SQL thread", sql)):
            ok = val == "Yes"
            lines.append(f"- [{'OK' if ok else 'CRIT'}] {name}: {val}")
            if not ok:
                issues.append(f"Replication {name} not running "
                              f"(Last_Error: {row.get('Last_SQL_Error') or row.get('Last_IO_Error')})")
        if lag is None:
            lines.append("- [CRIT] Lag: unknown (replication broken)")
            issues.append("Replication lag unknown")
        elif lag > LAG_WARN_SECONDS:
            lines.append(f"- [WARN] Lag: {lag}s (threshold {LAG_WARN_SECONDS}s)")
            issues.append(f"Replication lag {lag}s exceeds threshold")
        else:
            lines.append(f"- [OK] Lag: {lag}s")
    return lines


def check_replica_safety():
    """The replica must be locked read-only (lesson learned the hard way)."""
    lines = ["## 2. Replica Safety"]
    with connect(REPLICA) as conn, conn.cursor() as cur:
        cur.execute("SELECT @@super_read_only AS sro")
        sro = cur.fetchone()["sro"]
        if sro == 1:
            lines.append("- [OK] super_read_only = ON")
        else:
            lines.append("- [CRIT] super_read_only = OFF — replica is writable!")
            issues.append("Replica is writable (risk of data divergence)")
    return lines


def check_table_sizes():
    """Largest tables on the primary, via information_schema."""
    lines = ["## 3. Table Sizes (primary)"]
    q = """SELECT table_name,
                  table_rows,
                  ROUND((data_length + index_length)/1024/1024, 1) AS size_mb,
                  ROUND(index_length/1024/1024, 1) AS index_mb
           FROM information_schema.tables
           WHERE table_schema = 'ecommerce_ops'
           ORDER BY (data_length + index_length) DESC
           LIMIT 5"""
    with connect(PRIMARY) as conn, conn.cursor() as cur:
        cur.execute(q)
        for r in cur.fetchall():
            lines.append(f"- {r['TABLE_NAME']}: ~{r['TABLE_ROWS']} rows, "
                         f"{r['size_mb']} MB total ({r['index_mb']} MB index)")
    return lines


def check_slow_patterns():
    """Top queries by avg latency + full-scan offenders, via performance_schema."""
    lines = ["## 4. Slow Query Patterns (performance_schema)"]
    q = """SELECT LEFT(digest_text, 80) AS query,
                  count_star AS calls,
                  ROUND(avg_timer_wait/1e12, 4) AS avg_seconds,
                  sum_rows_examined AS rows_examined,
                  sum_rows_sent AS rows_sent,
                  sum_no_index_used AS no_index_used
           FROM performance_schema.events_statements_summary_by_digest
           WHERE schema_name = 'ecommerce_ops'
             AND digest_text LIKE 'SELECT%%'
           ORDER BY avg_timer_wait DESC
           LIMIT 5"""
    with connect(PRIMARY) as conn, conn.cursor() as cur:
        cur.execute(q)
        for r in cur.fetchall():
            flag = "WARN" if r["no_index_used"] > 0 else "OK"
            waste = (r["rows_examined"] / r["rows_sent"]) if r["rows_sent"] else 0
            lines.append(f"- [{flag}] avg {r['avg_seconds']}s, calls {r['calls']}, "
                         f"examined/sent ratio {waste:.0f}x | {r['query']}")
            if r["no_index_used"] > 0:
                issues.append(f"Full scan pattern: {r['query'][:60]}")
    return lines


def main():
    report = [f"# Database Health Report — {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for section in (check_replication, check_replica_safety,
                    check_table_sizes, check_slow_patterns):
        report.extend(section())
        report.append("")
    report.append("## Summary")
    if issues:
        report.append(f"{len(issues)} issue(s) need attention:")
        report.extend(f"- {i}" for i in issues)
    else:
        report.append("All checks passed.")
    text = "\n".join(report)
    print(text)
    fname = f"results/health_report_{datetime.now():%Y%m%d_%H%M%S}.md"
    with open(fname, "w") as f:
        f.write(text)
    print(f"\nSaved: {fname}")


if __name__ == "__main__":
    main()