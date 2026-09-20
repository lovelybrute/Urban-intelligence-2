"""
Urban Intelligence Platform - Simulator Runner

CLI runner that drives fleet GPS movement and periodically injects demonstration
events into the Central Command Platform.
"""
import sys
import os
import time
import asyncio
import httpx
from typing import Optional
from loguru import logger
from simulator.bus_sim import BusSimulator
from simulator.event_generator import DemoEventGenerator


async def run_simulation(
    api_url: str = "http://localhost:8000",
    bus_count: int = 10,
    tick_rate_seconds: float = 2.0,
    event_interval_ticks: int = 5,
    max_ticks: Optional[int] = None
):
    """
    Continuous simulation loop.
    Advances bus GPS telemetry and submits simulated events to backend.
    """
    logger.info(f"🚌 Initializing Urban Fleet Simulator ({bus_count} buses in Hyderabad)...")
    sim = BusSimulator(bus_count=bus_count)
    event_idx = 0
    tick = 0

    async with httpx.AsyncClient(timeout=5.0, headers={"Authorization": f"Bearer {os.environ.get('URBAN_API_TOKEN', '')}"}) as client:
        # Check backend availability
        try:
            res = await client.get(f"{api_url}/")
            logger.info(f"Connected to backend: {res.json().get('platform')}")
        except Exception:
            logger.warning(f"Backend at {api_url} not immediately reachable; simulation will still run locally.")

        while True:
            tick += 1
            telemetries = sim.step(delta_time_seconds=tick_rate_seconds)

            # Update bus GPS on backend
            for telem in telemetries:
                try:
                    # Update bus location endpoint
                    await client.post(
                        f"{api_url}/api/buses/telemetry",
                        json={
                            "bus_id": telem.bus_id,
                            "is_simulated": True,
                            "latitude": telem.latitude,
                            "longitude": telem.longitude,
                            "speed": telem.speed_kmh
                        }
                    )
                except Exception:
                    pass

            # Periodically inject a demonstration event
            if tick % event_interval_ticks == 0:
                scenario = DemoEventGenerator.get_scenario(event_idx)
                event_idx += 1
                logger.info(f"📢 [SIMULATED EVENT] {scenario['name']} by Bus #{scenario['bus_id']}")
                try:
                    res = await client.post(f"{api_url}/api/events/", json=scenario)
                    if res.status_code in [200, 201]:
                        logger.info(f"✅ Event successfully registered in central platform (ID: {res.json().get('event_id')})")
                except Exception as ex:
                    logger.debug(f"Event post skipped (offline mode): {ex}")

            if max_ticks and tick >= max_ticks:
                break

            await asyncio.sleep(tick_rate_seconds)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(run_simulation(api_url=url))
