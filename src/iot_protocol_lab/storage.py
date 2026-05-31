from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .config import DB_PATH


# 在首次创建数据库或者每次查询时调用，以防数据库不存在
def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mqtt_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at REAL NOT NULL,
                topic TEXT NOT NULL,
                device_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                qos INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                alert INTEGER NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_mqtt_message(row: dict[str, Any], db_path: Path = DB_PATH) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO mqtt_messages (
                received_at, topic, device_id, sensor_type, value, unit, qos,
                latency_ms, alert, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["received_at"],
                row["topic"],
                row["device_id"],
                row["sensor_type"],
                row["value"],
                row["unit"],
                row["qos"],
                row["latency_ms"],
                int(row["alert"]),
                row["payload"],
            ),
        )
        conn.commit()


def latest_by_sensor(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT m.*
            FROM mqtt_messages m
            JOIN (
                SELECT device_id, sensor_type, MAX(id) AS max_id
                FROM mqtt_messages
                GROUP BY device_id, sensor_type
            ) latest ON m.id = latest.max_id
            ORDER BY m.device_id, m.sensor_type
            """
        ).fetchall()
    return [dict(row) for row in rows]


def recent_messages(limit: int = 50, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT *
            FROM mqtt_messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def summary_stats(db_path: Path = DB_PATH) -> dict[str, Any]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_messages,
                AVG(latency_ms) AS avg_latency_ms,
                MIN(latency_ms) AS min_latency_ms,
                MAX(latency_ms) AS max_latency_ms,
                SUM(alert) AS alert_count
            FROM mqtt_messages
            """
        ).fetchone()
    stats = dict(row)
    # 防止返回none导致数据出错
    for key in ("avg_latency_ms", "min_latency_ms", "max_latency_ms"):
        stats[key] = round(stats[key] or 0.0, 3)
    stats["total_messages"] = stats["total_messages"] or 0
    stats["alert_count"] = stats["alert_count"] or 0
    return stats

