from __future__ import annotations

import asyncio

from amqtt.broker import Broker

from .config import MQTT_HOST, MQTT_PORT


BROKER_CONFIG = {
    "listeners": {
        "default": {
            "type": "tcp",
            "bind": f"{MQTT_HOST}:{MQTT_PORT}",
        }
    },
    "sys_interval": 10,
    "topic-check": {"enabled": False},
    # 不使用账号来登录，匿名可访问
    "auth": {"allow-anonymous": True},
}


async def run_broker() -> None:
    broker = Broker(BROKER_CONFIG)
    await broker.start()
    print(f"MQTT broker listening on {MQTT_HOST}:{MQTT_PORT}")
    try:
        # Broker 启动后一直等待
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


def main() -> None:
    asyncio.run(run_broker())


if __name__ == "__main__":
    main()
