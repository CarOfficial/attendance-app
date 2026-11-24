"""Wipe every record in the database, keeping only the admin login.

Run from the backend directory with the server's virtualenv:
    .venv/Scripts/python.exe scripts/reset_data.py --yes

Deletes: attendance records, leave requests, forgotten check-out requests, every
user whose role is not "admin" (plus their branch assignments) and all branches
(office locations).
Keeps: admin accounts and the work-schedule settings.

Pass --keep-branches to keep the office locations.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BACKEND_DIR / "data" / "attendance.db"

DATA_TABLES = ("late_checkout_requests", "leave_requests", "attendance_records")
ADMIN_ONLY_TABLES = ("employee_branches", "branches")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="actually delete (otherwise only report)")
    parser.add_argument("--keep-branches", action="store_true", help="keep office locations")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"database not found: {DB_PATH}", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    admins = [row[0] for row in cur.execute("SELECT id, username FROM users WHERE role = 'admin'")]
    if not admins:
        print("refusing to run: no admin account found in the database", file=sys.stderr)
        return 1

    counts = {table: cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in DATA_TABLES}
    employees = cur.execute("SELECT COUNT(*) FROM users WHERE role <> 'admin'").fetchone()[0]
    branches = cur.execute("SELECT COUNT(*) FROM branches").fetchone()[0]

    print(f"database: {DB_PATH}")
    print(f"will delete: {counts}, employees: {employees}, branches: {branches}")
    print("will keep: admin users, work schedule" + (", branches" if args.keep_branches else ""))

    if not args.yes:
        print("\ndry run — pass --yes to apply", file=sys.stderr)
        return 0

    with con:
        for table in DATA_TABLES:
            cur.execute(f"DELETE FROM {table}")
        placeholders = ",".join("?" * len(admins))
        cur.execute(
            f"DELETE FROM employee_branches WHERE user_id NOT IN ({placeholders})",
            admins,
        )
        cur.execute("DELETE FROM users WHERE role <> 'admin'")
        if not args.keep_branches:
            cur.execute("DELETE FROM employee_branches")
            cur.execute("DELETE FROM branches")
        # sqlite_sequence only exists once an AUTOINCREMENT table has been written to.
        has_sequence = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
        ).fetchone()
        if has_sequence:
            tables = set(DATA_TABLES)
            if not args.keep_branches:
                tables |= set(ADMIN_ONLY_TABLES)
            marks = ",".join("?" * len(tables))
            cur.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({marks})", tuple(tables))

    remaining = cur.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    left_branches = cur.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
    print("\ndone. remaining users:")
    for row in remaining:
        print(f"  id={row[0]} username={row[1]} role={row[2]}")
    print(f"remaining branches: {left_branches}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
