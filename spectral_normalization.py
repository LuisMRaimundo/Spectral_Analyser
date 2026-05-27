from __future__ import annotations

import math
import warnings


def n_fft_normalization_factor(
    n_fft: int,
    n_fft_reference: int = 8192,
    quantity_kind: str = "peak_amplitude_sum",
    kind: str | None = None,
) -> float:
    """
    Compute the multiplier that brings an N-dependent spectral quantity onto
    the reference-N scale.

    quantity_kind must be one of:
    - ``"peak_amplitude_sum"``: factor = N_ref / N
      Use for sums of peak-bin magnitudes (e.g. harmonic_amplitude_sum).
      Peak magnitudes scale linearly with window coherent gain (const * N).
    - ``"peak_power_sum"``: factor = (N_ref / N)^2
      Use for sums of peak-bin powers.
    - ``"broadband_amplitude_l2"``: factor = sqrt(N_ref / N)
      Reserved for L2 norms of broadband-noise spectra.
    - ``"broadband_power_l2"``: factor = N_ref / N
      Reserved for broadband power-L2 quantities.

    The legacy keyword ``kind`` is preserved for backward compatibility:
      kind="amplitude" -> quantity_kind="broadband_amplitude_l2"
      kind="power"     -> quantity_kind="broadband_power_l2"
    and emits a DeprecationWarning.

    References
    ----------
    - Heinzel, G., Rudiger, A., & Schilling, R. (2002). Spectrum and spectral
      density estimation by the Discrete Fourier transform (DFT), including a
      comprehensive list of window functions and some new at-top windows.
      Max-Planck-Institut fur Gravitationsphysik technical report.
    - Harris, F. J. (1978). On the use of windows for harmonic analysis with
      the discrete Fourier transform. Proceedings of the IEEE, 66(1), 51-83.
    """
    n = int(n_fft)
    n_ref = int(n_fft_reference)
    if n <= 0 or n_ref <= 0:
        raise ValueError("n_fft and n_fft_reference must be positive integers.")

    ratio = float(n_ref) / float(n)
    if kind is not None:
        kind_norm = str(kind or "").strip().lower()
        legacy_to_quantity = {
            "amplitude": "broadband_amplitude_l2",
            "power": "broadband_power_l2",
        }
        if kind_norm not in legacy_to_quantity:
            raise ValueError("kind must be one of {'amplitude', 'power'}.")
        quantity_kind = legacy_to_quantity[kind_norm]
        warnings.warn(
            "n_fft_normalization_factor(kind=...) is deprecated; use "
            "quantity_kind=... explicitly.",
            DeprecationWarning,
            stacklevel=2,
        )

    qk = str(quantity_kind or "peak_amplitude_sum").strip().lower()
    if qk == "peak_amplitude_sum":
        return float(ratio)
    if qk == "peak_power_sum":
        return float(ratio * ratio)
    if qk == "broadband_amplitude_l2":
        return float(math.sqrt(ratio))
    if qk == "broadband_power_l2":
        return float(ratio)
    raise ValueError(
        "quantity_kind must be one of "
        "{'peak_amplitude_sum', 'peak_power_sum', "
        "'broadband_amplitude_l2', 'broadband_power_l2'}."
    )
