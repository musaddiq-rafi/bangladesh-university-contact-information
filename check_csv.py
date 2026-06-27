import csv, sys
sys.stdout.reconfigure(encoding='utf-8')
with open('data/university_of_bangladesh.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    no_url = []
    dup_acr = {}
    for row in reader:
        acr = row['Acronym']
        web = row.get('Website', '').strip()
        name = row['University']
        if not web:
            no_url.append(f'  {acr:12s} {name}')
        if acr in dup_acr:
            dup_acr[acr].append(name)
        else:
            dup_acr[acr] = [name]
    print('=== NO WEBSITE ===')
    for n in no_url:
        print(n)
    print()
    print('=== DUPLICATE ACRONYMS ===')
    for acr, names in dup_acr.items():
        if len(names) > 1:
            print(f'  {acr}: {names}')
