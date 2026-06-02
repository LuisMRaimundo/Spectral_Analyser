from __future__ import annotations

from pipeline_contract import (
    CANONICAL_STAGE3_EWSD_CONTRACT,
    CANONICAL_STAGE3_EWSD_PURE,
    CANONICAL_STAGE3_EWSD_UNCERTAINTY,
    PIPELINE_CONTRACT_VERSION,
    get_canonical_pipeline_contract,
)


def test_pipeline_contract_includes_ewsd_v18_1_modules() -> None:
    c = get_canonical_pipeline_contract()
    assert "EWSD_v18_1" in PIPELINE_CONTRACT_VERSION or "UQ" in PIPELINE_CONTRACT_VERSION
    assert c.stage3_ewsd_pure == CANONICAL_STAGE3_EWSD_PURE
    assert c.stage3_ewsd_uncertainty == CANONICAL_STAGE3_EWSD_UNCERTAINTY
    assert c.stage3_ewsd_contract == CANONICAL_STAGE3_EWSD_CONTRACT
