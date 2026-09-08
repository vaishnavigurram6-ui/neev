"""Explicit unit conversions. Unknown dimensions are never guessed."""
import math

UNITS = {
    "kg": ("mass", 1), "kilogram": ("mass", 1), "mt": ("mass", 1000),
    "tonne": ("mass", 1000), "tonnes": ("mass", 1000), "ton": ("mass", 1000),
    "sqm": ("area", 1), "m2": ("area", 1), "sqft": ("area", 0.09290304),
    "cum": ("volume", 1), "m3": ("volume", 1), "cft": ("volume", 0.028316846592),
    "m": ("length", 1), "rmt": ("length", 1), "rm": ("length", 1),
    "metre": ("length", 1), "ft": ("length", 0.3048),
    "no": ("count", 1), "nos": ("count", 1), "each": ("count", 1),
    "ls": ("lump_sum", 1), "lumpsum": ("lump_sum", 1),
}


def rate_in_unit(rate: float, source: str, target: str) -> float:
    """Convert a rate per source unit to a rate per target unit."""
    def unit(value):
        return str(value or "").lower().replace("²", "2").replace("³", "3").replace(" ", "").rstrip(".")
    left, right = UNITS.get(unit(source)), UNITS.get(unit(target))
    if not left or not right or left[0] != right[0]:
        raise ValueError("Missing or incompatible benchmark units; manual comparison required.")
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("Benchmark rate must be positive and finite.")
    return rate * right[1] / left[1]