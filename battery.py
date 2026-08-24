
"""
battery.py
----------
Energy-conserving battery model for the Disaster Energy Mesh.

The battery tracks:
- Capacity in Wh
- State of charge (SOC) in %
- Minimum reserve SOC

Power convention:
    power_w > 0  -> battery charging
    power_w < 0  -> battery discharging

The model is deterministic and conserves energy based on the
simulated time step.
"""

from dataclasses import dataclass


@dataclass
class Battery:
    capacity_wh: float
    soc: float
    reserve_soc: float = 10.0

    def __post_init__(self):
        # ----------------------------------------------------------
        # Validate battery configuration
        # ----------------------------------------------------------

        self.capacity_wh = max(0.0, float(self.capacity_wh))

        self.reserve_soc = min(
            100.0,
            max(0.0, float(self.reserve_soc)),
        )

        self.soc = min(
            100.0,
            max(0.0, float(self.soc)),
        )

    # --------------------------------------------------------------
    # Stored energy
    # --------------------------------------------------------------

    @property
    def stored_wh(self) -> float:
        """Current stored energy in Wh."""

        return self.capacity_wh * (
            self.soc / 100.0
        )

    # --------------------------------------------------------------
    # Available energy
    # --------------------------------------------------------------

    @property
    def usable_wh(self) -> float:
        """
        Energy available above the protected reserve.
        """

        usable_soc = max(
            0.0,
            self.soc - self.reserve_soc,
        )

        return self.capacity_wh * (
            usable_soc / 100.0
        )

    @property
    def headroom_wh(self) -> float:
        """
        Energy capacity remaining before reaching 100% SOC.
        """

        remaining_soc = max(
            0.0,
            100.0 - self.soc,
        )

        return self.capacity_wh * (
            remaining_soc / 100.0
        )

    # --------------------------------------------------------------
    # Maximum power
    # --------------------------------------------------------------

    def max_discharge_power_w(self) -> float:
        """
        Maximum discharge power available for the current state.

        The protected reserve SOC is never offered to loads.

        Assumption:
            1-hour discharge horizon.
        """

        return max(
            0.0,
            self.usable_wh,
        )

    def max_charge_power_w(self) -> float:
        """
        Maximum charging power that can be accepted.

        Assumption:
            1-hour charging horizon.
        """

        return max(
            0.0,
            self.headroom_wh,
        )

    # --------------------------------------------------------------
    # Apply power
    # --------------------------------------------------------------

    def apply_power(
        self,
        power_w: float,
        dt_hours: float,
    ) -> float:
        """
        Apply battery power for the given simulation time step.

        Positive power:
            Charging.

        Negative power:
            Discharging.

        Returns:
            Actual power applied after physical limits.
        """

        # ----------------------------------------------------------
        # Invalid / zero time step
        # ----------------------------------------------------------

        if dt_hours <= 0:
            return 0.0

        if self.capacity_wh <= 0:
            return 0.0

        power_w = float(power_w)

        # ----------------------------------------------------------
        # Charging
        # ----------------------------------------------------------

        if power_w > 0:

            max_charge_power = (
                self.max_charge_power_w()
                / dt_hours
            )

            applied_power = min(
                power_w,
                max_charge_power,
            )

        # ----------------------------------------------------------
        # Discharging
        # ----------------------------------------------------------

        elif power_w < 0:

            max_discharge_power = (
                self.max_discharge_power_w()
                / dt_hours
            )

            applied_power = -min(
                abs(power_w),
                max_discharge_power,
            )

        # ----------------------------------------------------------
        # No power flow
        # ----------------------------------------------------------

        else:

            applied_power = 0.0

        # ----------------------------------------------------------
        # Convert power to energy
        # ----------------------------------------------------------

        transferred_wh = (
            applied_power * dt_hours
        )

        delta_soc = (
            transferred_wh
            / self.capacity_wh
            * 100.0
        )

        # ----------------------------------------------------------
        # Update SOC safely
        # ----------------------------------------------------------

        self.soc = min(
            100.0,
            max(
                self.reserve_soc if applied_power < 0 else 0.0,
                self.soc + delta_soc,
            ),
        )

        return applied_power

