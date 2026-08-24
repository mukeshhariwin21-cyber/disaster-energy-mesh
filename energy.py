"""
energy.py
---------
Shared energy calculations used by the simulator:
 - the solar daylight curve (time-of-day -> fraction of rated capacity)
 - the fixed priority load definitions
 - the core "Power = Voltage x Current" helper

Everything here is a deterministic function of simulated time / node
state -- no random numbers are used for the main simulation.
"""

import math
from dataclasses import dataclass

SUNRISE_HOUR = 6.0
SUNSET_HOUR = 18.0


def solar_daylight_factor(hour_of_day: float) -> float:
    """
    Returns a value in [0, 1] describing how much of a node's rated solar
    capacity is achievable at the given simulated hour (0-24).

    Shape: 0 before sunrise and after sunset, rising through the morning,
    peaking at solar noon, falling through the evening -- a half-sine
    curve across the daylight window.
    """
    h = hour_of_day % 24
    if h <= SUNRISE_HOUR or h >= SUNSET_HOUR:
        return 0.0
    daylight_span = SUNSET_HOUR - SUNRISE_HOUR
    return max(0.0, math.sin(math.pi * (h - SUNRISE_HOUR) / daylight_span))


def power_from_v_i(voltage_v: float, current_a: float) -> float:
    """P = V x I"""
    return voltage_v * current_a


@dataclass(frozen=True)
class PriorityLoad:
    priority: int
    name: str
    demand_w: float
    examples: str


PRIORITY_LOADS = [
    PriorityLoad(1, "Critical", 100.0, "Emergency communication, medical support"),
    PriorityLoad(2, "Essential", 100.0, "Water system, emergency lighting"),
    PriorityLoad(3, "Non-critical", 150.0, "General lighting, auxiliary loads"),
]

TOTAL_POSSIBLE_LOAD_W = sum(l.demand_w for l in PRIORITY_LOADS)
