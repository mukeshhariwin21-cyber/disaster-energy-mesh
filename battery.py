"""
battery.py
----------
Simple energy-conserving battery model. State of charge (SOC) moves up
when the battery is charged and down when it supplies power, based on
actual Wh transferred over the simulated time step -- never randomly.

Assumption (documented in README): a node's battery can be charged or
discharged at a maximum rate equal to its own capacity per hour (i.e. a
1C-ish rate), which is a reasonable simplification for a software-only
hackathon prototype.
"""

from dataclasses import dataclass


@dataclass
class Battery:
    capacity_wh: float
    soc: float                 # percent, 0-100
    reserve_soc: float = 10.0  # percent kept in reserve, not offered to loads

    @property
    def stored_wh(self) -> float:
        return self.capacity_wh * (self.soc / 100.0)

    def max_discharge_power_w(self) -> float:
        """
        Maximum power this battery can safely supply right now, treating
        the reserve SOC as untouchable. Assumes a 1-hour discharge horizon.
        """
        usable_pct = max(0.0, self.soc - self.reserve_soc)
        return self.capacity_wh * (usable_pct / 100.0)

    def max_charge_power_w(self) -> float:
        """Maximum power this battery can currently absorb (headroom to 100% SOC)."""
        headroom_pct = max(0.0, 100.0 - self.soc)
        return self.capacity_wh * (headroom_pct / 100.0)

    def apply_power(self, power_w: float, dt_hours: float) -> float:
        """
        Apply a power flow to the battery for dt_hours.
        power_w > 0  => charging (SOC increases)
        power_w < 0  => discharging (SOC decreases)
        Returns the power actually applied (clamped to physical limits).
        """
        if power_w >= 0:
            applied = min(power_w, self.max_charge_power_w() / dt_hours if dt_hours > 0 else power_w)
        else:
            max_out = self.max_discharge_power_w() / dt_hours if dt_hours > 0 else abs(power_w)
            applied = -min(abs(power_w), max_out)

        delta_wh = applied * dt_hours
        delta_soc = (delta_wh / self.capacity_wh) * 100.0 if self.capacity_wh > 0 else 0.0
        self.soc = min(100.0, max(0.0, self.soc + delta_soc))
        return applied
