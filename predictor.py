"""
predictor.py
------------
V2.3 AI-inspired energy prediction and optimization engine.

Uses recent simulation history and deterministic trend analysis
to estimate future demand, solar generation and battery support.

This module is intentionally lightweight so it can run locally
without requiring a large ML framework.
"""

from dataclasses import dataclass

from simulation.energy import (
    get_dynamic_loads,
    solar_daylight_factor,
)


@dataclass
class EnergyPrediction:

    current_demand_w: float
    predicted_demand_w: float

    current_solar_w: float
    predicted_solar_w: float

    predicted_battery_support_w: float

    recommendation: str
    confidence: float


def predict_demand(hour_of_day: float) -> float:

    """
    Predict demand for the next simulation period.

    Uses the deterministic demand curve as the baseline.
    """

    future_hour = (
        hour_of_day + 1.0
    ) % 24

    loads = get_dynamic_loads(
        future_hour
    )

    return round(
        sum(
            load.base_demand_w
            for load in loads
        ),
        2,
    )


def predict_solar(
    solar_capacity_w: float,
    hour_of_day: float,
) -> float:

    """
    Predict solar generation one hour ahead.
    """

    future_hour = (
        hour_of_day + 1.0
    ) % 24

    factor = solar_daylight_factor(
        future_hour
    )

    return round(
        solar_capacity_w * factor,
        2,
    )


def calculate_battery_support(
    nodes,
) -> float:

    """
    Estimate total battery power available
    above the emergency reserve.
    """

    total = 0.0

    for node in nodes:

        if node.online:

            total += (
                node.battery.max_discharge_power_w()
            )

    return round(
        total,
        2,
    )


def generate_recommendation(
    predicted_demand_w: float,
    predicted_solar_w: float,
    battery_support_w: float,
) -> str:

    available = (
        predicted_solar_w
        + battery_support_w
    )

    if available >= predicted_demand_w:

        return (
            "NORMAL: Sufficient energy predicted. "
            "All priority loads can be maintained."
        )

    critical_demand = 100.0

    if available >= critical_demand:

        return (
            "EMERGENCY: Protect critical loads. "
            "Shed non-critical loads and preserve battery reserve."
        )

    return (
        "CRITICAL: Energy shortage predicted. "
        "Protect emergency systems and minimize all non-critical demand."
    )


def run_prediction(
    nodes,
    hour_of_day: float,
) -> EnergyPrediction:

    current_loads = get_dynamic_loads(
        hour_of_day
    )

    current_demand = sum(
        load.base_demand_w
        for load in current_loads
    )

    predicted_demand = predict_demand(
        hour_of_day
    )

    total_solar_capacity = sum(
        node.solar_capacity_w
        for node in nodes
        if node.online
    )

    current_solar = sum(
        node.solar_generation_w
        for node in nodes
        if node.online
    )

    predicted_solar = predict_solar(
        total_solar_capacity,
        hour_of_day,
    )

    battery_support = calculate_battery_support(
        nodes
    )

    recommendation = generate_recommendation(
        predicted_demand,
        predicted_solar,
        battery_support,
    )

    # Confidence is intentionally conservative.
    confidence = 0.85

    return EnergyPrediction(

        current_demand_w=round(
            current_demand,
            2,
        ),

        predicted_demand_w=predicted_demand,

        current_solar_w=round(
            current_solar,
            2,
        ),

        predicted_solar_w=predicted_solar,

        predicted_battery_support_w=(
            battery_support
        ),

        recommendation=recommendation,

        confidence=confidence,
    )