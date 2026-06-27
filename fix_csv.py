"""Fix CSV with exact verified website mapping."""
import sys, csv
sys.stdout.reconfigure(encoding="utf-8")

path = "D:\\Development\\bd_uni_contact_info\\data\\university_of_bangladesh.csv"

# Read all rows
rows = []
with open(path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    for row in reader:
        rows.append(row)

# EXACT mapping: University name -> website (from user's UGC list)
EXACT = {
    "University of Rajshahi": "https://www.ru.ac.bd",
    "University of Dhaka": "https://www.du.ac.bd",
    "University of Chittagong": "https://www.cu.ac.bd",
    "University of Barisal": "https://www.bu.ac.bd",
    "Sheikh Hasina University": "https://www.shu.edu.bd",
    "Rabindra University, Bangladesh": "https://www.rub.ac.bd",
    "Khulna University": "https://www.ku.ac.bd",
    "Jatiya Kabi Kazi Nazrul Islam University": "https://www.jkkniu.edu.bd",
    "Jahangirnagar University": "https://www.juniv.edu",
    "Jagannath University": "https://www.jnu.ac.bd",
    "Islamic University, Bangladesh": "https://www.iu.ac.bd",
    "Comilla University": "https://www.cou.ac.bd",
    "Begum Rokeya University": "https://www.brur.ac.bd",
    "Bangladesh University of Professionals": "https://www.bup.edu.bd",
    "Bangabandhu Sheikh Mujib Medical University": "https://www.bsmmu.ac.bd",
    "Chittagong Medical University": "https://www.cmu.edu.bd",
    "Rajshahi Medical University": "https://www.rmu.ac.bd",
    "Sylhet Medical University": "https://www.smu.edu.bd",
    "Sheikh Hasina Medical University": "https://www.shmu.ac.bd",
    "Shahjalal University of Science and Technology": "https://www.sust.edu",
    "Hajee Mohammad Danesh Science & Technology University": "https://www.hstu.ac.bd",
    "Mawlana Bhashani Science and Technology University": "https://www.mbstu.ac.bd",
    "Patuakhali Science and Technology University": "https://www.pstu.ac.bd",
    "Noakhali Science and Technology University": "https://www.nstu.edu.bd",
    "Jashore University of Science and Technology": "https://www.just.edu.bd",
    "Pabna University of Science and Technology": "https://www.pust.ac.bd",
    "Bangabandhu Sheikh Mujibur Rahman Science and Technology University": "https://www.bsmrstu.edu.bd",
    "Rangamati Science and Technology University": "https://www.rmstu.ac.bd",
    "Bangamata Sheikh Fojilatunnesa Mujib Science & Technology University": "https://www.bsfmstu.ac.bd",
    "Chandpur Science and Technology University": "https://www.cstu.ac.bd",
    "Sunamganj Science and Technology University": "https://www.sstu.ac.bd",
    "Bogra Science and Technology University": "https://bstu.ac.bd",
    "Lakshmipur Science and Technology University": "",
    "Bangladesh Agricultural University": "https://www.bau.edu.bd",
    "Bangabandhu Sheikh Mujibur Rahman Agricultural University": "https://www.bsmrau.edu.bd",
    "Sher-e-Bangla Agricultural University": "https://www.sau.edu.bd",
    "Sylhet Agricultural University": "https://www.sau.ac.bd",
    "Khulna Agricultural University": "https://www.kau.edu.bd",
    "Habiganj Agricultural University": "https://www.hau.ac.bd",
    "Kurigram Agricultural University": "https://www.kuriau.edu.bd",
    "Bangladesh University of Engineering & Technology": "https://www.buet.ac.bd",
    "Khulna University of Engineering & Technology": "https://www.kuet.ac.bd",
    "Chittagong University of Engineering & Technology": "https://www.cuet.ac.bd",
    "Rajshahi University of Engineering & Technology": "https://www.ruet.ac.bd",
    "Dhaka University of Engineering & Technology": "https://www.duet.ac.bd",
    "Mymensingh Engineering College.": "https://www.mec.edu",
    "Sylhet Engineering College.": "https://www.sec.ac.bd",
    "Faridpur Engineering College": "https://www.fec.edu.bd",
    "Barisal Engineering College.": "https://www.bec.org",
    "Chittagong Veterinary and Animal Sciences University": "https://cvasu.ac.bd",
    "Bangladesh University of Textiles": "https://www.butex.edu.bd",
    "Bangabandhu Sheikh Mujibur Rahman Maritime University": "https://www.bsmrmu.edu.bd",
    "Bangabandhu Sheikh Mujibur Rahman Digital University": "https://www.bdu.gov.bd",
    "Bangabandhu Sheikh Mujibur Rahman Aviation and Aerospace University": "https://www.bsmraau.ac.bd",
    "Bangladesh Open University": "https://www.bou.ac.bd",
    "National University Bangladesh": "https://www.nu.edu.bd",
    "Islamic Arabic University": "https://www.iau.edu.bd",
    "International University of Business Agriculture and Technology": "https://www.iubat.edu",
    "North South University": "https://www.northsouth.edu",
    "Independent University, Bangladesh": "https://www.iub.edu.bd",
    "Ahsanullah University of Science and Technology": "https://www.aust.edu",
    "American International University-Bangladesh": "https://www.aiub.edu",
    "East West University": "https://www.ewubd.edu",
    "University of Asia Pacific (Bangladesh)": "https://www.uap-bd.edu",
    "Gono Bishwabidyalay": "https://www.gonouniversity.edu.bd",
    "People's University of Bangladesh": "https://www.pub.ac.bd",
    "Queens University": "",
    "Asian University for Women": "https://www.auw.edu.bd",
    "Asian University for Women": "https://www.auw.edu.bd",
    "Dhaka International University": "https://www.diu.ac",
    "Manarat International University": "https://www.manarat.ac.bd",
    "BRAC University": "https://www.bracu.ac.bd",
    "Bangladesh University": "https://www.bu.edu.bd",
    "Leading University": "https://www.lus.ac.bd",
    "BGC Trust University Bangladesh": "https://www.bgctub.ac.bd",
    "Sylhet International University": "https://www.siu.edu.bd",
    "University of Development Alternative": "https://www.uoda.edu.bd",
    "Premier University, Chittagong": "https://www.puc.ac.bd",
    "Southeast University": "https://www.seu.edu.bd",
    "Daffodil International University": "https://www.daffodilvarsity.edu.bd",
    "Stamford University Bangladesh": "https://www.stamforduniversity.edu.bd",
    "State University of Bangladesh": "https://www.sub.ac.bd",
    "City University, Bangladesh": "https://www.cityuniversity.ac.bd",
    "Prime University": "https://www.primeuniversity.edu.bd",
    "Northern University of Bangladesh": "https://www.nub.ac.bd",
    "Southern University, Bangladesh": "https://www.southern.edu.bd",
    "Green University of Bangladesh": "https://www.green.edu.bd",
    "Pundra University of Science & Technology": "https://www.pundrauniversity.ac.bd",
    "World University of Bangladesh": "https://www.wub.edu.bd",
    "Shanto-Mariam University of Creative Technology": "https://www.smuct.ac.bd",
    "The Millennium University": "https://www.themillenniumuniversity.edu.bd",
    "Eastern University, Bangladesh": "https://www.easternuni.edu.bd",
    "Metropolitan University": "https://www.metrouni.edu.bd",
    "Uttara University": "https://www.uttarauniversity.edu.bd",
    "United International University": "https://www.uiu.ac.bd",
    "University of South Asia, Bangladesh": "https://www.southasiauni.ac.bd",
    "Victoria University of Bangladesh": "https://www.vub.edu.bd",
    "Bangladesh University of Business & Technology (BUBT)": "https://www.bubt.edu.bd",
    "University of Information Technology and Sciences": "https://www.uits.edu.bd",
    "Primeasia University": "https://www.primeasia.edu.bd",
    "Royal University of Dhaka": "https://www.royal.edu.bd",
    "University of Liberal Arts Bangladesh": "https://www.ulab.edu.bd",
    "Atish Dipankar University of Science & Technology": "https://www.adust.edu.bd",
    "Bangladesh Islami University": "https://www.biu.ac.bd",
    "ASA University Bangladesh": "https://www.asaub.edu.bd",
    "East Delta University": "https://www.eastelta.edu.bd",
    "BGMEA University of Fashion & Technology": "https://www.buft.edu.bd",
    "North East University Bangladesh": "https://www.neub.edu.bd",
    "First Capital University Of Bangladesh": "https://www.fcub.edu.bd",
    "Ishakha International University": "https://www.ishakha.edu.bd",
    "North Western University, Bangladesh": "https://www.nwu.ac.bd",
    "Khwaja Yunus Ali University": "https://www.kyau.edu.bd",
    "Sonargaon University": "https://www.su.edu.bd",
    "Feni University": "https://www.feniuniversity.ac.bd",
    "Britannia University": "https://www.britannia.edu.bd",
    "Port City International University": "https://www.portcity.edu.bd",
    "Bangladesh University of Health Sciences": "https://www.buhs.ac.bd",
    "Chittagong Independent University (CIU)": "https://www.ciu.edu.bd",
    "Notre Dame University Bangladesh": "https://www.ndub.edu.bd",
    "Times University, Bangladesh": "https://www.timesuniversitybd.com",
    "North Bengal International University": "https://www.nbiu.edu.bd",
    "Fareast International University": "https://www.fiu.edu.bd",
    "Rajshahi Science & Technology University": "https://www.rstu.edu.bd",
    "Cox's Bazar International University": "https://www.cbiu.ac.bd",
    "Ranada Prasad Shaha University": "https://www.rpsu.edu.bd",
    "German University Bangladesh": "https://www.gub.edu.bd",
    "Global University Bangladesh": "https://www.globaluniversity.edu.bd",
    "CCN University of Science & Technology": "https://www.ccnust.ac.bd",
    "Bangladesh Army University of Science and Technology (BAUST), Saidpur": "https://www.baust.edu.bd",
    "Bangladesh Army University of Engineering and Technology (BAUET), Qadirabad": "https://www.bauet.ac.bd",
    "Bangladesh Army International University of Science & Technology": "https://www.baiust.ac.bd",
    "The International University of Scholars": "https://www.ius.edu.bd",
    "Canadian University of Bangladesh": "https://www.cub.edu.bd",
    "N.P.I University of Bangladesh": "https://www.npiub.edu.bd",
    "Northern University of Business & Technology, Khulna": "https://www.nubtkhulna.ac.bd",
    "Rabindra Maitree University, Kushtia": "",
    "University of Creative Technology Chittagong": "https://www.uctc.edu.bd",
    "Central University of Science and Technology": "https://www.cust.edu.bd",
    "Tagore University of Creative Arts": "https://www.tuca.edu.bd",
    "University of Global Village": "https://www.ugv.edu.bd",
    "Anwer Khan Modern University": "https://www.akmu.edu.bd",
    "ZNRF University of Management Sciences": "https://www.zums.edu.bd",
    "Ahsania Mission University of Science and Technology": "https://www.amust.ac.bd",
    "Khulna Khan Bahadur Ahsanullah University": "https://www.kkbau.ac.bd",
    "Bandarban University": "https://www.bubban.ac.bd",
    "Trust University, Barishal": "https://www.trustuniversity.edu.bd",
    "International Standard University": "https://www.isu.ac.bd",
    "University of Brahmanbaria": "https://www.uob.edu.bd",
    "University of Skill Enrichment and Technology": "https://www.uset.ac.bd",
    "R.T.M Al-Kabir Technical University": "https://www.rtm-aktu.edu.bd",
    "Dr. Momtaz Begum University of Science and Technology": "https://www.must.ac.bd",
    "Chattogram BGMEA University of Fashion and Technology": "https://www.cbuft.edu.bd",
    "Bangladesh Army University of Science and Technology, Khulna": "https://www.baustkhulna.ac.bd",
    "Teesta University, Rangpur": "https://www.teestauniversity.ac.bd",
    "International Islami University of Science and Technology Bangladesh": "https://www.iiustb.ac.bd",
    "Lalon University of Science and Arts": "https://lusa.ac.bd",
    "Islamic University of Technology": "https://www.iutoic-dhaka.edu",
    "Asian University for Women": "https://www.auw.edu.bd",
    "South Asian University": "https://www.southasianuniversity.org",
    "Bangladesh Maritime University": "https://bmu.edu.bd",
    "University of Frontier Technology, Bangladesh": "https://www.uftb.ac.bd",
    "Netrokona University": "https://www.shu.edu.bd",
    "Aviation And Aerospace University, Bangladesh": "https://www.aaub.edu.bd",
    "Khulna Medical University, Khulna": "https://www.shmu.ac.bd",
    "Pirojpur Science & Technology University": "https://www.prstu.ac.bd",
    "Naogaon University": "",
    "Meherpur University": "",
    "Dhaka Central University": "",
    "Thakurgaon University": "",
    "European University of Bangladesh": "",
    "Hamdard University Bangladesh": "https://www.hamdarduniversity.edu.bd",
    "ZH Sikder University of Science & Technology": "https://www.zhsust.edu.bd",
    "Bangabandhu Sheikh Mujibur Rahman University": "https://www.bsmrau.edu.bd",
    "Exim Bank Agricultural University Bangladesh": "",
    "Rabindra University, Bangladesh": "https://www.rub.ac.bd",
    "Varendra University": "https://www.vu.edu.bd",
    "IBAIS University": "",
    "Presidency University": "https://www.pu.edu.bd",
    "University of Comilla": "",
    "Sheikh Fazilatunnesa Mujib University": "",
    "America Bangladesh University": "",
}

# Update Website column with exact mapping
updated = 0
for row in rows:
    name = row["University"]
    if name in EXACT:
        row["Website"] = EXACT[name]
        updated += 1

# Write back
with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

# Verify
with open(path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    total = 0
    found = 0
    missing = []
    for row in reader:
        total += 1
        if row.get("Website"):
            found += 1
        else:
            missing.append(f"  {row['Acronym']:12s} {row['University']}")

print(f"Total: {total}, With website: {found}, Missing: {total - found}")
print("\nMissing websites:")
for m in missing:
    print(m)
