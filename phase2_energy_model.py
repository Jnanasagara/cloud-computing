"""
Phase 2: Solar Energy Model
Models solar energy production across 96 time slots (15-min intervals = 24 hours).
"""

import math
import numpy as np

# ── Constants ────────────────────────────────────────────────────────────────
SLOTS_PER_DAY    = 96          # 96 × 15 min = 24 h
SLOT_DURATION    = 15          # minutes per slot
MAX_ENERGY       = 100         # peak solar energy units per slot
SUNRISE_SLOT     = 24          # 06:00
SUNSET_SLOT      = 80          # 20:00
PEAK_SLOT        = 52          # 13:00  (solar noon)

# Carbon intensity constants (gCO2 per energy unit)
SOLAR_CARBON     = 2.0         # near-zero carbon for solar
GRID_CARBON      = 45.0        # grid carbon intensity when no solar
CLOUD_FACTOR     = 0.55        # cloudy day reduces solar output by 45%


# ── Core solar functions ──────────────────────────────────────────────────────

def solar_fraction(slot: int) -> float:
    """
    Return the solar generation fraction [0.0, 1.0] for a given slot.
    Uses a bell curve centred on PEAK_SLOT between SUNRISE_SLOT and SUNSET_SLOT.
    """
    if slot < SUNRISE_SLOT or slot > SUNSET_SLOT:
        return 0.0
    # Gaussian bell curve
    sigma = (SUNSET_SLOT - SUNRISE_SLOT) / 4.0
    exponent = -0.5 * ((slot - PEAK_SLOT) / sigma) ** 2
    return math.exp(exponent)


def energy_at_slot(slot: int, cloudy: bool = False) -> float:
    """
    Return actual energy units available at a given slot.
    Applies cloud factor if it's a cloudy day.
    """
    raw = MAX_ENERGY * solar_fraction(slot)
    if cloudy:
        raw *= CLOUD_FACTOR
    return round(raw, 2)


def build_energy_profile(cloudy: bool = False) -> list:
    """
    Build a list of energy values for all 96 slots of the day.
    Returns: list of floats of length SLOTS_PER_DAY.
    """
    return [energy_at_slot(s, cloudy) for s in range(SLOTS_PER_DAY)]


def carbon_intensity(slot: int, cloudy: bool = False) -> float:
    """
    Return carbon intensity (gCO2 per energy unit) at a given slot.
    Interpolates between solar (low carbon) and grid (high carbon) based on solar fraction.
    """
    frac = solar_fraction(slot)
    if cloudy:
        frac *= CLOUD_FACTOR
    # Linear blend: full solar → SOLAR_CARBON, no solar → GRID_CARBON
    return round(SOLAR_CARBON * frac + GRID_CARBON * (1 - frac), 3)


def total_carbon(schedule: list, cloudy: bool = False) -> float:
    """
    Compute total carbon emissions for a list of (slot, energy_cost) tuples.
    schedule: list of (slot, energy_cost) pairs.
    Returns: total gCO2.
    """
    return sum(carbon_intensity(slot, cloudy) * cost for slot, cost in schedule)


def slot_to_time(slot: int) -> str:
    """Convert a slot index (0-95) to a human-readable HH:MM string."""
    total_minutes = slot * SLOT_DURATION
    hours   = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def time_to_slot(time_str: str) -> int:
    """Convert HH:MM string to slot index (0-95)."""
    parts = time_str.split(":")
    hours   = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    total_minutes = hours * 60 + minutes
    return total_minutes // SLOT_DURATION


def is_solar_window(slot: int, threshold: float = 30.0, cloudy: bool = False) -> bool:
    """Return True if solar energy at this slot exceeds the threshold."""
    return energy_at_slot(slot, cloudy) >= threshold


def peak_solar_slots(n: int = 10, cloudy: bool = False) -> list:
    """Return the top-n slots with highest solar energy."""
    profile = build_energy_profile(cloudy)
    indexed = sorted(enumerate(profile), key=lambda x: x[1], reverse=True)
    return [slot for slot, _ in indexed[:n]]


def carbon_savings_vs_grid(schedule: list, cloudy: bool = False) -> float:
    """
    Calculate carbon savings (gCO2) compared to always using grid power.
    schedule: list of (slot, energy_cost) pairs.
    """
    actual   = total_carbon(schedule, cloudy)
    grid_ref = sum(GRID_CARBON * cost for _, cost in schedule)
    return round(grid_ref - actual, 2)


def describe_energy_window(slot: int, cloudy: bool = False) -> str:
    """Return a textual description of the energy window for a given slot."""
    e = energy_at_slot(slot, cloudy)
    ci = carbon_intensity(slot, cloudy)
    time_str = slot_to_time(slot)
    if e >= 70:
        label = "PEAK SOLAR"
    elif e >= 40:
        label = "GOOD SOLAR"
    elif e >= 10:
        label = "LOW SOLAR"
    else:
        label = "NO SOLAR (GRID)"
    return f"[{time_str}] Slot {slot:02d}: {label} | Energy={e:.1f} | Carbon={ci:.1f} gCO2/unit"


# ── Numpy array helpers (used by scheduler and benchmark) ──────────────────

def energy_array(cloudy: bool = False) -> "np.ndarray":
    """Return energy profile as a numpy array of shape (96,)."""
    return np.array(build_energy_profile(cloudy), dtype=float)


def carbon_array(cloudy: bool = False) -> "np.ndarray":
    """Return carbon intensity profile as a numpy array of shape (96,)."""
    return np.array([carbon_intensity(s, cloudy) for s in range(SLOTS_PER_DAY)], dtype=float)


# ── Quick demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Solar Energy Profile (sample slots) ===")
    for slot in [0, 12, 24, 36, 48, 52, 60, 72, 80, 90, 95]:
        print(describe_energy_window(slot))
    print()
    print("=== Cloudy Day ===")
    for slot in [36, 48, 52, 60]:
        print(describe_energy_window(slot, cloudy=True))
    print()
    profile = build_energy_profile()
    total_solar = sum(profile)
    print(f"Total solar energy today: {total_solar:.1f} units")
    print(f"Peak slots: {peak_solar_slots(5)}")
