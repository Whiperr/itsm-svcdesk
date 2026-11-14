#!/usr/bin/env python3
# ai-generated: 80% - implemented SARIF matching and confusion matrix engine from CI-SPEC.md section 3
import argparse
import json
import re
import sys
import urllib.parse

COURSE_CLASSES = {
    "secret",
    "injection",
    "deserialization",
    "weak-crypto",
    "insecure-transport",
    "path-traversal",
    "ssrf",
    "vulnerable-dependency",
    "misconfiguration",
    "access-control",
}

CLASS_CWES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}

CWE_TO_CLASSES = {}
for _cls, _cwes in CLASS_CWES.items():
    for _cwe in _cwes:
        CWE_TO_CLASSES.setdefault(_cwe, set()).add(_cls)

SEMGREP_ALIASES = {
    "semgrep",
    "semgrep oss",
    "semgrep ce",
    "semgrep community edition",
    "semgrep pro",
}

FIXED_TOOL_NAMES = {"trivy", "grype", "osv-scanner", "gitleaks"}

TRIVY_TAG_MAP = {
    "vulnerability": "vulnerable-dependency",
    "secret": "secret",
    "misconfiguration": "misconfiguration",
}

CWE_RE = re.compile(r"(?<![A-Za-z0-9])[cC][wW][eE]-([0-9]+)")
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")
PEP503_RE = re.compile(r"[-_.]+")


def normalize_tool_id(run: dict) -> str:
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return "unknown"
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return "unknown"
    name = driver.get("name")
    if not isinstance(name, str):
        return "unknown"
    cleaned = name.strip().lower()
    if not cleaned:
        return "unknown"
    if cleaned in FIXED_TOOL_NAMES:
        return cleaned
    if cleaned in SEMGREP_ALIASES:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug if slug else "unknown"


def is_empty_suppression(sup) -> bool:
    if sup is None or sup is False or sup == "":
        return True
    if isinstance(sup, (int, float)) and not isinstance(sup, bool) and sup == 0:
        return True
    if isinstance(sup, (list, dict)) and len(sup) == 0:
        return True
    return False


