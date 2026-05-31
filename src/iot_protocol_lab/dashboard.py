from __future__ import annotations

import argparse
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .config import MQTT_HOST, MQTT_PORT, MQTT_TOPIC_ROOT, SENSOR_TYPES
from .storage import init_db, insert_mqtt_message, latest_by_sensor, recent_messages, summary_stats


def is_alert(sensor_type: str, value: float) -> bool:
    threshold = SENSOR_TYPES.get(sensor_type, {}).get("alert_above")
    return bool(threshold is not None and value >= float(threshold))


def start_mqtt_collector(host: str, port: int) -> mqtt.Client:
    init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="iot-dashboard")

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        print(f"Dashboard connected to MQTT broker: {reason_code}")
        # +匹配所有的设备编号和传感器类型
        client.subscribe(f"{MQTT_TOPIC_ROOT}/+/+", qos=2)

    def on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        received_at = time.time()
        try:
            payload_text = message.payload.decode("utf-8")
            payload = json.loads(payload_text)
            sensor_type = str(payload["sensor_type"])
            value = float(payload["value"])
            # 用发送和接收时间估算消息经 Broker 转发后的端到端延迟
            latency_ms = max(0.0, (received_at - float(payload["sent_at"])) * 1000)
            row = {
                "received_at": received_at,
                "topic": message.topic,
                "device_id": str(payload["device_id"]),
                "sensor_type": sensor_type,
                "value": value,
                "unit": str(payload["unit"]),
                "qos": int(message.qos),
                "latency_ms": latency_ms,
                "alert": is_alert(sensor_type, value),
                "payload": payload_text,
            }
            insert_mqtt_message(row)
        except Exception as exc:
            print(f"Failed to process MQTT message on {message.topic}: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message

    def worker() -> None:
        while True:
            try:
                client.connect(host, port, keepalive=30)
                client.loop_forever()
            except OSError as exc:
                print(f"Waiting for MQTT broker at {host}:{port}: {exc}")
                time.sleep(2)

    threading.Thread(target=worker, daemon=True).start()
    return client


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_mqtt_collector(app.state.mqtt_host, app.state.mqtt_port)
    yield


app = FastAPI(lifespan=lifespan)
app.state.mqtt_host = MQTT_HOST
app.state.mqtt_port = MQTT_PORT


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return DASHBOARD_HTML


@app.get("/api/latest")
def api_latest() -> list[dict[str, Any]]:
    return latest_by_sensor()


@app.get("/api/messages")
def api_messages(limit: int = 30) -> list[dict[str, Any]]:
    return recent_messages(limit=limit)


@app.get("/api/stats")
def api_stats() -> dict[str, Any]:
    return summary_stats()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MQTT IoT dashboard")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app.state.mqtt_host = args.mqtt_host
    app.state.mqtt_port = args.mqtt_port
    uvicorn.run(app, host=args.host, port=args.port)


DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IoT MQTT Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --text: #1d2433;
      --muted: #667085;
      --line: #d8dee9;
      --ok: #0f9f6e;
      --warn: #c2410c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      padding: 20px 28px 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0 0 6px; font-size: 24px; letter-spacing: 0; }
    .sub { color: var(--muted); font-size: 14px; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px;
    }
    .stats, .latest {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .card, .table-wrap {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { margin-top: 8px; font-size: 24px; font-weight: 700; }
    .sensor .value { font-size: 20px; }
    .alert { color: var(--warn); }
    .ok { color: var(--ok); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }
    th { color: var(--muted); font-weight: 600; }
    .table-wrap { overflow-x: auto; }
  </style>
</head>
<body>
  <header>
    <h1>MQTT IoT Data Monitor</h1>
    <div class="sub">Sensor simulator -> MQTT Broker -> Subscriber collector -> SQLite -> Web Dashboard</div>
  </header>
  <main>
    <section class="stats" id="stats"></section>
    <section class="latest" id="latest"></section>
    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Topic</th>
            <th>Device</th>
            <th>Type</th>
            <th>Value</th>
            <th>QoS</th>
            <th>Latency(ms)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="messages"></tbody>
      </table>
    </section>
  </main>
  <script>
    const fmt = (n) => Number(n || 0).toFixed(2);
    const timeText = (ts) => new Date(ts * 1000).toLocaleTimeString();

    async function refresh() {
      const [stats, latest, messages] = await Promise.all([
        fetch('/api/stats').then(r => r.json()),
        fetch('/api/latest').then(r => r.json()),
        fetch('/api/messages?limit=30').then(r => r.json())
      ]);

      document.querySelector('#stats').innerHTML = [
        ['Total messages', stats.total_messages],
        ['Average latency', `${fmt(stats.avg_latency_ms)} ms`],
        ['Minimum latency', `${fmt(stats.min_latency_ms)} ms`],
        ['Maximum latency', `${fmt(stats.max_latency_ms)} ms`],
        ['Alert count', stats.alert_count],
      ].map(([label, value]) => `
        <article class="card">
          <div class="label">${label}</div>
          <div class="value">${value}</div>
        </article>
      `).join('');

      document.querySelector('#latest').innerHTML = latest.map(row => `
        <article class="card sensor">
          <div class="label">${row.device_id} / ${row.sensor_type}</div>
          <div class="value ${row.alert ? 'alert' : 'ok'}">${fmt(row.value)} ${row.unit}</div>
          <div class="label">${fmt(row.latency_ms)} ms</div>
        </article>
      `).join('');

      document.querySelector('#messages').innerHTML = messages.map(row => `
        <tr>
          <td>${timeText(row.received_at)}</td>
          <td>${row.topic}</td>
          <td>${row.device_id}</td>
          <td>${row.sensor_type}</td>
          <td>${fmt(row.value)} ${row.unit}</td>
          <td>${row.qos}</td>
          <td>${fmt(row.latency_ms)}</td>
          <td class="${row.alert ? 'alert' : 'ok'}">${row.alert ? 'Alert' : 'Normal'}</td>
        </tr>
      `).join('');
    }

    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
