"""Evidence-based infrastructure absence checks.

A single image cannot prove that an asset is missing. This helper combines
mapped expectations with repeated observations from the same geospatial area.
"""
ASSET_CLASSES = {
    "zebra_crossing": {"zebra_crossing", "damaged_zebra_crossing"},
    "road_divider": {"road_divider", "damaged_divider"},
    "traffic_sign": {"traffic_sign", "damaged_traffic_sign"},
}

def assess_missing_assets(expected_assets, observed_classes, repeated_observations: int, min_observations: int = 2):
    expected = [str(x) for x in expected_assets]
    observed = {str(x) for x in observed_classes}
    missing = []
    insufficient = repeated_observations < min_observations
    for asset in expected:
        known = ASSET_CLASSES.get(asset)
        if not known:
            continue
        seen = bool(known & observed)
        if not seen and not insufficient:
            missing.append({
                "asset": asset,
                "status": "missing_candidate",
                "confidence_source": "repeated absence against mapped expectation",
                "observation_count": repeated_observations,
            })
    return {
        "missing_candidates": missing,
        "observation_count": repeated_observations,
        "minimum_observations": min_observations,
        "evidence_sufficient": not insufficient,
        "note": "Candidates require geotagged expected-asset data and repeated route observations before confirmation.",
    }
