"""
AL-05: Priors por especie.

Base de conocimiento estática sobre el comportamiento ESPERABLE de cada especie,
usada como punto de partida antes de que el aprendizaje individual lo refine.
"""
from __future__ import annotations

# Priors para especie 'cat' — valores normalizados
CAT_PRIORS: dict = {
    "preferred_heights": [0.5, 0.7, 1.0],   # fracción del frame (prefieren alto/elevado)
    "active_hours": list(range(5, 9)) + list(range(17, 22)),  # crepusculares
    "rest_fraction": 0.7,   # 70% del tiempo están en reposo
    "top_speed_norm": 0.15,  # desplazamiento máximo por frame (normalizado)
    "typical_zones": ["sofa", "cama", "ventana", "suelo_soleado"],
    "dangerous_curiosity": True,  # les atraen cables, cocinas, altura
}

DOG_PRIORS: dict = {
    "preferred_heights": [0.0, 0.3],
    "active_hours": list(range(6, 10)) + list(range(17, 20)),
    "rest_fraction": 0.5,
    "top_speed_norm": 0.25,
    "typical_zones": ["suelo", "cama", "cesta"],
    "dangerous_curiosity": False,
}

_PRIORS: dict[str, dict] = {
    "cat": CAT_PRIORS,
    "dog": DOG_PRIORS,
}


def get_priors(species: str = "cat") -> dict:
    return _PRIORS.get(species.lower(), CAT_PRIORS)


def is_active_hour(species: str = "cat") -> bool:
    """¿Es una hora de actividad esperada para esta especie?"""
    import time
    hour = int(time.localtime().tm_hour)
    return hour in get_priors(species).get("active_hours", [])


def expected_max_displacement(species: str = "cat") -> float:
    """Desplazamiento máximo esperado entre frames consecutivos."""
    return get_priors(species).get("top_speed_norm", 0.15)
