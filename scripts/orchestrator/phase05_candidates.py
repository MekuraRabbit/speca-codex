"""Build representative PoC candidates from Phase 04 review results."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANDIDATE_VERDICTS = {
    "CONFIRMED_VULNERABILITY",
    "CONFIRMED_POTENTIAL",
    # Legacy Phase 04 partials used DOWNGRADED as a verdict for findings that
    # survived review but had their severity capped. Keep them reportable.
    "DOWNGRADED",
}

VERDICT_RANK = {
    "CONFIRMED_VULNERABILITY": 0,
    "DOWNGRADED": 1,
    "CONFIRMED_POTENTIAL": 2,
}

SEVERITY_RANK = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Informational": 4,
    "": 5,
}


def build_poc_candidate_index(output_dir: Path) -> dict[str, Any]:
    """Return the Phase 05 representative PoC candidate index.

    The selector is deliberately deterministic and conservative: Phase 05 should
    shrink manual PoC effort by grouping duplicate root causes, not invent new
    findings. It only consumes Phase 03/04 partials and TARGET_INFO from the
    selected output directory.
    """

    output_dir = output_dir.resolve()
    target_info = _read_optional_json(output_dir / "TARGET_INFO.json")
    phase3_items = _load_phase_items(output_dir, "03", "audit_items")
    phase4_items = _load_phase_items(output_dir, "04", "reviewed_items")

    audit_by_id = {
        _item_id(item): item
        for item in phase3_items
        if _item_id(item)
    }

    merged_items: list[dict[str, Any]] = []
    for review in phase4_items:
        prop_id = _item_id(review)
        verdict = str(review.get("review_verdict", ""))
        if not prop_id or verdict not in CANDIDATE_VERDICTS:
            continue
        audit = audit_by_id.get(prop_id, {})
        merged_items.append(_merge_candidate_input(review, audit, target_info))

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in merged_items:
        groups.setdefault(item["group_key"], []).append(item)

    candidates = [
        _build_candidate(group_key, items, target_info)
        for group_key, items in sorted(groups.items())
    ]

    return {
        "metadata": {
            "phase": "05-candidates",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_dir": output_dir.as_posix(),
            "source_files": {
                "phase03_partials": len(list(output_dir.glob("03_PARTIAL_*.json"))),
                "phase04_partials": len(list(output_dir.glob("04_PARTIAL_*.json"))),
            },
            "reviewed_candidate_items": len(merged_items),
            "candidate_count": len(candidates),
        },
        "target_info": target_info,
        "candidates": candidates,
    }


def write_poc_candidate_index(output_dir: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Build and write ``05_POC_CANDIDATES.json``."""

    output_dir = output_dir.resolve()
    output_path = output_path or (output_dir / "05_POC_CANDIDATES.json")
    index = build_poc_candidate_index(output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _load_phase_items(output_dir: Path, phase: str, key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob(f"{phase}_PARTIAL_*.json")):
        data = _read_optional_json(path)
        raw_items = data.get(key, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if isinstance(item, dict):
                item_copy = dict(item)
                item_copy["_source_file"] = path.as_posix()
                items.append(item_copy)
    return items


def _item_id(item: dict[str, Any]) -> str:
    return str(
        item.get("property_id")
        or item.get("check_id")
        or item.get("checklist_id")
        or ""
    )


def _merge_candidate_input(
    review: dict[str, Any],
    audit: dict[str, Any],
    target_info: dict[str, Any],
) -> dict[str, Any]:
    original_prop_id = _item_id(review)
    target_checkout = _target_checkout(target_info)
    target_files = _target_files(audit, target_checkout)
    primary_file = target_files[0] if target_files else ""
    challenge = _challenge_from_paths(target_files) or _challenge_from_property_id(original_prop_id)
    prop_id = _normalized_property_id(original_prop_id, challenge)
    symbol = _primary_symbol(audit)
    attack_text = " ".join(
        str(value)
        for value in [
            audit.get("attack_scenario"),
            audit.get("summary"),
            audit.get("proof_trace"),
            audit.get("code_snippet"),
            review.get("reviewer_notes"),
            review.get("final_recommendation"),
        ]
        if value
    )
    attack_family = _attack_family(challenge, symbol, attack_text)

    return {
        "property_id": prop_id,
        "original_property_id": original_prop_id,
        "review_verdict": review.get("review_verdict", ""),
        "severity_action": _severity_action(review),
        "adjusted_severity": review.get("adjusted_severity", ""),
        "reviewer_notes": review.get("reviewer_notes", ""),
        "spec_reference": review.get("spec_reference", ""),
        "original_classification": review.get("original_classification", ""),
        "audit_classification": audit.get("classification", ""),
        "audit_summary": audit.get("summary", ""),
        "attack_scenario": audit.get("attack_scenario", ""),
        "code_path": audit.get("code_path", ""),
        "target_files": target_files,
        "primary_file": primary_file,
        "primary_symbol": symbol,
        "challenge": challenge,
        "attack_family": attack_family,
        "group_key": f"{challenge}:{attack_family}",
    }


def _build_candidate(
    group_key: str,
    items: list[dict[str, Any]],
    target_info: dict[str, Any],
) -> dict[str, Any]:
    sorted_items = sorted(items, key=_candidate_sort_key)
    representative = sorted_items[0]
    covered_ids = sorted(item["property_id"] for item in sorted_items)
    challenge = representative["challenge"] or "unknown"
    attack_family = representative["attack_family"] or "finding"
    target_checkout = _target_checkout(target_info)
    output_path = _recommended_output_path(target_checkout, challenge, attack_family, target_info)
    review_verdict = _candidate_review_verdict(representative)

    return {
        "candidate_id": _candidate_id(challenge, attack_family, covered_ids),
        "group_key": group_key,
        "representative_property_id": representative["property_id"],
        "covered_property_ids": covered_ids,
        "covered_count": len(covered_ids),
        "challenge": challenge,
        "attack_family": attack_family,
        "review_verdict": review_verdict,
        "severity_action": representative["severity_action"],
        "adjusted_severity": representative["adjusted_severity"],
        "spec_reference": representative["spec_reference"],
        "target_files": sorted({path for item in sorted_items for path in item["target_files"]}),
        "primary_file": representative["primary_file"],
        "primary_symbol": representative["primary_symbol"],
        "attack_summary": _summary_for_candidate(representative),
        "recommended_type": _recommended_type(target_info),
        "recommended_output_path": output_path,
        "run_command": _run_command(output_path, target_info),
        "target_local_checkout": target_checkout,
        "source_items": [
            _source_item_for_output(item)
            for item in sorted_items
        ],
        "status": "candidate",
    }


def _source_item_for_output(item: dict[str, Any]) -> dict[str, Any]:
    source_item = {
        "property_id": item["property_id"],
        "review_verdict": item["review_verdict"],
        "severity_action": item["severity_action"],
        "adjusted_severity": item["adjusted_severity"],
        "primary_file": item["primary_file"],
        "primary_symbol": item["primary_symbol"],
    }
    if item.get("original_property_id") and item["original_property_id"] != item["property_id"]:
        source_item["original_property_id"] = item["original_property_id"]
    return source_item


def _candidate_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    notes_len = len(str(item.get("reviewer_notes") or item.get("attack_scenario") or ""))
    return (
        VERDICT_RANK.get(str(item.get("review_verdict", "")), 9),
        SEVERITY_RANK.get(str(item.get("adjusted_severity", "")), 5),
        -notes_len,
        item["property_id"],
    )


def _target_checkout(target_info: dict[str, Any]) -> str:
    checkout = str(target_info.get("local_checkout") or "target_workspace").replace("\\", "/").strip()
    return checkout.rstrip("/")


def _target_files(audit: dict[str, Any], target_checkout: str) -> list[str]:
    files: list[str] = []

    code_path = str(audit.get("code_path") or "")
    if code_path:
        file_part = code_path.split("::", 1)[0]
        files.append(_anchor_code_path(file_part, target_checkout))

    code_scope = audit.get("code_scope")
    if isinstance(code_scope, dict):
        locations = code_scope.get("locations", [])
        if isinstance(locations, list):
            for location in locations:
                if isinstance(location, dict) and location.get("file"):
                    files.append(_anchor_code_path(str(location["file"]), target_checkout))

    seen: set[str] = set()
    unique: list[str] = []
    for path in files:
        normalized = path.replace("\\", "/").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _anchor_code_path(path: str, target_checkout: str) -> str:
    candidate = path.replace("\\", "/").strip()
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if not candidate:
        return ""
    checkout = target_checkout.rstrip("/")
    if candidate == checkout or candidate.startswith(f"{checkout}/"):
        return candidate
    if candidate.startswith(("http://", "https://")):
        return candidate
    if re.match(r"^[A-Za-z]:/", candidate) or candidate.startswith("/"):
        return candidate
    if candidate.startswith("target_workspace/") and checkout != "target_workspace":
        return f"{checkout}/{_safe_relative_path(candidate[len('target_workspace/'):])}"
    return f"{checkout}/{_safe_relative_path(candidate)}"


def _challenge_from_paths(paths: list[str]) -> str:
    for path in paths:
        normalized = path.replace("\\", "/")
        match = re.search(r"/(?:contracts|test)/([^/]+)/", f"/{normalized}")
        if match:
            return match.group(1)
    return ""


def _challenge_from_property_id(prop_id: str) -> str:
    match = re.match(r"PROP-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-(?:pre|post|inv|asm)-", prop_id)
    return match.group(1) if match else "unknown"


def _normalized_property_id(prop_id: str, challenge: str) -> str:
    if not prop_id or not challenge or challenge == "unknown":
        return prop_id
    return re.sub(
        r"^PROP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-(pre|post|inv|asm)-",
        f"PROP-{challenge}-\\1-",
        prop_id,
        count=1,
    )


def _primary_symbol(audit: dict[str, Any]) -> str:
    code_path = str(audit.get("code_path") or "")
    parts = code_path.split("::")
    if len(parts) >= 2 and not parts[1].startswith("L"):
        return parts[1]

    code_scope = audit.get("code_scope")
    if isinstance(code_scope, dict):
        for location in code_scope.get("locations", []):
            if isinstance(location, dict) and location.get("symbol"):
                return str(location["symbol"])
    return ""


def _attack_family(challenge: str, symbol: str, text: str) -> str:
    haystack = f"{challenge} {symbol} {text}".lower()
    if _has_oracle_source_quorum_context(challenge, symbol, text):
        return "oracle-source-quorum-degradation"
    if _has_max_boundary_conversion_context(haystack):
        return "max-boundary-conversion-overflow"
    if _has_short_delivering_underlying_context(haystack):
        return "short-delivering-underlying"

    known_challenge_families = {
        "truster": "unauthorized-token-approval",
        "side-entrance": "flash-loan-deposit-credit",
        "the-rewarder": "flash-loan-reward-snapshot",
        "selfie": "flash-loan-governance-snapshot",
        "puppet": "amm-spot-price-manipulation",
        "naive-receiver": "forced-flash-loan-fee-drain",
        "unstoppable": "direct-token-transfer-dos",
    }
    if challenge in known_challenge_families:
        return known_challenge_families[challenge]

    if "approve" in haystack and "transferfrom" in haystack:
        return "unauthorized-token-approval"
    if "reward" in haystack and ("snapshot" in haystack or "accounting" in haystack or "flash" in haystack):
        return "flash-loan-reward-snapshot"
    if "side-entrance" in haystack or ("deposit" in haystack and "withdraw" in haystack and "flashloan" in haystack):
        return "flash-loan-deposit-credit"
    if "governance" in haystack or "queueaction" in haystack or "snapshotid" in haystack:
        return "flash-loan-governance-snapshot"
    if "uniswap" in haystack or "tokenToEthSwapInput".lower() in haystack or "computeoracleprice" in haystack:
        return "amm-spot-price-manipulation"
    if "oracle" in haystack or "postprice" in haystack or "median" in haystack:
        return "oracle-price-manipulation"
    if "receiver" in haystack and ("fixed fee" in haystack or "balance" in haystack) and "flashloan" in haystack:
        return "forced-flash-loan-fee-drain"
    if "direct" in haystack and ("poolbalance" in haystack or "balance assertion" in haystack or "token balance" in haystack):
        return "direct-token-transfer-dos"
    return _slug(symbol or challenge or "finding")


def _recommended_type(target_info: dict[str, Any]) -> str:
    language = str(target_info.get("language", "")).lower()
    if language in {"solidity", "javascript", "typescript", "js", "ts"}:
        return "it"
    return "unit"


def _recommended_output_path(
    target_checkout: str,
    challenge: str,
    attack_family: str,
    target_info: dict[str, Any],
) -> str:
    language = str(target_info.get("language", "")).lower()
    slug = _slug(attack_family, max_len=40)
    if language == "solidity":
        return f"{target_checkout}/test/speca-poc/{challenge}/poc_{slug}.challenge.js"
    if language in {"javascript", "js"}:
        return f"{target_checkout}/test/speca-poc/{challenge}/poc_{slug}.test.js"
    if language in {"typescript", "ts"}:
        return f"{target_checkout}/test/speca-poc/{challenge}/poc_{slug}.test.ts"
    return f"{target_checkout}/test/speca-poc/{challenge}/poc_{slug}_test.py"


def _run_command(output_path: str, target_info: dict[str, Any]) -> str:
    target_checkout = _target_checkout(target_info)
    rel_path = output_path
    if rel_path.startswith(f"{target_checkout}/"):
        rel_path = rel_path[len(target_checkout) + 1:]

    language = str(target_info.get("language", "")).lower()
    if language == "solidity":
        return f"npm run compile && npx mocha --timeout 5000 --exit {rel_path}"
    if language in {"javascript", "typescript", "js", "ts"}:
        return f"npm test -- {rel_path}"
    if language == "python":
        return f"pytest {rel_path} -vv"
    return f"<run native test command for {rel_path}>"


def _candidate_id(challenge: str, attack_family: str, covered_ids: list[str]) -> str:
    digest = hashlib.sha256("\n".join(covered_ids).encode("utf-8")).hexdigest()[:8]
    return f"POC-{_slug(challenge, 24)}-{_slug(attack_family, 40)}-{digest}"


def _candidate_review_verdict(item: dict[str, Any]) -> str:
    if (
        item.get("attack_family") == "oracle-source-quorum-degradation"
        and _item_has_oracle_source_quorum_context(item)
    ):
        return "CONFIRMED_POTENTIAL"
    return str(item.get("review_verdict", ""))


def _severity_action(review: dict[str, Any]) -> str:
    action = str(review.get("severity_action") or "")
    if action:
        return action
    if str(review.get("review_verdict") or "") == "DOWNGRADED":
        return "DOWNGRADED"
    return ""


def _summary_for_candidate(item: dict[str, Any]) -> str:
    if item.get("attack_family") == "max-boundary-conversion-overflow":
        return (
            "A maximum supply or asset-balance boundary can make ERC-4626 "
            "conversion, preview, or limit-query view functions revert through "
            "checked arithmetic in the shared conversion helpers. Treat this as "
            "a standards-compliance edge case unless practical reachability is proven."
        )
    if item.get("attack_family") == "short-delivering-underlying":
        return (
            "A fee-on-transfer, deflationary, or otherwise short-delivering "
            "underlying token can make the vault receive fewer assets than the "
            "nominal deposit or mint amount. Treat this as a conditional "
            "integration hazard unless the target explicitly supports such assets."
        )
    if (
        item.get("attack_family") == "oracle-source-quorum-degradation"
        and _item_has_oracle_source_quorum_context(item)
    ):
        return (
            "A current oracle source, or an attacker holding that source key, can call "
            "renounceRole(TRUSTED_SOURCE_ROLE, source) directly on the oracle. This "
            "degrades oracle quorum and is a potential availability risk; a full median "
            "DoS requires the source set to become empty."
        )
    for key in ("attack_scenario", "audit_summary", "reviewer_notes"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return f"Representative PoC candidate for {item['property_id']}."


def _item_has_oracle_source_quorum_context(item: dict[str, Any]) -> bool:
    text = " ".join(
        str(item.get(key) or "")
        for key in (
            "attack_scenario",
            "audit_summary",
            "reviewer_notes",
            "code_path",
            "primary_file",
        )
    )
    return _has_oracle_source_quorum_context(
        str(item.get("challenge") or ""),
        str(item.get("primary_symbol") or ""),
        text,
    )


def _has_oracle_source_quorum_context(challenge: str, symbol: str, text: str) -> bool:
    haystack = f"{challenge} {symbol} {text}".lower()
    if "renounce" not in haystack:
        return False

    oracle_terms = (
        "oracle",
        "trustfuloracle",
        "postprice",
        "median",
    )
    source_quorum_terms = (
        "source",
        "trusted_source_role",
        "trusted source",
        "source set",
        "quorum",
        "median",
    )
    return (
        any(term in haystack for term in oracle_terms)
        and any(term in haystack for term in source_quorum_terms)
    )


def _has_max_boundary_conversion_context(haystack: str) -> bool:
    boundary_terms = (
        "type(uint256).max",
        "uint256.max",
        "max-supply",
        "maximum supply",
        "max-share",
        "checked-addition boundary",
    )
    conversion_terms = (
        "converttoshares",
        "converttoassets",
        "_converttoshares",
        "_converttoassets",
        "previewdeposit",
        "previewmint",
        "previewwithdraw",
        "previewredeem",
        "maxwithdraw",
        "maxredeem",
        "_decimalsoffset",
        "virtual-share",
        "virtual share",
    )
    return (
        "overflow" in haystack
        and any(term in haystack for term in boundary_terms)
        and any(term in haystack for term in conversion_terms)
    )


def _has_short_delivering_underlying_context(haystack: str) -> bool:
    short_delivery_terms = (
        "fee-on-transfer",
        "fee on transfer",
        "transfer-tax",
        "transfer tax",
        "deflationary",
        "short-deliver",
        "short deliver",
        "short-transferring",
        "delivering less",
        "delivers less",
        "received less",
        "receives less",
        "less than the requested",
        "actual received",
        "assets_received",
        "balance delta",
        "does not measure the vault balance",
        "does not verify the vault balance",
        "does not verify that the vault asset balance",
        "does not verify balance delta",
    )
    transfer_terms = (
        "underlying",
        "_transferin",
        "safetransferfrom",
        "deposit",
        "mint",
        "transferfrom",
    )
    return (
        any(term in haystack for term in short_delivery_terms)
        and any(term in haystack for term in transfer_terms)
    )


def _safe_relative_path(path: str) -> str:
    parts = [
        part
        for part in path.split("/")
        if part not in {"", ".", ".."}
    ]
    return "/".join(parts)


def _slug(value: str, max_len: int = 64) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or "item"
