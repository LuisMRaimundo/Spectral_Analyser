# Inharmonicity family scope

The stiff-string coefficient `B` (Fletcher 1962) is a physical claim only
for string-family sources. The same numerical fit is still computed for
every note; the export column changes with family.

| Condition | `inharmonicity_coefficient_B` | `spectral_stretch_coefficient` | `inharmonicity_model_scope` |
|---|---|---|---|
| String-family token match | fitted signed `B` | NaN | `string_family` |
| Other named family | NaN | fitted value | `out_of_family` |
| Metadata absent | NaN | fitted value | `out_of_family_unspecified` |

`spectral_stretch_coefficient` contract text: phenomenological spectral
stretch; no stiff-string physical claim.

## Mapping table (`STRING_FAMILY_TOKENS`)

A source is string-family when its instrument metadata (or, at Stage 1,
`instrument` / `source_file_name` / `note`) contains any of:

Stage 1 stamps `source_file_name` from the input path before the family-scope
map runs. A filename such as `cello_A2.wav` is therefore eligible for
physical `B` even when the `instrument` field is empty. A named non-string
token such as `clarinet_A2.wav` is `out_of_family` (physical `B` is NaN).
Completely absent tokens remain `out_of_family_unspecified`. Digital silence
does not publish a measured `B`: metrics stay NaN and the filename note is
a prior only.

`cello`, `violoncello`, `violin`, `viola`, `double bass`, `doublebass`,
`contrabass`, `bass`, `guitar`, `piano`, `harp`, `clavier`, `clavecin`,
`harpsichord`, `lute`, `theorbo`, `banjo`, `mandolin`, `zither`,
`string`, `strings`, `arco`, `pizz`.

Wind, voice, and unspecified sources use the phenomenological export.
Detection is a substring match on the lower-cased token.

Internal stretch of the harmonic comb still uses the raw fitted value
when `|B|` exceeds `INHARMONICITY_B_ENABLE_THRESHOLD`. Family scope
governs the published physical claim, not the existence of the fit.
