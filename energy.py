
"""
energy.py
---------
Energy and load models for the Disaster Energy Mesh.

Provides:
- Solar daylight calculation
- Voltage/current power calculation
- Dynamic priority-based loads
- Total load demand calculation
"""

import math
from dataclasses import dataclass


# ==============================================================
# SOLAR CONFIGURATION
# ==============================================================

SUNRISE_HOUR = 6.0
SUNSET_HOUR = 18.0


def solar_daylight_factor(hour_of_day: float) -> float:
    """
    Return solar availability as a value between 0.0 and 1.0.

    06:00  -> 0.0
    12:00  -> 1.0
    18:00  -> 0.0
    """

    hour = float(hour_of_day) % 24.0

    if (
        hour <= SUNRISE_HOUR
        or hour >= SUNSET_HOUR
    ):
        return 0.0

    daylight_duration = (
        SUNSET_HOUR - SUNRISE_HOUR
    )

    factor = math.sin(
        math.pi
        * (hour - SUNRISE_HOUR)
        / daylight_duration
    )

    return max(
        0.0,
        min(1.0, factor),
    )


# ==============================================================
# ELECTRICAL HELPERS
# ==============================================================

def power_from_v_i(
    voltage_v: float,
    current_a: float,
) -> float:
    """Calculate electrical power using P = V × I."""

    return float(voltage_v) * float(current_a)


# ==============================================================
# LOAD MODEL
# ==============================================================

@dataclass(frozen=True)
class PriorityLoad:
    """Definition of one priority class of electrical load."""

    priority: int
    name: str
    base_demand_w: float
    examples: str


PRIORITY_LOADS = [
    PriorityLoad(
        priority=1,
        name="Critical",
        base_demand_w=100.0,
        examples="Emergency communication, medical support",
    ),
    PriorityLoad(
        priority=2,
        name="Essential",
        base_demand_w=100.0,
        examples="Water system, emergency lighting",
    ),
    PriorityLoad(
        priority=3,
        name="Non-critical",
        base_demand_w=150.0,
        examples="General lighting, auxiliary loads",
    ),
]


# ==============================================================
# LOAD DEMAND PROFILE
# ==============================================================

def load_demand_factor(hour_of_day: float) -> float:
    """
    Return the demand multiplier for the simulated time.

    The profile represents a simplified emergency microgrid
    demand pattern.
    """

    hour = float(hour_of_day) % 24.0

    if 0 <= hour < 6:
        return 0.75

    if 6 <= hour < 9:
        return 0.90

    if 9 <= hour < 13:
        return 1.05

    if 13 <= hour < 17:
        return 1.10

    if 17 <= hour < 21:
        return 1.25

    return 0.85


# ==============================================================
# DYNAMIC LOAD GENERATION
# ==============================================================

def get_dynamic_loads(
    hour_of_day: float,
) -> list[PriorityLoad]:
    """
    Generate current load values from the time-dependent demand
    profile.
    """

    factor = load_demand_factor(
        hour_of_day
    )

    return [
        PriorityLoad(
            priority=load.priority,
            name=load.name,
            base_demand_w=round(
                load.base_demand_w * factor,
                2,
            ),
            examples=load.examples,
        )
        for load in PRIORITY_LOADS
    ]


# ==============================================================
# TOTAL DEMAND
# ==============================================================

def total_load_demand(
    hour_of_day: float,
) -> float:
    """Return total dynamic load demand in watts."""

    return round(
        sum(
            load.base_demand_w
            for load in get_dynamic_loads(
                hour_of_day
            )
        ),
        2,
    )


# ==============================================================
# CONSTANTS
# ==============================================================

TOTAL_POSSIBLE_LOAD_W = sum(
    load.base_demand_w
    for load in PRIORITY_LOADS
)
