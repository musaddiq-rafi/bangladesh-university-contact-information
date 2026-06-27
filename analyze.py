"""Analyze the current scraper results."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

with open("output/llm_results_pass1.json", encoding="utf-8") as f:
    d = json.load(f)

total = len(d)
fetch_failed = [x for x in d if x.get("notes") == "Fetch failed"]
found = [x for x in d if x.get("registrar_email") or x.get("cse_dept_email")]
notfound = [x for x in d if not x.get("registrar_email") and not x.get("cse_dept_email") and x.get("notes") != "Fetch failed"]

print(f"=== PASS 1 RESULTS ===")
print(f"Total: {total}")
print(f"  Found emails: {len(found)}")
print(f"  Fetch failed: {len(fetch_failed)}")
print(f"  No emails (fetched ok): {len(notfound)}")
print()

print("=== FETCH FAILED ===")
for x in fetch_failed:
    acr = x.get("acronym", "")
    web = x.get("website") or "NO_URL"
    print(f"  {acr:12s} {web}")

print()
print("=== NO EMAILS FOUND (pages were fetched) ===")
for x in notfound:
    acr = x.get("acronym", "")
    web = x.get("website") or "NO_URL"
    src = x.get("email_source", "")
    cse_url = x.get("cse_dept_url") or ""
    notes = x.get("notes", "")
    print(f"  {acr:12s} src={src:20s} cse_url={cse_url[:50]}")

print()
print("=== FOUND EMAILS ===")
for x in found:
    acr = x.get("acronym", "")
    re_ = x.get("registrar_email") or "-"
    ce = x.get("cse_dept_email") or "-"
    he = x.get("cse_dept_head_email") or "-"
    print(f"  {acr:12s} reg={re_:35s} cse={ce:35s} head={he}")

# Also check pass2
try:
    with open("output/llm_results_pass2.json", encoding="utf-8") as f:
        p2 = json.load(f)
    p2_found = [x for x in p2 if x.get("cse_dept_email") or x.get("cse_dept_head_email")]
    print(f"\n=== PASS 2 RESULTS ===")
    print(f"Total pass2: {len(p2)}, Found CSE emails: {len(p2_found)}")
    for x in p2_found:
        print(f"  {x.get('acronym',''):12s} cse={x.get('cse_dept_email','-')} head={x.get('cse_dept_head_email','-')}")
except:
    print("\nNo pass 2 results found")
