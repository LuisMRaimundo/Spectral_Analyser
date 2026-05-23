from __future__ import annotations

import density
import dissonance_models


def test_density_public_api_symbols_importable_and_callable_when_expected() -> None:
    for name in density.__all__:
        assert hasattr(density, name), f"density is missing exported symbol '{name}'"
        symbol = getattr(density, name)
        if isinstance(symbol, type):
            continue
        if callable(symbol):
            assert callable(symbol)


def test_dissonance_models_public_api_symbols_importable_and_callable_when_expected() -> None:
    for name in dissonance_models.__all__:
        assert hasattr(dissonance_models, name), f"dissonance_models is missing exported symbol '{name}'"
        symbol = getattr(dissonance_models, name)
        if isinstance(symbol, type):
            continue
        if callable(symbol):
            assert callable(symbol)
