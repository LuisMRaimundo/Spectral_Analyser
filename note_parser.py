"""Canonical note-token parser for SoundSpectrAnalyse.

This module is the single source of truth for note-token extraction from
audio filenames and result folders. It enforces the following audit
rules:

* A valid note token consists of:
    - one letter ``A`` through ``G`` (uppercase or lowercase),
    - an optional accidental (``#``, ``b``, ``\u266f`` / sharp,
      ``\u266d`` / flat),
    - one or more **mandatory** octave digits (positive integer).
* Unicode accidentals are normalised to ASCII ``#`` / ``b``.
* Source priority (highest first) for any caller that knows where the
  note tokens may live:

    1. ``manifest`` — explicit note already produced upstream
       (e.g. manifest / orchestrator metadata).
    2. ``filename_token`` — first valid token in the audio filename.
    3. ``parent_folder`` — first valid token in the per-note result
       folder name.
    4. ``fallback_no_octave`` — letter-only label scraped from the
       filename / parent folder when no explicit octave is present.
       This is a diagnostic label only; callers must not feed it back
       into ``librosa.note_to_hz``.
    5. ``unknown`` — nothing parseable.

Parsers never invent a default octave and never fall back to
``filename_stem.split('_')[0]`` style heuristics, which mis-identify
ornamentation tokens such as ``Bn``, ``ord`` or ``pp`` as notes.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


__all__ = (
    "parse_note_token",
    "canonical_note_from_filename",
    "NOTE_SOURCE_MANIFEST",
    "NOTE_SOURCE_FILENAME",
    "NOTE_SOURCE_PARENT_FOLDER",
    "NOTE_SOURCE_FALLBACK_NO_OCTAVE",
    "NOTE_SOURCE_UNKNOWN",
    "VALID_NOTE_SOURCES",
)


NOTE_SOURCE_MANIFEST = "manifest"
NOTE_SOURCE_FILENAME = "filename_token"
NOTE_SOURCE_PARENT_FOLDER = "parent_folder"
NOTE_SOURCE_FALLBACK_NO_OCTAVE = "fallback_no_octave"
NOTE_SOURCE_UNKNOWN = "unknown"

VALID_NOTE_SOURCES: Tuple[str, ...] = (
    NOTE_SOURCE_MANIFEST,
    NOTE_SOURCE_FILENAME,
    NOTE_SOURCE_PARENT_FOLDER,
    NOTE_SOURCE_FALLBACK_NO_OCTAVE,
    NOTE_SOURCE_UNKNOWN,
)


# Letter + optional accidental + mandatory positive octave digits.
# Unicode accidentals (\u266f / \u266d) are accepted and normalised to
# ASCII below. A leading position predicate prevents matches inside a
# larger alphabetical token (e.g. the ``Bn`` in ``Bn-ord-A#1`` must NOT
# match ``B`` even though ``B`` is a valid letter).
_NOTE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z])([A-Ga-g])([#b\u266f\u266d]?)(\d+)"
)

# Letter + optional accidental WITHOUT octave digits (e.g. ``A#``,
# ``Bb``). Only used for the diagnostic ``fallback_no_octave`` source.
_NOTE_LETTER_ONLY_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Ga-g])([#b\u266f\u266d]?)(?![A-Za-z0-9])"
)


def _normalise_accidental(a: str) -> str:
    if a == "\u266f":
        return "#"
    if a == "\u266d":
        return "b"
    return a


def parse_note_token(text: Optional[str]) -> Optional[str]:
    """Return the first canonical note token in ``text`` or ``None``.

    The returned token has an uppercase letter and an ASCII accidental.

    Examples::

        parse_note_token("A#3_3.72sec_Sustains.wav")              # "A#3"
        parse_note_token("Bb4_3.80sec_Sustains.wav")              # "Bb4"
        parse_note_token("Bn-ord-A#1-pp-N-N_Sustains.wav")        # "A#1"
        parse_note_token("D6_3.88sec_shifted_Sustains.wav")       # "D6"
        parse_note_token("Bn-ord-Sustains.wav")                   # None
    """

    if not text:
        return None
    s = str(text).strip()
    if not s:
        return None
    m = _NOTE_TOKEN_RE.search(s)
    if not m:
        return None
    letter = m.group(1).upper()
    accidental = _normalise_accidental(m.group(2) or "")
    octave = m.group(3)
    return f"{letter}{accidental}{octave}"


def _parse_letter_only(text: str) -> Optional[str]:
    """Return ``A`` / ``Bb`` style letter-only label when the source
    carries a note letter (with optional accidental) but no explicit
    octave. Used only for the diagnostic ``fallback_no_octave`` source.
    """

    m = _NOTE_LETTER_ONLY_RE.search(text)
    if not m:
        return None
    letter = m.group(1).upper()
    accidental = _normalise_accidental(m.group(2) or "")
    return f"{letter}{accidental}"


def canonical_note_from_filename(
    filename: Optional[str],
    *,
    manifest_note: Optional[str] = None,
    parent_folder: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """Return ``(note, note_source)`` following the canonical priority.

    Source order:

        1. ``manifest`` — when ``manifest_note`` parses to a valid token.
        2. ``filename_token`` — first valid token in ``filename``.
        3. ``parent_folder`` — first valid token in ``parent_folder``.
        4. ``fallback_no_octave`` — letter-only label scraped from
           ``filename`` or ``parent_folder`` (no explicit octave found).
           Diagnostic only.
        5. ``unknown`` — nothing parseable.

    ``note_source`` is always one of :data:`VALID_NOTE_SOURCES`.
    """

    n = parse_note_token(manifest_note)
    if n:
        return n, NOTE_SOURCE_MANIFEST
    n = parse_note_token(filename)
    if n:
        return n, NOTE_SOURCE_FILENAME
    n = parse_note_token(parent_folder)
    if n:
        return n, NOTE_SOURCE_PARENT_FOLDER

    fallback: Optional[str] = None
    if filename:
        fallback = _parse_letter_only(str(filename))
    if not fallback and parent_folder:
        fallback = _parse_letter_only(str(parent_folder))
    if fallback:
        return fallback, NOTE_SOURCE_FALLBACK_NO_OCTAVE
    return None, NOTE_SOURCE_UNKNOWN
