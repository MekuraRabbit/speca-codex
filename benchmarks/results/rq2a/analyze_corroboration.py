import json

# Load the summary files
with open('speca_sonnet4/speca_summary.json', 'r') as f:
    sonnet4 = json.load(f)

with open('speca/speca_summary.json', 'r') as f:
    sonnet45 = json.load(f)

with open('speca_deepseek_r1/speca_summary.json', 'r') as f:
    deepseek = json.load(f)

# Sonnet 4 new_tp findings
sonnet4_new_tp = set(sonnet4['new_tp_findings'])
sonnet45_new_tp = set(sonnet45['new_tp_findings'])
deepseek_new_tp = set(deepseek['new_tp_findings'])

print("=" * 80)
print("SONNET 4 NEW_TP FINDINGS: 18 total")
print("=" * 80)
for i, finding in enumerate(sorted(sonnet4_new_tp), 1):
    print(f"{i:2d}. {finding}")

print("\n" + "=" * 80)
print("3 GT DUPLICATE FINDINGS TO REMOVE:")
print("=" * 80)
gt_dups = ['PROP-N2-npd-018', 'PROP-N5-npd-013', 'PROP-N5-npd-017']
for dup in gt_dups:
    in_sonnet4 = dup in sonnet4_new_tp
    print(f"  {dup}: IN SONNET4 new_tp = {in_sonnet4}")

print("\n" + "=" * 80)
print("CROSS-MODEL CORROBORATION ANALYSIS")
print("=" * 80)

# For each Sonnet 4 new_tp finding, check if corroborated by other models
corroborated = []
not_corroborated = []

for finding in sorted(sonnet4_new_tp):
    in_sonnet45 = finding in sonnet45_new_tp
    in_deepseek = finding in deepseek_new_tp
    
    is_corroborated = in_sonnet45 or in_deepseek
    
    if is_corroborated:
        corroborated.append(finding)
        models = []
        if in_sonnet45:
            models.append("Sonnet 4.5")
        if in_deepseek:
            models.append("DeepSeek R1")
        print(f"CORROBORATED: {finding} ({', '.join(models)})")
    else:
        not_corroborated.append(finding)
        print(f"NOT CORROBORATED: {finding}")

print("\n" + "=" * 80)
print("CORROBORATION SUMMARY")
print("=" * 80)
print(f"Total Sonnet 4 new_tp findings: {len(sonnet4_new_tp)}")
print(f"Corroborated by other models: {len(corroborated)}")
print(f"Not corroborated: {len(not_corroborated)}")
print(f"Corroboration percentage: {100 * len(corroborated) / len(sonnet4_new_tp):.1f}%")

print("\n" + "=" * 80)
print("CHECKING 3 GT DUPLICATES FOR CORROBORATION")
print("=" * 80)

gt_dup_corroboration = {}
for dup in gt_dups:
    in_sonnet45 = dup in sonnet45_new_tp
    in_deepseek = dup in deepseek_new_tp
    is_corroborated = in_sonnet45 or in_deepseek
    gt_dup_corroboration[dup] = is_corroborated
    
    if is_corroborated:
        models = []
        if in_sonnet45:
            models.append("Sonnet 4.5")
        if in_deepseek:
            models.append("DeepSeek R1")
        print(f"  {dup}: CORROBORATED ({', '.join(models)})")
    else:
        print(f"  {dup}: NOT CORROBORATED")

print("\n" + "=" * 80)
print("AFTER REMOVING 3 GT DUPLICATES")
print("=" * 80)

# Remove GT dups from corroborated list
remaining_corroborated = [f for f in corroborated if f not in gt_dups]
remaining_not_corroborated = not_corroborated  # These never get removed

new_total = len(sonnet4_new_tp) - 3
new_corroborated_count = len(remaining_corroborated)
new_corroboration_pct = 100 * new_corroborated_count / new_total if new_total > 0 else 0

print(f"Remaining findings: {new_total} (was 18)")
print(f"Corroborated findings: {new_corroborated_count} (was {len(corroborated)})")
print(f"Not corroborated: {len(remaining_not_corroborated)}")
print(f"New corroboration percentage: {new_corroboration_pct:.1f}% (was {100 * len(corroborated) / len(sonnet4_new_tp):.1f}%)")

print("\n" + "=" * 80)
print("FINAL CORROBORATED FINDINGS (after removal):")
print("=" * 80)
for finding in sorted(remaining_corroborated):
    print(f"  {finding}")

print("\n" + "=" * 80)
print("BUG TYPE BREAKDOWN")
print("=" * 80)

# Original breakdown
original_counts = {'NPD': 6, 'MLK': 6, 'UAF': 9}
print(f"Original (21 findings): NPD=6, MLK=6, UAF=9, Total=21")

# Categorize Sonnet 4 new_tp findings
def extract_type(finding):
    if 'npd' in finding:
        return 'NPD'
    elif 'mlk' in finding:
        return 'MLK'
    elif 'uaf' in finding:
        return 'UAF'
    return 'UNKNOWN'

# Count types in remaining findings
remaining_findings = sonnet4_new_tp - set(gt_dups)
type_counts = {'NPD': 0, 'MLK': 0, 'UAF': 0}
for finding in remaining_findings:
    bug_type = extract_type(finding)
    if bug_type in type_counts:
        type_counts[bug_type] += 1

print(f"After removing 3 NPD GT dups: NPD={type_counts['NPD']}, MLK={type_counts['MLK']}, UAF={type_counts['UAF']}, Total={new_total}")

# Verify which types were removed
removed_types = {'NPD': 0, 'MLK': 0, 'UAF': 0}
for dup in gt_dups:
    bug_type = extract_type(dup)
    if bug_type in removed_types:
        removed_types[bug_type] += 1
print(f"Removed findings: NPD={removed_types['NPD']}, MLK={removed_types['MLK']}, UAF={removed_types['UAF']}")

