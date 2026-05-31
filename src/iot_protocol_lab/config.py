from __future__ import annotations

from pathlib import Path


MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC_ROOT = "iot/lab"

# 数据库放在项目目录下的data文件夹
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "iot_messages.db"


# 为每种传感器都设置一个正常范围和告警上限
SENSOR_TYPES = {
    "temperature": {"unit": "C", "normal": (18.0, 32.0), "alert_above": 35.0},
    "humidity": {"unit": "%", "normal": (35.0, 75.0), "alert_above": 85.0},
    "light": {"unit": "lux", "normal": (120.0, 800.0), "alert_above": 950.0},
    "air_quality": {"unit": "AQI", "normal": (20.0, 120.0), "alert_above": 150.0},
}
