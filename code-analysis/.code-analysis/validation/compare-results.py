#!/usr/bin/env python3
"""Compare Opus vs Sonnet scanner findings for validation."""

import json
import os
import sys

VALIDATION_DIR = os.path.dirname(os.path.abspath(__file__))

def load_scan_reports(directory):
    """Load all scan report JSONs from a directory."""
    results = {}
    if not os.path.exists(directory):
        return results
    for f in sorted(os.listdir(directory)):
        if not f.endswith('.json'):
            continue
        dim = f.split('-', 3)[-1].replace('.json', '')
        with open(os.path.join(directory, f)) as fh:
            data = json.load(fh)
        results[dim] = data
    return results

def extract_findings(scan_data):
    """Extract finding IDs and severities from scan data."""
    findings = scan_data.get('findings', [])
    return {
        f.get('id', 'unknown'): {
            'severity': f.get('severity', 'unknown'),
            'title': f.get('title', ''),
            'effort': f.get('effort', ''),
        }
        for f in findings
    }

def compute_score(findings_dict):
    """Compute dimension score from findings."""
    c = sum(1 for f in findings_dict.values() if f['severity'] == 'critical')
    h = sum(1 for f in findings_dict.values() if f['severity'] == 'high')
    m = sum(1 for f in findings_dict.values() if f['severity'] == 'medium')
    l = sum(1 for f in findings_dict.values() if f['severity'] == 'low')
    raw = 3*c + 2*h + 1*m + 0.5*l
    return max(1.0, 10 - min(raw, 9))

def main():
    opus_dir = os.path.join(VALIDATION_DIR, 'opus-v080')
    sonnet_dir = os.path.join(VALIDATION_DIR, 'sonnet-v080')

    if not os.path.exists(opus_dir):
        # Fall back to pre-v0.8.0 baseline
        opus_dir = os.path.join(VALIDATION_DIR, 'opus-baseline-pre-v080')
        print("NOTE: Using pre-v0.8.0 Opus baseline (codebase may have changed)")
        print()

    if not os.path.exists(opus_dir) or not os.path.exists(sonnet_dir):
        print(f"ERROR: Missing scan results.")
        print(f"  Opus dir: {opus_dir} ({'exists' if os.path.exists(opus_dir) else 'MISSING'})")
        print(f"  Sonnet dir: {sonnet_dir} ({'exists' if os.path.exists(sonnet_dir) else 'MISSING'})")
        sys.exit(1)

    opus = load_scan_reports(opus_dir)
    sonnet = load_scan_reports(sonnet_dir)

    all_dims = sorted(set(opus.keys()) | set(sonnet.keys()))

    print("=" * 90)
    print(f"{'Dimension':<30} {'Opus':>8} {'Sonnet':>8} {'Delta':>8} {'Opus#':>6} {'Son#':>6} {'Overlap':>8}")
    print("=" * 90)

    total_opus_critical_high = 0
    total_sonnet_critical_high = 0
    missed_critical_high = []

    for dim in all_dims:
        opus_findings = extract_findings(opus.get(dim, {}))
        sonnet_findings = extract_findings(sonnet.get(dim, {}))

        opus_score = compute_score(opus_findings)
        sonnet_score = compute_score(sonnet_findings)
        delta = sonnet_score - opus_score

        opus_ids = set(opus_findings.keys())
        sonnet_ids = set(sonnet_findings.keys())
        overlap = len(opus_ids & sonnet_ids)
        total = len(opus_ids | sonnet_ids)
        overlap_pct = f"{overlap/total*100:.0f}%" if total > 0 else "N/A"

        delta_str = f"{delta:+.1f}"
        status = "OK" if abs(delta) <= 1.0 else "WARN"

        print(f"{dim:<30} {opus_score:>8.1f} {sonnet_score:>8.1f} {delta_str:>8} {len(opus_ids):>6} {len(sonnet_ids):>6} {overlap_pct:>8}  {status}")

        # Track critical+high findings
        for fid, f in opus_findings.items():
            if f['severity'] in ('critical', 'high'):
                total_opus_critical_high += 1
                if fid not in sonnet_findings:
                    missed_critical_high.append((dim, fid, f['title'], f['severity']))

        for fid, f in sonnet_findings.items():
            if f['severity'] in ('critical', 'high'):
                total_sonnet_critical_high += 1

    print("=" * 90)

    # Acceptance criteria
    print()
    print("=== ACCEPTANCE CRITERIA ===")
    print()

    sonnet_caught = total_opus_critical_high - len(missed_critical_high)
    catch_rate = sonnet_caught / total_opus_critical_high * 100 if total_opus_critical_high > 0 else 100
    pass1 = catch_rate >= 90
    print(f"1. Sonnet catches >= 90% of Opus critical+high findings: {catch_rate:.0f}% {'PASS' if pass1 else 'FAIL'}")
    print(f"   (Opus: {total_opus_critical_high}, Sonnet caught: {sonnet_caught}, missed: {len(missed_critical_high)})")

    score_diffs = []
    for dim in all_dims:
        opus_score = compute_score(extract_findings(opus.get(dim, {})))
        sonnet_score = compute_score(extract_findings(sonnet.get(dim, {})))
        score_diffs.append(abs(sonnet_score - opus_score))
    max_diff = max(score_diffs) if score_diffs else 0
    pass2 = max_diff <= 1.0
    print(f"2. Dimension scores within 1.0 point: max diff = {max_diff:.1f} {'PASS' if pass2 else 'FAIL'}")

    pass3 = not any(s == 'critical' for _, _, _, s in missed_critical_high)
    print(f"3. No critical findings missed by Sonnet: {'PASS' if pass3 else 'FAIL'}")

    if missed_critical_high:
        print()
        print("  Missed findings:")
        for dim, fid, title, sev in missed_critical_high:
            print(f"    [{sev}] {dim}: {fid} — {title}")

    print()
    overall = pass1 and pass2 and pass3
    print(f"OVERALL: {'PASS — Sonnet defaults are safe to ship' if overall else 'FAIL — keep inherit as default'}")

    if not overall:
        print()
        print("Recommendation: Revert model-resolution.md scanning default to 'inherit'")
        print("Progressive escalation (Section 6) becomes the primary cost optimization.")


if __name__ == '__main__':
    main()
