# Backup — scripts retirados do caminho ativo

Esta pasta guarda scripts que **não estão a ser usados** pelo pipeline, pela
GUI, pelos testes, nem declarados em `pyproject.toml`. Foram movidos para aqui
(em vez de apagados) por precaução. Nada no código importa estes ficheiros.

Para restaurar um ficheiro, basta movê-lo de volta para a localização original
indicada abaixo.

| Ficheiro (aqui) | Localização original | Porque foi movido |
|-----------------|----------------------|-------------------|
| `audio_analysis/batch_example.py` | `audio_analysis/batch_example.py` | Script de **exemplo/demo** (cabeçalho: "Example batch execution script"). Apenas importa `batch_audio_analyzer`; nada o importa. Não é entry point, não é teste, não está em `pyproject.toml`. |
| `scripts/harmonic_count_audit.py` | `scripts/harmonic_count_audit.py` | Utilitário de auditoria autónomo (CLI). Não é importado em lado nenhum, não tem referências em testes/CI/docs, não está em `pyproject.toml`. |

## Fase 2 — módulos da raiz mortos (movidos + removidos de `pyproject.toml`)

Estes 5 módulos estavam declarados em `pyproject.toml` mas **nenhum código `.py`
os importa** (verificado: o token de cada módulo só aparecia em `pipeline.md`,
no `pyproject.toml` e no próprio ficheiro — um import diferido teria de conter
o texto do nome em algum `.py`, e não existe). Foram movidos para
`Backup/root_modules/` e removidos da lista `py-modules` do `pyproject.toml`.

| Ficheiro (aqui) | Localização original | Porque foi movido |
|-----------------|----------------------|-------------------|
| `root_modules/interface.py` | `interface.py` | GUI PyQt **legado/referência**. O próprio docstring: "remains for reference or manual experiments only". `main.py` reencaminha para o orquestrador Tk; nada importa este módulo. |
| `root_modules/export_paths.py` | `export_paths.py` | Sanitização de paths não usada (a sanitização ativa é feita por `metadata_sanitizer`). Nenhum importador. |
| `root_modules/public_audio_identifiers.py` | `public_audio_identifiers.py` | Construtores de IDs/hash não usados. Nenhum importador. |
| `root_modules/reference_signal_utils.py` | `reference_signal_utils.py` | Geradores de sinais sintéticos não usados (nem pelos testes — estes geram WAVs localmente). Nenhum importador. |
| `root_modules/runtime_versions.py` | `runtime_versions.py` | Fingerprint de versões não usado. Nenhum importador. |

**Para restaurar qualquer um:** mover de volta para a raiz **e** voltar a
adicionar o nome (sem `.py`) à lista `py-modules` em `pyproject.toml`.

## Notas de segurança (o que NÃO foi movido e porquê)

- **Os 49 módulos da raiz** estão todos declarados em `pyproject.toml`
  (`[tool.setuptools] py-modules`) — fazem parte da superfície publicada do
  pacote e **não** foram tocados.
- `harmonic_alignment.py` parece não-importado por análise estática, mas é
  carregado via **import diferido** durante a análise (confirmado por profiling:
  `compute_harmonic_alignment_metrics`). **Mantido.**
- `audio_analysis/super_audio_analyzer.py`, `super_audio_analyzer_gui.py` e
  `batch_audio_analyzer.py` são usados (subprocess do orquestrador integrado e
  imports diferidos da GUI do analisador). **Mantidos.**