def is_json_int(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def resolve_path(uri: str, set_root: str):
    decoded = urllib.parse.unquote(uri, encoding="utf-8", errors="replace")
    if decoded.lower().startswith("file://"):
        decoded = decoded[7:]
    if decoded.startswith("./"):
        decoded = decoded[2:]
    parts = decoded.split("/")
    if set_root not in parts:
        return None
    last_idx = len(parts) - 1 - parts[::-1].index(set_root)
    return "/".join(parts[last_idx:])


def extract_lines(phys: dict):
    region = phys.get("region")
    if not isinstance(region, dict):
        return None
    sl = region.get("startLine")
    if not is_json_int(sl) or sl < 1:
        return None
    el = region.get("endLine")
    if is_json_int(el) and el >= sl:
        return (sl, el)
    return (sl, sl)


def get_rule_tags(run: dict, rule_id) -> list[str]:
    if not isinstance(rule_id, str):
        return []
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return []
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return []
    rules = driver.get("rules")
    if not isinstance(rules, list):
        return []
    for r in rules:
        if isinstance(r, dict) and r.get("id") == rule_id:
            props = r.get("properties")
            if isinstance(props, dict) and isinstance(props.get("tags"), list):
                return [t for t in props["tags"] if isinstance(t, str)]
            return []
    return []


def get_result_tags(res: dict) -> list[str]:
    props = res.get("properties")
    if isinstance(props, dict) and isinstance(props.get("tags"), list):
        return [t for t in props["tags"] if isinstance(t, str)]
    return []


def classify_result(tool_id: str, run: dict, res: dict, rule_id) -> set[str]:
    props = res.get("properties")
    if isinstance(props, dict):
        p_cls = props.get("class")
        if isinstance(p_cls, str) and p_cls in COURSE_CLASSES:
            return {p_cls}

    rule_tags = get_rule_tags(run, rule_id)

    if tool_id == "gitleaks":
        return {"secret"}
    if tool_id in {"grype", "osv-scanner"}:
        return {"vulnerable-dependency"}
    if tool_id == "trivy":
        trivy_classes = set()
        for t in rule_tags:
            mapped = TRIVY_TAG_MAP.get(t.lower())
            if mapped:
                trivy_classes.add(mapped)
        if trivy_classes:
            return trivy_classes

    cwe_classes = set()
    for tag in get_result_tags(res) + rule_tags:
        for match in CWE_RE.finditer(tag):
            cwe_num = int(match.group(1))
            cwe_classes.update(CWE_TO_CLASSES.get(cwe_num, ()))
    if cwe_classes:
        return cwe_classes

    return {"other"}


def pep503_norm(name: str) -> str:
    return PEP503_RE.sub("-", name.lower())


def extract_package_tokens(res: dict) -> set[str]:
    msg = res.get("message")
    if not isinstance(msg, dict):
        return set()
    text = msg.get("text")
    if not isinstance(text, str):
        return set()
    tokens = set()
    for m in TOKEN_RE.finditer(text):
        stripped = m.group(0).strip("._-")
        if stripped:
            tokens.add(pep503_norm(stripped))
    return tokens


def evaluate(labels_data: dict, sarif_paths: list[str]) -> dict:
    set_root = labels_data["set"]
    defects = labels_data.get("defects", [])

    tool_state = {}

    for path in sarif_paths:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            continue
        runs = doc.get("runs")
        if not isinstance(runs, list):
            continue

        for run in runs:
            if not isinstance(run, dict):
                continue
            tool_id = normalize_tool_id(run)
            state = tool_state.setdefault(
                tool_id,
                {"matched_defects": set(), "fp_keys": set()},
            )

            results = run.get("results")
            if not isinstance(results, list):
                continue

            for res in results:
                if not isinstance(res, dict):
                    continue

                kind = res.get("kind")
                if kind is not None and not (isinstance(kind, str) and kind == "fail"):
                    continue

                if "suppressions" in res and not is_empty_suppression(res.get("suppressions")):
                    continue

                locs = res.get("locations")
                if not isinstance(locs, list) or len(locs) == 0:
                    continue
                loc0 = locs[0]
                if not isinstance(loc0, dict):
                    continue
                phys = loc0.get("physicalLocation")
                if not isinstance(phys, dict):
                    continue
                art = phys.get("artifactLocation")
                if not isinstance(art, dict):
                    continue
                uri = art.get("uri")
                if not isinstance(uri, str) or len(uri) == 0:
                    continue

                norm_file = resolve_path(uri, set_root)
                if norm_file is None:
                    continue

                rule_id = res.get("ruleId")
                norm_rule_id = rule_id if isinstance(rule_id, str) else None
                lines = extract_lines(phys)
                classes = classify_result(tool_id, run, res, norm_rule_id)
                pkg_tokens = None

                matched_any = False
                for idx, defect in enumerate(defects):
                    if norm_file != defect["file"]:
                        continue
                    d_cls = defect["class"]
                    if d_cls not in classes:
                        continue
                    if d_cls == "vulnerable-dependency":
                        if pkg_tokens is None:
                            pkg_tokens = extract_package_tokens(res)
                        if pep503_norm(defect["package"]) in pkg_tokens:
                            state["matched_defects"].add(idx)
                            matched_any = True
                    else:
                        if lines is not None:
                            if lines[0] <= defect["end_line"] and defect["start_line"] <= lines[1]:
                                state["matched_defects"].add(idx)
                                matched_any = True

                if not matched_any:
                    fp_key = (
                        norm_rule_id,
                        norm_file,
                        lines[0] if lines is not None else None,
                        lines[1] if lines is not None else None,
                    )
                    state["fp_keys"].add(fp_key)

    total_defects = len(defects)
    tools_out = {}
    for tool_id, state in tool_state.items():
        tp = len(state["matched_defects"])
        fp = len(state["fp_keys"])
        fn = total_defects - tp
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
        f1 = round((2 * tp) / (2 * tp + fp + fn), 4) if (2 * tp + fp + fn) > 0 else None
        tools_out[tool_id] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {
        "set": set_root,
        "defects": total_defects,
        "tools": tools_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SARIF scanner outputs against labels.")
    parser.add_argument("--labels", required=True, help="Path to labels.json")
    parser.add_argument("sarif", nargs="+", help="One or more SARIF 2.1.0 files")
    args = parser.parse_args()

    with open(args.labels, "r", encoding="utf-8") as f:
        labels_data = json.load(f)

    result = evaluate(labels_data, args.sarif)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())