from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from .config import MQTT_HOST, MQTT_PORT, MQTT_TOPIC_ROOT, SENSOR_TYPES


def build_payload(device_id: str, sensor_type: str, qos: int) -> dict[str, object]:
    meta = SENSOR_TYPES[sensor_type]
    low, high = meta["normal"]
    # 随机产生数据，并让8%概论发送的是预警值
    if random.random() < 0.08:
        value = float(meta["alert_above"]) + random.uniform(0.5, 8.0)
    else:
        value = random.uniform(float(low), float(high))

    return {
        "device_id": device_id,
        "sensor_type": sensor_type,
        "value": round(value, 2),
        "unit": meta["unit"],
        "sent_at": time.time(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "qos": qos,
    }


def run_simulator(host: str, port: int, devices: int, interval: float, qos: int) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="iot-simulator")
    client.connect(host, port, keepalive=30)
    client.loop_start()

    device_ids = [f"device_{index:02d}" for index in range(1, devices + 1)]
    sensor_types = list(SENSOR_TYPES)
    print(f"Publishing MQTT sensor data to {host}:{port}, qos={qos}")

    try:
        while True:
            for device_id in device_ids:
                sensor_type = random.choice(sensor_types)
                payload = build_payload(device_id, sensor_type, qos)
                topic = f"{MQTT_TOPIC_ROOT}/{device_id}/{sensor_type}"
                client.publish(topic, json.dumps(payload), qos=qos)
                print(f"{topic} -> {payload['value']}{payload['unit']}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Simulator stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MQTT IoT sensor simulator")
    parser.add_argument("--host", default=MQTT_HOST)
    parser.add_argument("--port", type=int, default=MQTT_PORT)
    parser.add_argument("--devices", type=int, default=4)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_simulator(args.host, args.port, args.devices, args.interval, args.qos)


if __name__ == "__main__":
    main()

