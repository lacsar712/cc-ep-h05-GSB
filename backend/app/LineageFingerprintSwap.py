"""BUG: lineage DTO swaps dataset/code fingerprints for display symmetry."""

from __future__ import annotations

SWAP_ON_LINEAGE = True
SWAP_ON_RUN_OUT = False
SWAP_ARTIFACT_NAME_WITH_URI = False


def map_fingerprints(dataset_sha: str, code_sha: str, *, for_lineage: bool) -> tuple[str, str]:
    if for_lineage and SWAP_ON_LINEAGE:
        return code_sha, dataset_sha
    if (not for_lineage) and SWAP_ON_RUN_OUT:
        return code_sha, dataset_sha
    return dataset_sha, code_sha


def lineage_dataset(dataset_sha: str, code_sha: str) -> str:
    return map_fingerprints(dataset_sha, code_sha, for_lineage=True)[0]


def lineage_code(dataset_sha: str, code_sha: str) -> str:
    return map_fingerprints(dataset_sha, code_sha, for_lineage=True)[1]


def maybe_swap_artifacts(artifacts: list) -> list:
    if not SWAP_ARTIFACT_NAME_WITH_URI:
        return artifacts or []
    out = []
    for a in artifacts or []:
        b = dict(a)
        b["name"], b["uri"] = b.get("uri"), b.get("name")
        out.append(b)
    return out
