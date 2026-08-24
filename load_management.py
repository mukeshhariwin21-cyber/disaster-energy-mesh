"""
load_management.py
------------------
Priority-based power distribution for the Disaster Energy Mesh.
"""

from simulation.energy import get_dynamic_loads


def allocate_loads(
    available_power_w: float,
    time_label: str,
    hour_of_day: float = 12.0,
    load_override_w=None,
):
    """
    Allocate available power according to priority.

    load_override_w:
        Optional manual total load limit used by the dashboard.
    """

    available_power_w = max(
        0.0,
        float(available_power_w),
    )

    loads = get_dynamic_loads(hour_of_day)

    # ------------------------------------------------------------
    # Manual load override
    # ------------------------------------------------------------

    if load_override_w is not None:

        override = max(
            0.0,
            float(load_override_w),
        )

        automatic_total = sum(
            max(0.0, float(load.base_demand_w))
            for load in loads
        )

        if automatic_total > 0:

            scale = min(
                1.0,
                override / automatic_total,
            )

            loads = [
                type(load)(
                    priority=load.priority,
                    name=load.name,
                    base_demand_w=round(
                        load.base_demand_w * scale,
                        2,
                    ),
                    examples=load.examples,
                )
                for load in loads
            ]

    # ------------------------------------------------------------
    # Priority order
    # ------------------------------------------------------------

    loads = sorted(
        loads,
        key=lambda load: load.priority,
    )

    remaining = available_power_w
    total_allocated = 0.0

    load_status = {}
    events = []

    # ------------------------------------------------------------
    # Allocate power
    # ------------------------------------------------------------

    for load in loads:

        demand = max(
            0.0,
            float(load.base_demand_w),
        )

        priority = load.priority
        name = load.name

        if remaining >= demand:

            load_status[name] = True

            remaining -= demand
            total_allocated += demand

            events.append(
                f"[{time_label}] "
                f"P{priority} {name} LOAD ON "
                f"({demand:.1f} W)"
            )

        else:

            load_status[name] = False

            if priority == 1:

                events.append(
                    f"[{time_label}] "
                    f"CRITICAL POWER SHORTAGE: "
                    f"{name} requires {demand:.1f} W, "
                    f"available {remaining:.1f} W"
                )

                events.append(
                    f"[{time_label}] "
                    f"CRITICAL LOAD {name} OFF"
                )

            elif priority == 2:

                events.append(
                    f"[{time_label}] "
                    f"ESSENTIAL LOAD {name} SHED"
                )

            else:

                events.append(
                    f"[{time_label}] "
                    f"NON-CRITICAL LOAD {name} SHED"
                )

    # ------------------------------------------------------------
    # Status
    # ------------------------------------------------------------

    critical_on = load_status.get(
        "Critical",
        False,
    )

    essential_on = load_status.get(
        "Essential",
        False,
    )

    noncritical_on = load_status.get(
        "Non-critical",
        False,
    )

    # ------------------------------------------------------------
    # Self-healing messages
    # ------------------------------------------------------------

    if not critical_on:

        events.append(
            f"[{time_label}] "
            "SELF-HEALING WARNING: "
            "Critical load cannot be protected"
        )

    elif not essential_on or not noncritical_on:

        events.append(
            f"[{time_label}] "
            "POWER REDISTRIBUTION ACTIVE: "
            "Lower-priority loads shed"
        )

    else:

        events.append(
            f"[{time_label}] "
            "POWER DISTRIBUTION NORMAL"
        )

    # ------------------------------------------------------------
    # Network status
    # ------------------------------------------------------------

    network_status = classify_network_status(
        load_status
    )

    events.append(
        f"[{time_label}] "
        f"Network operating in "
        f"{network_status} mode"
    )

    # ------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------

    return (
        load_status,
        remaining,
        total_allocated,
        events,
    )


def classify_network_status(
    load_status: dict,
) -> str:

    critical = load_status.get(
        "Critical",
        False,
    )

    essential = load_status.get(
        "Essential",
        False,
    )

    noncritical = load_status.get(
        "Non-critical",
        False,
    )

    if not critical:
        return "CRITICAL"

    if not essential or not noncritical:
        return "EMERGENCY"

    return "NORMAL"