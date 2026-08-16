"""Schedules — the editable per-room time curves.

One :class:`Schedule` per load kind (occupancy, device, lighting): a 24 h
curve, a 7-day week curve (day 1 = Saturday, as in the workbook) and a
12-month curve.  ``schedule[hour]`` addresses the 24 h curve, matching the
"occupancy[18] *= 0.8" user idiom; ``schedule.weekly`` / ``schedule.monthly``
address the other axes.  Values are plain lists — editable in place.

The 8760-hour yearly distribution is derived as
``hour[hour_of_day] * week[weekday] * month[month]``, normalized to sum 1.
"""

from __future__ import annotations

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)  # non-leap year


class Schedule:
    """Three editable curves of one load kind.

    Args:
        hourly: 24 values (0-23 h).
        weekly: 7 values, day 1 = Saturday.
        monthly: 12 values.
    """

    def __init__(
        self,
        hourly: list[float] | tuple[float, ...],
        weekly: list[float] | tuple[float, ...],
        monthly: list[float] | tuple[float, ...],
    ) -> None:
        if len(hourly) != 24:
            raise ValueError(f"hourly schedule must have 24 values, got {len(hourly)}")
        if len(weekly) != 7:
            raise ValueError(f"weekly schedule must have 7 values, got {len(weekly)}")
        if len(monthly) != 12:
            raise ValueError(f"monthly schedule must have 12 values, got {len(monthly)}")
        self.hourly = list(hourly)
        self.weekly = list(weekly)
        self.monthly = list(monthly)

    def __getitem__(self, hour: int) -> float:
        """The 24 h curve value of the given hour (0-23)."""
        return self.hourly[hour]

    def __setitem__(self, hour: int, value: float) -> None:
        self.hourly[hour] = value

    def __iter__(self):
        return iter(self.hourly)

    def __len__(self) -> int:
        return 24

    # -- 8760 synthesis -----------------------------------------------------

    def yearly_distribution(self) -> list[float]:
        """The normalized 8760-hour distribution of this schedule.

        ``hour[hour_of_day] * week[weekday] * month[month]``, normalized so
        the 8760 values sum to 1 (a flat 1/1/1 schedule gives 1/8760 per
        hour).
        """
        distribution = [0.0] * 8760
        total = 0.0
        day_of_year = 0
        for month, days in enumerate(_MONTH_DAYS):
            for day in range(days):
                weekday = day_of_year % 7  # day 1 = Saturday of the week axis
                for hour in range(24):
                    value = (
                        self.hourly[hour]
                        * self.weekly[weekday]
                        * self.monthly[month]
                    )
                    distribution[day_of_year * 24 + hour] = value
                    total += value
                day_of_year += 1
        if total > 0.0:
            for index in range(8760):
                distribution[index] /= total
        return distribution

    def __repr__(self) -> str:
        return f"Schedule(hourly={self.hourly!r}, weekly={self.weekly!r}, monthly={self.monthly!r})"


class Schedules:
    """The three editable schedules of a room (occupancy/device/lighting)."""

    def __init__(
        self,
        occupancy_hourly: list[float],
        occupancy_weekly: list[float],
        occupancy_monthly: list[float],
        device_hourly: list[float],
        device_weekly: list[float],
        device_monthly: list[float],
        lighting_hourly: list[float],
        lighting_weekly: list[float],
        lighting_monthly: list[float],
    ) -> None:
        self.occupancy = Schedule(occupancy_hourly, occupancy_weekly, occupancy_monthly)
        self.device = Schedule(device_hourly, device_weekly, device_monthly)
        self.lighting = Schedule(lighting_hourly, lighting_weekly, lighting_monthly)

    def __repr__(self) -> str:
        return "Schedules(occupancy, device, lighting)"
