from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time

import aiocoap

from .config import COAP_HOST, COAP_PORT, SENSOR_TYPES


async def send_one(protocol: aiocoap.Context, uri: str, index: int) -> float:
    sensor_type = random.choice(list(SENSOR_TYPES))
    meta = SENSOR_TYPES[sensor_type]
    low, high = meta["normal"]
    payload = {
        "device_id": f"coap_device_{index % 4 + 1:02d}",
        "sensor_type": sensor_type,
        "value": round(random.uniform(float(low), float(high)), 2),
        "unit": meta["unit"],
        "sent_at": time.time(),
    }
    request = aiocoap.Message(
        code=aiocoap.POST,
        uri=uri,
        payload=json.dumps(payload).encode("utf-8"),
    )
    start = time.perf_counter()
    response = await protocol.request(request).response
    rtt_ms = (time.perf_counter() - start) * 1000
    print(f"{index:03d} {response.code} rtt={rtt_ms:.3f}ms payload={response.payload.decode('utf-8')}")
    return rtt_ms


async def run_client(host: str, port: int, count: int, interval: float) -> None:
    uri = f"coap://{host}:{port}/sensor"
    protocol = await aiocoap.Context.create_client_context()
    await asyncio.sleep(0.1)
    rtts: list[float] = []
    for index in range(1, count + 1):
        rtts.append(await send_one(protocol, uri, index))
        await asyncio.sleep(interval)

    print("\nCoAP RTT summary")
    print(f"count: {len(rtts)}")
    print(f"avg:   {statistics.mean(rtts):.3f} ms")
    print(f"min:   {min(rtts):.3f} ms")
    print(f"max:   {max(rtts):.3f} ms")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CoAP sensor data client")
    parser.add_argument("--host", default=COAP_HOST)
    parser.add_argument("--port", type=int, default=COAP_PORT)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.interval < 0:
        parser.error("--interval must be non-negative")
    return args


def main() -> None:
    args = parse_args()
    asyncio.run(run_client(args.host, args.port, args.count, args.interval))


if __name__ == "__main__":
    main()
