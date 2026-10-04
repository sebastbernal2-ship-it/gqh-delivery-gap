"""Immutable, hash-addressed research report storage in Snowflake."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import sync

TABLE = "VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS"


def _connection():
    import snowflake.connector

    sync.load_local_env()
    name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if name:
        return snowflake.connector.connect(connection_name=name)
    options = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": "VECTOR_RESEARCH",
        "schema": "RAW",
    }
    if os.getenv("SNOWFLAKE_ROLE"):
        options["role"] = os.environ["SNOWFLAKE_ROLE"]
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        options["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
    else:
        options["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**options)


def publish_artifacts(paths: list[Path], *, generated_at: str,
                      input_lineage: dict) -> dict[str, str]:
    """Insert exact report bytes once and verify the stored content hash.

    Source inputs stay in their own hash-addressed tables. This table is for compact derived
    artifacts and carries their exact source-batch/file lineage; it is not a raw-source substitute.
    """
    lineage_json = json.dumps(input_lineage, sort_keys=True, separators=(",", ":"))
    payloads: dict[str, tuple[str, str, str]] = {}
    for path in paths:
        payload = path.read_bytes()
        if len(payload) > 4_000_000:
            raise ValueError(f"refusing to bind oversized report artifact: {path.name}")
        digest = hashlib.sha256(payload).hexdigest()
        payloads[path.name] = (digest, "csv" if path.suffix.lower() == ".csv" else "json",
                               payload.decode("utf-8"))

    connection = _connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                ARTIFACT_SHA256 VARCHAR NOT NULL,
                ARTIFACT_NAME VARCHAR NOT NULL,
                ARTIFACT_TYPE VARCHAR NOT NULL,
                GENERATED_AT TIMESTAMP_TZ NOT NULL,
                CONTENT VARCHAR NOT NULL,
                INPUTS_JSON VARIANT NOT NULL,
                PRIMARY KEY (ARTIFACT_SHA256, ARTIFACT_NAME))""")
            for name, (digest, artifact_type, content) in payloads.items():
                cursor.execute(f"""INSERT INTO {TABLE}
                    (ARTIFACT_SHA256,ARTIFACT_NAME,ARTIFACT_TYPE,GENERATED_AT,CONTENT,INPUTS_JSON)
                    SELECT %s,%s,%s,%s,%s,PARSE_JSON(%s)
                    WHERE NOT EXISTS (SELECT 1 FROM {TABLE}
                      WHERE ARTIFACT_SHA256=%s AND ARTIFACT_NAME=%s)""",
                    (digest, name, artifact_type, generated_at, content, lineage_json,
                     digest, name))
                cursor.execute(f"""SELECT SHA2(CONTENT, 256), CONTENT FROM {TABLE}
                    WHERE ARTIFACT_SHA256=%s AND ARTIFACT_NAME=%s""", (digest, name))
                stored = cursor.fetchone()
                if not stored or str(stored[0]).lower() != digest or stored[1] != content:
                    raise RuntimeError(f"Snowflake artifact verification failed: {name}")
        connection.commit()
    finally:
        connection.close()
    return {name: digest for name, (digest, _, _) in payloads.items()}
