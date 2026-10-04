"""Export the pinned panel inputs through a local read-only Snowflake session."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import sys


MAX_ROWS = 20_000
EXPECTED_COLUMNS = (
    "SOURCE_ID", "BATCH_SHA256", "ROW_INDEX", "ROW_SHA256", "LOADED_AT", "PAYLOAD_JSON"
)


def connect_kwargs(env):
    required = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_WAREHOUSE")
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise ValueError("missing connection settings: " + ", ".join(missing))
    kwargs = {"account": env["SNOWFLAKE_ACCOUNT"], "user": env["SNOWFLAKE_USER"],
              "warehouse": env["SNOWFLAKE_WAREHOUSE"]}
    for key, arg in (("SNOWFLAKE_ROLE", "role"), ("SNOWFLAKE_PASSWORD", "password"),
                     ("SNOWFLAKE_AUTHENTICATOR", "authenticator"),
                     ("SNOWFLAKE_TOKEN", "token"),
                     ("SNOWFLAKE_PRIVATE_KEY_FILE", "private_key_file"),
                     ("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "private_key_file_pwd")):
        if env.get(key):
            kwargs[arg] = env[key]
    if not any(k in kwargs for k in ("password", "authenticator", "token", "private_key_file")):
        raise ValueError("configure a supported local authentication method")
    return kwargs


def export(output, limit=MAX_ROWS, env=None):
    env = os.environ if env is None else env
    if not 1 <= limit <= MAX_ROWS:
        raise ValueError(f"row limit must be between 1 and {MAX_ROWS}")
    repo = Path(__file__).resolve().parents[3]
    target = Path(output).expanduser().resolve()
    try:
        target.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ValueError("export must be outside the repository")
    if not target.parent.is_dir():
        raise ValueError("output directory must already exist")

    query_path = Path(__file__).with_name("development_export.sql")
    query = query_path.read_text(encoding="utf-8").strip().rstrip(";")
    if not query.lower().startswith("-- read-only") or "SELECT SOURCE_ID" not in query:
        raise ValueError("pinned query is missing its read-only marker or expected projection")

    try:
        import snowflake.connector
    except ImportError as exc:
        raise RuntimeError("install src/unified_factors/panel/requirements-local.txt first") from exc

    connection = snowflake.connector.connect(**connect_kwargs(env))
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = tuple(item[0] for item in (cursor.description or ()))
        if columns != EXPECTED_COLUMNS:
            raise ValueError(f"unexpected Snowflake result schema: {columns}")
        rows = cursor.fetchmany(limit + 1)
        if len(rows) > limit:
            raise ValueError(f"query returned more than {limit} rows; no export written")
    finally:
        connection.close()

    # Exclusive create prevents overwriting an existing file; restrictive permissions
    # are applied atomically by the OS before any vendor payload is written.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise

    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"rows": len(rows), "sha256": checksum, "permissions": "0600",
            "study_window_end": "2022-09-30", "path": str(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="new private CSV path outside the repository")
    parser.add_argument("--limit", default=MAX_ROWS, type=int,
                        help=f"maximum export rows (1..{MAX_ROWS})")
    args = parser.parse_args()
    try:
        result = export(args.output, args.limit)
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 2
    print(f"exported {result['rows']} rows; SHA-256 {result['sha256']}; permissions {result['permissions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
