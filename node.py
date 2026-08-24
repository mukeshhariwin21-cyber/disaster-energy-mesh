"""
node.py
-------
Defines the Node class: a single distributed energy node in the
Disaster Energy Mesh. Each node owns a solar array, a battery, and a
set of live electrical readings (voltage, current, power, temperature,
health, communication status).

A Node does NOT decide how loads are allocated across the mesh -- that
is the job of control/load_management.py. Node is purely a physical /
electrical model of one point in the network.
"""

from dataclasses import dataclass, field
from simulation.battery import Battery

SYSTEM_VOLTAGE_NOMINAL = 12.0   # 12V DC system
AMBIENT_TEMP_BASE = 27.0        # deg C, baseline ambient temperature
BATTERY_RESERVE_SOC = 10.0      # % SOC treated as "empty" for load supply purposes


@dataclass
class Node:
    node_id: str
    solar_capacity_w: float
    battery_capacity_wh: float
    initial_soc: float

    # Live state (populated by simulator each tick)
    status: str = "HEALTHY"          # HEALTHY | FAILED
    online: bool = True
    comm_status: str = "CONNECTED"   # CONNECTED | LOST
    soc: float = field(init=False)
    solar_generation_w: float = 0.0
    battery_power_w: float = 0.0     # +charging, -discharging (from battery's perspective)
    net_power_w: float = 0.0         # generation - battery flow, node's contribution to the bus
    voltage_v: float = SYSTEM_VOLTAGE_NOMINAL
    current_a: float = 0.0
    temperature_c: float = AMBIENT_TEMP_BASE
    health: str = "OPTIMAL"

    def __post_init__(self):
        self.soc = self.initial_soc
        self.battery = Battery(
            capacity_wh=self.battery_capacity_wh,
            soc=self.initial_soc,
            reserve_soc=BATTERY_RESERVE_SOC,
        )

    # ------------------------------------------------------------------
    # Fault control
    # ------------------------------------------------------------------
    def fail(self):
        """Simulate a hard node failure: generation and battery become unavailable."""
        self.status = "FAILED"
        self.online = False
        self.comm_status = "LOST"
        self.solar_generation_w = 0.0
        self.battery_power_w = 0.0
        self.net_power_w = 0.0
        self.current_a = 0.0
        self.health = "FAILED"

    def recover(self):
        """Bring the node back online. Battery SOC is retained from before failure."""
        self.status = "HEALTHY"
        self.online = True
        self.comm_status = "CONNECTED"

    # ------------------------------------------------------------------
    # Electrical model
    # ------------------------------------------------------------------
    def compute_solar_generation(self, daylight_factor: float):
        """
        daylight_factor in [0, 1] describes how much of the node's rated
        solar capacity is currently achievable, based on simulated time
        of day (see simulation/energy.py::solar_daylight_factor).
        """
        if not self.online:
            self.solar_generation_w = 0.0
            return
        self.solar_generation_w = self.solar_capacity_w * daylight_factor

    def update_electrical_readings(self):
        """
        Derive voltage / current / power from current battery SOC and
        net power flow. Power = Voltage x Current is preserved exactly
        by computing current from power and voltage.
        """
        if not self.online:
            self.voltage_v = 0.0
            self.current_a = 0.0
            self.net_power_w = 0.0
            self.soc = self.battery.soc
            return

        # Bus voltage sags/rises gently with state of charge (11.5V - 13.2V band)
        self.voltage_v = 11.5 + (self.battery.soc / 100.0) * 1.7

        # Net power this node is putting on the shared bus:
        # solar generation, minus whatever is being routed into the battery
        # (battery_power_w > 0 means charging => consumes generation)
        self.net_power_w = self.solar_generation_w - self.battery_power_w
        self.current_a = self.net_power_w / self.voltage_v if self.voltage_v > 0 else 0.0
        self.soc = self.battery.soc

    def update_temperature(self, hour_of_day: float):
        """
        Simple deterministic thermal model: temperature rises with solar
        loading and with midday ambient heat, cools at night.
        """
        if not self.online:
            self.temperature_c = AMBIENT_TEMP_BASE
            return

        loading_ratio = (
            self.solar_generation_w / self.solar_capacity_w
            if self.solar_capacity_w > 0 else 0.0
        )
        # Ambient swing: coolest at 04:00, warmest at 15:00
        import math
        ambient_swing = 4.0 * math.sin(math.pi * (hour_of_day - 4) / 15) if 4 <= hour_of_day <= 19 else -2.0
        self.temperature_c = AMBIENT_TEMP_BASE + ambient_swing + loading_ratio * 6.0

    def update_health(self):
        if not self.online:
            self.health = "FAILED"
        elif self.battery.soc < 15:
            self.health = "LOW BATTERY"
        elif self.temperature_c > 45:
            self.health = "OVERHEAT WARNING"
        elif self.battery.soc < 30:
            self.health = "DEGRADED"
        else:
            self.health = "OPTIMAL"

    def snapshot(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "online": self.online,
            "comm_status": self.comm_status,
            "soc": round(self.soc, 2),
            "solar_generation_w": round(self.solar_generation_w, 2),
            "battery_power_w": round(self.battery_power_w, 2),
            "net_power_w": round(self.net_power_w, 2),
            "voltage_v": round(self.voltage_v, 2),
            "current_a": round(self.current_a, 2),
            "temperature_c": round(self.temperature_c, 2),
            "health": self.health,
        }
