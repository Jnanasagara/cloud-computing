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


# ── Global overrides for real-world dataset support ───────────────────────────
_USE_DATASET: bool = False
_DATASET_SOLAR_PROFILE: list = []  # length 96
_DATASET_CACHE: dict = {}  # Cache: {date_str: solar_profile}
_GLOBAL_MAX_RADIATION: float = 1.0  # Normalized scale factor



# ── Core solar functions ──────────────────────────────────────────────────────

def solar_fraction(slot: int) -> float:
    """
    Return the solar generation fraction [0.0, 1.0] for a given slot.
    Uses a bell curve centred on PEAK_SLOT between SUNRISE_SLOT and SUNSET_SLOT.
    """
    if _USE_DATASET:
        if not _DATASET_SOLAR_PROFILE:
            return 0.0
        return _DATASET_SOLAR_PROFILE[slot] / MAX_ENERGY

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
    if _USE_DATASET:
        if not _DATASET_SOLAR_PROFILE:
            return 0.0
        val = _DATASET_SOLAR_PROFILE[slot]
        if cloudy:
            val *= CLOUD_FACTOR
        return round(val, 2)

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
    if _USE_DATASET:
        val = energy_at_slot(slot, cloudy)
        frac = val / MAX_ENERGY
        return round(SOLAR_CARBON * frac + GRID_CARBON * (1 - frac), 3)

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


# ── Dataset Parsers and Utility Helpers ────────────────────────────────────────

def load_solar_dataset(filepath: str = "SolarPrediction.csv") -> list:
    """
    Load the solar dataset from a CSV, group by date, normalize by the global maximum,
    and cache the daily 96-slot profiles.
    """
    import os
    import pandas as pd
    import numpy as np

    global _DATASET_CACHE, _GLOBAL_MAX_RADIATION

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Solar dataset not found at: {filepath}")

    # Read dataset
    df = pd.read_csv(filepath)

    # Clean date strings: "9/29/2016 12:00:00 AM" -> "2016-09-29"
    df['CleanDate'] = df['Data'].apply(lambda x: x.split()[0])
    df['CleanDate'] = pd.to_datetime(df['CleanDate'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')

    # Find the global maximum radiation to use as scaling factor (Global Max Normalization)
    _GLOBAL_MAX_RADIATION = float(df['Radiation'].max())
    if _GLOBAL_MAX_RADIATION <= 0:
        _GLOBAL_MAX_RADIATION = 1.0

    # Parse time to slot indices
    def time_to_slot_idx(t_str):
        parts = t_str.split(':')
        h = int(parts[0])
        m = int(parts[1])
        return (h * 60 + m) // 15

    df['Slot'] = df['Time'].apply(time_to_slot_idx)

    # Group by CleanDate and Slot
    grouped = df.groupby(['CleanDate', 'Slot'])['Radiation'].mean().reset_index()

    # Get unique dates
    unique_dates = df['CleanDate'].unique()

    _DATASET_CACHE = {}

    for date in unique_dates:
        day_data = grouped[grouped['CleanDate'] == date]
        xp = day_data['Slot'].values
        # Scale to 0..100 relative to Global Max
        fp = (day_data['Radiation'].values / _GLOBAL_MAX_RADIATION) * 100.0
        
        if len(xp) > 0:
            full_slots = np.arange(96)
            profile = np.interp(full_slots, xp, fp, left=0.0, right=0.0)
            profile = np.round(profile, 2).tolist()
        else:
            profile = [0.0] * 96

        _DATASET_CACHE[date] = profile

    return sorted(list(_DATASET_CACHE.keys()))


def activate_solar_day(date_str: str, filepath: str = "SolarPrediction.csv") -> bool:
    """
    Activate the solar profile for a specific date from the dataset.
    Loads the dataset if it hasn't been cached yet.
    """
    global _USE_DATASET, _DATASET_SOLAR_PROFILE, _DATASET_CACHE
    
    if not _DATASET_CACHE:
        try:
            load_solar_dataset(filepath)
        except Exception as e:
            print(f"[ERROR] Failed to load solar dataset: {e}")
            _USE_DATASET = False
            return False

    if date_str in _DATASET_CACHE:
        _DATASET_SOLAR_PROFILE = _DATASET_CACHE[date_str]
        _USE_DATASET = True
        return True
    else:
        print(f"[WARN] Date {date_str} not found in solar dataset. Falling back to synthetic solar profile.")
        _USE_DATASET = False
        return False


def deactivate_solar_dataset():
    """Disable the dataset-backed solar profile and return to synthetic mode."""
    global _USE_DATASET
    _USE_DATASET = False


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

