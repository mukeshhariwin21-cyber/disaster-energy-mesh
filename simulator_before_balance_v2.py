
"""
simulator.py
------------
V2.2 simulation engine for the Disaster Energy Mesh.

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
- Simulation history
"""

from dataclasses import dataclass

from simulation.node import Node
from simulation.energy import (
    solar_daylight_factor,
    get_dynamic_loads,
)
from control import fault_detection, load_management


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

        self.manual_solar_w = None
        self.manual_load_w = None
        self.manual_battery_w = None

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

    # ------------------------------------------------------------------
    # Manual energy configuration
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Disable manual energy mode
    # ------------------------------------------------------------------

    def clear_manual_energy(self):

        self.manual_solar_w = None
        self.manual_load_w = None
        self.manual_battery_w = None

        self._log(
            f"[{self._time_label()}] "
            "Manual energy input disabled. "
            "Returning to automatic simulation."
        )

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------

    def _time_label(self) -> str:

        total_minutes = int(
            round(self.sim_time_hours * 60)
        )

        total_minutes %= 24 * 60

        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours:02d}:{minutes:02d}"

    # ------------------------------------------------------------------
    # Event logging
    # ------------------------------------------------------------------

    def _log(self, message: str):

        self.event_log.append(message)
        self.event_log = self.event_log[-200:]

    # ------------------------------------------------------------------
    # Fault controls
    # ------------------------------------------------------------------

    def fail_node(self, node_id: str):

        for node in self.nodes:

            if (
                node.node_id == node_id
                and node.status != "FAILED"
            ):

                node.fail()

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} failure manually triggered"
                )

    def recover_node(self, node_id: str):

        for node in self.nodes:

            if (
                node.node_id == node_id
                and node.status == "FAILED"
            ):

                node.recover()

                self._log(
                    f"[{self._time_label()}] "
                    f"{node_id} recovery manually triggered"
                )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self):
        self.__init__()

    # ------------------------------------------------------------------
    # Main simulation tick
    # ------------------------------------------------------------------

    def step(self) -> TickResult:

        time_label = self._time_label()
        hour_of_day = self.sim_time_hours % 24

        daylight_factor = solar_daylight_factor(
            hour_of_day
        )

        online_nodes = [
            node
            for node in self.nodes
            if node.online
        ]

        # --------------------------------------------------------------
        # Solar generation
        # --------------------------------------------------------------

        for node in self.nodes:

            node.compute_solar_generation(
                daylight_factor
            )

        if self.manual_solar_w is not None:

            requested_solar = self.manual_solar_w

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
                        requested_solar * share
                    )

            for node in self.nodes:

                if not node.online:
                    node.solar_generation_w = 0.0

        total_generation = sum(
            node.solar_generation_w
            for node in online_nodes
        )

        # --------------------------------------------------------------
        # Battery available power
        # --------------------------------------------------------------

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

        total_available_power = (
            total_generation
            + total_battery_available
        )

        # --------------------------------------------------------------
        # Load demand
        # --------------------------------------------------------------

        current_loads = get_dynamic_loads(
            hour_of_day
        )

        automatic_load_demand = sum(
            load.base_demand_w
            for load in current_loads
        )

        if self.manual_load_w is not None:
            total_load_demand = self.manual_load_w
        else:
            total_load_demand = automatic_load_demand

        # --------------------------------------------------------------
        # Priority-based allocation
        # --------------------------------------------------------------

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

        if self.manual_load_w is not None:

            total_allocated = min(
                total_allocated,
                self.manual_load_w,
            )

        # --------------------------------------------------------------
        # Physical power balance
        # --------------------------------------------------------------

        physical_net = (
            total_generation
            - total_allocated
        )

        # --------------------------------------------------------------
        # Battery management
        # --------------------------------------------------------------

        if physical_net >= 0:

            total_headroom = sum(
                node.battery.max_charge_power_w()
                for node in online_nodes
            )

            for node in online_nodes:

                if total_headroom > 0:

                    share = (
                        node.battery.max_charge_power_w()
                        / total_headroom
                    )

                else:

                    share = 0.0

                requested_power = (
                    physical_net * share
                )

                node.battery_power_w = (
                    node.battery.apply_power(
                        requested_power,
                        self.dt_hours,
                    )
                )

        else:

            deficit = abs(physical_net)

            total_reserve_available = sum(
                node.battery.max_discharge_power_w()
                for node in online_nodes
            )

            if self.manual_battery_w is not None:

                total_reserve_available = min(
                    total_reserve_available,
                    self.manual_battery_w,
                )

            for node in online_nodes:

                if total_reserve_available > 0:

                    available_node_power = (
                        node.battery.max_discharge_power_w()
                    )

                    share = (
                        available_node_power
                        / total_reserve_available
                    )

                    share = min(
                        share,
                        1.0,
                    )

                else:

                    share = 0.0

                requested_power = (
                    -deficit * share
                )

                node.battery_power_w = (
                    node.battery.apply_power(
                        requested_power,
                        self.dt_hours,
                    )
                )

        # Failed nodes
        for node in self.nodes:

            if not node.online:

                node.battery_power_w = 0.0
                node.solar_generation_w = 0.0

        # --------------------------------------------------------------
        # Update node state
        # --------------------------------------------------------------

        for node in self.nodes:

            node.update_electrical_readings()

            node.update_temperature(
                hour_of_day
            )

            node.update_health()

        # --------------------------------------------------------------
        # Fault detection
        # --------------------------------------------------------------

        events = fault_detection.detect_and_isolate(
            self.nodes,
            self._previous_status,
            time_label,
        )

        events += load_events

        for event in events:
            self._log(event)

        self._previous_status = {
            node.node_id: node.status
            for node in self.nodes
        }

        # --------------------------------------------------------------
        # Network state
        # --------------------------------------------------------------

        network_status = (
            load_management.classify_network_status(
                load_status
            )
        )

        # --------------------------------------------------------------
        # Result
        # --------------------------------------------------------------

        result = TickResult(

            time_label=time_label,

            hour_of_day=hour_of_day,

            total_generation_w=round(
                total_generation,
                2,
            ),

            total_battery_available_w=round(
                total_battery_available,
                2,
            ),

            total_available_power_w=round(
                total_available_power,
                2,
            ),

            total_load_demand_w=round(
                total_load_demand,
                2,
            ),

            total_allocated_w=round(
                total_allocated,
                2,
            ),

            surplus_deficit_w=round(
                physical_net,
                2,
            ),

            load_status=load_status,

            network_status=network_status,

            nodes=[
                node.snapshot()
                for node in self.nodes
            ],

            events=events,
        )

        self.history.append(result)
        self.history = self.history[-500:]

        self.sim_time_hours += self.dt_hours

        if self.sim_time_hours >= 48:
            self.sim_time_hours -= 24

        return result

