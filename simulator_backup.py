"""
simulator.py
------------
V2.3 simulation engine for the Disaster Energy Mesh.

Models:
- 3 distributed energy nodes
- Time-varying solar generation
- Manual solar override
- Manual load override
- Manual battery support
- Battery SOC
- Power balance
- Node health
- Fault/recovery events
- Automatic power redistribution
- Simulation history
"""

from dataclasses import dataclass

from simulation.node import Node
from simulation.energy import (
    solar_daylight_factor,
    get_dynamic_loads,
)
from control import fault_detection, load_management


# ============================================================
# TICK RESULT
# ============================================================

@dataclass
class TickResult:

    time_label: str
    hour_of_day: float

    total_generation_w: float
    total_battery_available_w: float
    total_available_power_w: float

    total_load_demand_w: float
    total_allocated_w: float

    surplus_deficit_w: float

    load_status: dict
    network_status: str

    nodes: list
    events: list


# ============================================================
# SIMULATOR
# ============================================================

class Simulator:

    def __init__(self):

        self.nodes = [

            Node(
                node_id="Node 1",
                solar_capacity_w=200,
                battery_capacity_wh=500,
                initial_soc=85,
            ),

            Node(
                node_id="Node 2",
                solar_capacity_w=150,
                battery_capacity_wh=400,
                initial_soc=70,
            ),

            Node(
                node_id="Node 3",
                solar_capacity_w=100,
                battery_capacity_wh=300,
                initial_soc=60,
            ),
        ]

        self.sim_time_hours = 6.0
        self.dt_hours = 0.25
        self.running = False

        # Manual controls
        self.manual_solar_w = None
        self.manual_load_w = None
        self.manual_battery_w = None

        # Logs
        self.event_log = []

        self._previous_status = {
            node.node_id: node.status
            for node in self.nodes
        }

        self.history = []

        self._log(
            f"[{self._time_label()}] "
            "Simulation initialized. 3 nodes online."
        )

    # ========================================================
    # MANUAL ENERGY CONFIGURATION
    # ========================================================

    def set_manual_energy(
        self,
        solar_w=None,
        load_w=None,
        battery_w=None,
    ):

        if solar_w is not None:

            self.manual_solar_w = max(
                0.0,
                float(solar_w),
            )

        if load_w is not None:

            self.manual_load_w = max(
                0.0,
                float(load_w),
            )

        if battery_w is not None:

            self.manual_battery_w = max(
                0.0,
                float(battery_w),
            )

        self._log(
            f"[{self._time_label()}] "
            "Manual energy configuration updated."
        )

    # ========================================================
    # CLEAR MANUAL ENERGY
    # ========================================================

    def clear_manual_energy(self):

        self.manual_solar_w = None
        self.manual_load_w = None
        self.manual_battery_w = None

        self._log(
            f"[{self._time_label()}] "
            "Manual energy input disabled. "
            "Returning to automatic simulation."
        )

    # ========================================================
    # TIME
    # ========================================================

    def _time_label(self) -> str:

        total_minutes = int(
            round(
                self.sim_time_hours * 60
            )
        )

        total_minutes %= 24 * 60

        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours:02d}:{minutes:02d}"

    # ========================================================
    # EVENT LOG
    # ========================================================

    def _log(self, message: str):

        self.event_log.append(message)

        self.event_log = (
            self.event_log[-200:]
        )

    # ========================================================
    # NODE FAILURE
    # ========================================================

    def fail_node(
        self,
        node_id: str,
    ):

        for node in self.nodes:

            if (
                node.node_id == node_id
                and node.status != "FAILED"
            ):

                node.fail()

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} failure manually triggered."
                )

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} isolated from power network."
                )

                self._log(
                    f"[{self._time_label()}] "
                    "Healthy nodes will automatically "
                    "rebalance available power."
                )

    # ========================================================
    # NODE RECOVERY
    # ========================================================

    def recover_node(
        self,
        node_id: str,
    ):

        for node in self.nodes:

            if (
                node.node_id == node_id
                and node.status == "FAILED"
            ):

                node.recover()

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} recovery manually triggered."
                )

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} reconnected to network."
                )

                self._log(
                    f"[{self._time_label()}] "
                    "Power distribution automatically rebalanced."
                )

    # ========================================================
    # RESET
    # ========================================================

    def reset(self):

        self.__init__()

    # ========================================================
    # MAIN SIMULATION STEP
    # ========================================================

    def step(self) -> TickResult:

        time_label = self._time_label()

        hour_of_day = (
            self.sim_time_hours % 24
        )

        daylight_factor = (
            solar_daylight_factor(
                hour_of_day
            )
        )

        # ----------------------------------------------------
        # ONLINE NODES
        # ----------------------------------------------------

        online_nodes = [
            node
            for node in self.nodes
            if node.online
        ]

        # Reset battery flow every tick.
        # Prevents old battery values from carrying forward.
        for node in self.nodes:

            node.battery_power_w = 0.0

        # ----------------------------------------------------
        # SOLAR GENERATION
        # ----------------------------------------------------

        for node in self.nodes:

            node.compute_solar_generation(
                daylight_factor
            )

        # ----------------------------------------------------
        # MANUAL SOLAR OVERRIDE
        # ----------------------------------------------------

        if self.manual_solar_w is not None:

            requested_solar = (
                self.manual_solar_w
            )

            total_capacity = sum(
                node.solar_capacity_w
                for node in online_nodes
            )

            if total_capacity > 0:

                for node in online_nodes:

                    share = (
                        node.solar_capacity_w
                        / total_capacity
                    )

                    node.solar_generation_w = (
                        requested_solar
                        * share
                    )

            for node in self.nodes:

                if not node.online:

                    node.solar_generation_w = 0.0

        # ----------------------------------------------------
        # TOTAL SOLAR
        # ----------------------------------------------------

        total_generation = sum(
            node.solar_generation_w
            for node in online_nodes
        )

        # ----------------------------------------------------
        # BATTERY AVAILABLE POWER
        # ----------------------------------------------------

        automatic_battery_available = sum(
            node.battery.max_discharge_power_w()
            for node in online_nodes
        )

        if self.manual_battery_w is not None:

            total_battery_available = min(
                self.manual_battery_w,
                automatic_battery_available,
            )

        else:

            total_battery_available = (
                automatic_battery_available
            )

        # ----------------------------------------------------
        # TOTAL AVAILABLE POWER
        # ----------------------------------------------------

        total_available_power = (
            total_generation
            + total_battery_available
        )

        # ----------------------------------------------------
        # LOAD DEMAND
        # ----------------------------------------------------

        current_loads = get_dynamic_loads(
            hour_of_day
        )

        automatic_load_demand = sum(
            load.base_demand_w
            for load in current_loads
        )

        if self.manual_load_w is not None:

            total_load_demand = (
                self.manual_load_w
            )

        else:

            total_load_demand = (
                automatic_load_demand
            )

        # ----------------------------------------------------
        # PRIORITY LOAD ALLOCATION
        # ----------------------------------------------------

        (
            load_status,
            remaining_power,
            total_allocated,
            load_events,
        ) = load_management.allocate_loads(
            total_available_power,
            time_label,
            hour_of_day,
        )

        # Manual load acts as a demonstration cap.
        if self.manual_load_w is not None:

            total_allocated = min(
                total_allocated,
                self.manual_load_w,
            )

        # ----------------------------------------------------
        # PHYSICAL POWER BALANCE
        # ----------------------------------------------------
        #
        # Positive:
        # Solar > load
        # Battery can charge.
        #
        # Negative:
        # Solar < load
        # Battery must discharge.
        #
        # IMPORTANT:
        # Do NOT add total_battery_available here.
        # Battery is physically dispatched below.
        # ----------------------------------------------------

        physical_net = (
            total_generation
            - total_allocated
        )

        # ----------------------------------------------------
        # BATTERY MANAGEMENT
        # ----------------------------------------------------

        if physical_net >= 0:

            # ==================================================
            # SURPLUS -> CHARGE BATTERIES
            # ==================================================

            surplus = physical_net

            total_headroom = sum(
                node.battery.max_charge_power_w()
                for node in online_nodes
            )

            if total_headroom > 0:

                charge_power = min(
                    surplus,
                    total_headroom,
                )

                for node in online_nodes:

                    node_headroom = (
                        node.battery.max_charge_power_w()
                    )

                    if node_headroom > 0:

                        share = (
                            node_headroom
                            / total_headroom
                        )

                    else:

                        share = 0.0

                    requested_power = (
                        charge_power
                        * share
                    )

                    node.battery