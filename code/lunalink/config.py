"""Mission configuration for the LunaLink simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import DEG2RAD, EARTH_MU_M3_S2, EARTH_RADIUS_M


@dataclass(frozen=True)
class OrbitConfig:
    """Fixed LunaLink orbit from the project brief."""

    perigee_altitude_m: float = 500_000.0
    apogee_altitude_m: float = 36_000_000.0
    inclination_rad: float = 63.4 * DEG2RAD
    raan_rad: float = 0.0
    argument_of_perigee_rad: float = 270.0 * DEG2RAD
    true_anomaly_at_epoch_rad: float = 0.0

    @property
    def perigee_radius_m(self) -> float:
        return EARTH_RADIUS_M + self.perigee_altitude_m

    @property
    def apogee_radius_m(self) -> float:
        return EARTH_RADIUS_M + self.apogee_altitude_m

    @property
    def semi_major_axis_m(self) -> float:
        return 0.5 * (self.perigee_radius_m + self.apogee_radius_m)

    @property
    def eccentricity(self) -> float:
        return (self.apogee_radius_m - self.perigee_radius_m) / (
            self.apogee_radius_m + self.perigee_radius_m
        )

    @property
    def period_s(self) -> float:
        return 2.0 * 3.141592653589793 * (self.semi_major_axis_m**3 / EARTH_MU_M3_S2) ** 0.5


@dataclass(frozen=True)
class SpacecraftConfig:
    mass_kg: float = 500.0
    length_x_m: float = 2.0
    length_y_m: float = 1.5
    length_z_m: float = 1.0
    eol_power_budget_w: float = 1200.0
    design_lifetime_years: float = 5.0


@dataclass(frozen=True)
class GroundStationConfig:
    name: str = "Ottobrunn"
    latitude_rad: float = 48.07 * DEG2RAD
    longitude_rad: float = 11.65 * DEG2RAD
    altitude_m: float = 0.0
    min_elevation_rad: float = 5.0 * DEG2RAD


@dataclass(frozen=True)
class SimulationConfig:
    epoch_utc: str = "2026-07-06T00:00:00Z"
    duration_s: float = 36.0 * 3600.0
    output_step_s: float = 60.0


@dataclass(frozen=True)
class MissionConfig:
    orbit: OrbitConfig = field(default_factory=OrbitConfig)
    spacecraft: SpacecraftConfig = field(default_factory=SpacecraftConfig)
    ground_station: GroundStationConfig = field(default_factory=GroundStationConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    def validation_messages(self) -> list[str]:
        messages: list[str] = []
        if self.simulation.duration_s < 36.0 * 3600.0:
            messages.append("Simulation duration is below the required 36 hours.")
        if self.ground_station.min_elevation_rad < 0.0:
            messages.append("Ground-station minimum elevation must be non-negative.")
        if self.spacecraft.mass_kg <= 0.0:
            messages.append("Spacecraft mass must be positive.")
        return messages


def default_mission_config() -> MissionConfig:
    return MissionConfig()

