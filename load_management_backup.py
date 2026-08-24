"""
load_management.py
------------------
Priority-based power distribution for the Disaster Energy Mesh.

Priority:
    P1 = Critical
    P2 = Essential
    P3 = Non-critical

The controller always attempts:
    Critical -> Essential -> Non-critical
"""


from simulation.energy import get_dynamic_loads


def allocate_loads(
    available_power_w: float,
    time_label: str,
    hour_of_day: float = 12.0,
):
    """
    Allocate available power according to priority.

    Returns:
        load_status
        remaining_power_w
        total_allocated_w
        events
    """

    available_power_w = max(
        0.0,
        float(available_power_w),
    )

    loads = get_dynamic_loads(
        hour_of_day
    )

    # Highest priority first.
    loads = sorted(
        loads,
        key=lambda load: load.priority,
    )

    remaining = available_power_w

    total_allocated = 0.0

    load_status = {}

    events = []

    # ------------------------------------------------------------
    # PRIORITY-BASED POWER DISTRIBUTION
    # ------------------------------------------------------------

    for load in loads:

        demand = max(
            0.0,
            float(load.base_demand_w),
        )

        priority = load.priority

        name = load.name

        # --------------------------------------------------------
        # Enough power for complete load
        # --------------------------------------------------------

        if remaining >= demand:

            load_status[name] = True

            remaining -= demand

            total_allocated += demand

            events.append(
                f"[{time_label}] "
                f"P{priority} {name} LOAD ON "
                f"({demand:.1f} W)"
            )

        # --------------------------------------------------------
        # Not enough power
        # --------------------------------------------------------

        else:

            load_status[name] = False

            # ----------------------------------------------------
            # Critical load
            # ----------------------------------------------------

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

            # ----------------------------------------------------
            # Essential load
            # ----------------------------------------------------

            elif priority == 2:

                events.append(
                    f"[{time_label}] "
                    f"ESSENTIAL LOAD {name} SHED"
                )

            # ----------------------------------------------------
            # Non-critical load
            # ----------------------------------------------------

            else:

                events.append(
                    f"[{time_label}] "
                    f"NON-CRITICAL LOAD {name} SHED"
                )

    # ------------------------------------------------------------
    # SELF-HEALING / REDISTRIBUTION MESSAGE
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

    if not critical_on:

        events.append(
            f"[{time_label}] "
            f"SELF-HEALING WARNING: "
            f"Critical load cannot be protected"
        )

    elif not essential_on or not noncritical_on:

        events.append(
            f"[{time_label}] "
            f"POWER REDISTRIBUTION ACTIVE: "
            f"Lower-priority loads shed"
        )

    else:

        events.append(
            f"[{time_label}] "
            f"POWER DISTRIBUTION NORMAL"
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

    return (
        load_status,
        remaining,
        total_allocated,
        events,
    )


def classify_network_status(
    load_status: dict,
) -> str:
    """
    Determine overall mesh operating condition.
    """

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

    # ------------------------------------------------------------
    # Critical load unavailable
    # ------------------------------------------------------------

    if not critical:

        return "CRITICAL"

    # ------------------------------------------------------------
    # Critical available, lower priority shed
    # ------------------------------------------------------------

    if not essential or not noncritical:

        return "EMERGENCY"

    # ------------------------------------------------------------
    # All priorities available
    # ------------------------------------------------------------

    return "NORMAL"

