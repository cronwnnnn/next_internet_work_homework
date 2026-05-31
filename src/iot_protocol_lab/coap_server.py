from __future__ import annotations

import asyncio
import json
import time

import aiocoap
import aiocoap.resource as resource

from .config import COAP_HOST, COAP_PORT


class SensorResource(resource.Resource):
    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        received_at = time.time()
        try:
            payload = json.loads(request.payload.decode("utf-8"))
            sent_at = float(payload.get("sent_at", received_at))
            latency_ms = max(0.0, (received_at - sent_at) * 1000)
            response = {
                "status": "ok",
                "device_id": payload.get("device_id"),
                "sensor_type": payload.get("sensor_type"),
                "latency_ms": round(latency_ms, 3),
                "received_at": received_at,
            }
            print(f"CoAP received {payload.get('device_id')} {payload.get('sensor_type')} latency={latency_ms:.3f}ms")
            return aiocoap.Message(code=aiocoap.CHANGED, payload=json.dumps(response).encode("utf-8"))
        except Exception as exc:
            response = {"status": "error", "error": str(exc)}
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=json.dumps(response).encode("utf-8"))


async def run_server(host: str = COAP_HOST, port: int = COAP_PORT) -> None:
    root = resource.Site()
    root.add_resource(["sensor"], SensorResource())
    await aiocoap.Context.create_server_context(root, bind=(host, port))
    print(f"CoAP server listening on coap://{host}:{port}/sensor")
    await asyncio.Event().wait()


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()

