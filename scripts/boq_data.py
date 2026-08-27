# boq_data.py — the BoQ fixture DATA, importable without reportlab so the
# offline test suite can cross-validate every rate against rate_benchmarks.csv
# using the same longest-keyword matching as the BigQuery lookup.
#
# Two variants:
#   RAVI  — the golden case: 4 seeded flaws + GST silence (see flags below)
#   CLEAN — the negative-test case: benchmark-aligned rates, full scope,
#           graded/branded specs, sane payment schedule, GST stated.
#           Paired with loan 1002 in draw_schedule.csv (slab, exposure 0.97).

# Item tuple: (section, id, description, qty, unit, rate)

RAVI_ITEMS = [
    ("1. EARTHWORK", "1.1", "Excavation for foundation in ordinary soil incl. disposal", 92, "cum", 285),
    ("", "1.2", "Backfilling with excavated earth, watered and rammed", 55, "cum", 160),
    ("", "1.3", "Sand filling under floors, 100mm", 18, "cum", 1450),
    ("2. FOUNDATION & PLINTH", "2.1", "PCC 1:4:8 with 40mm aggregate below footings", 14, "cum", 5900),
    ("", "2.2", "Size stone masonry in CM 1:6 for foundation", 38, "cum", 4200),
    ("", "2.3", "Plinth beam RCC M20 incl. shuttering", 6.5, "cum", 9800),      # F1 companion
    ("", "2.4", "DPC 50mm CC 1:2:4 with waterproof compound", 42, "sqm", 340),
    ("3. RCC WORK", "3.1", "RCC M25 for columns incl. shuttering & curing", 12.0, "cum", 9800),   # F1
    ("", "3.2", "RCC M25 for roof slab 125mm incl. shuttering", 22.5, "cum", 9800),               # F1
    ("", "3.3", "RCC M20 for lintels and chajjas", 3.8, "cum", 9100),
    ("", "3.4", "RCC M20 for staircase waist slab", 4.2, "cum", 9300),
    ("4. STEEL", "4.1", "Binding wire", 95, "kg", 78),
    ("", "4.2", "TMT bars, cut bent and placed incl. wastage", 4800, "kg", 62), # F3: no grade
    ("5. MASONRY", "5.1", "9\" brick wall in CM 1:6, table-moulded bricks", 118, "cum", 5600),
    ("", "5.2", "4.5\" partition wall in CM 1:4", 240, "sqm", 780),
    ("6. PLASTERING", "6.1", "Internal plaster 12mm CM 1:6", 640, "sqm", 195),
    ("", "6.2", "Ceiling plaster 6mm CM 1:4", 165, "sqm", 175),
    # F2: NO external plaster, NO waterproofing section anywhere
    ("7. FLOORING", "7.1", "Vitrified tiles 600x600 good quality, laid in CM", 152, "sqm", 1150),  # vague brand
    ("", "7.2", "Anti-skid ceramic tiles for toilets", 28, "sqm", 890),
    ("", "7.3", "Granite for kitchen platform, 18mm", 6.5, "sqm", 2900),
    ("", "7.4", "Skirting 100mm vitrified", 118, "rm", 165),
    ("8. DOORS & WINDOWS", "8.1", "Teak wood frame for main door 5\"x3\"", 1, "no", 14500),
    ("", "8.2", "Flush doors 35mm commercial ply, painted", 7, "no", 5200),
    ("", "8.3", "UPVC sliding windows with 5mm glass", 14, "sqm", 3900),
    ("", "8.4", "MS safety grills for windows", 14, "sqm", 1450),
    ("9. ELECTRICAL", "9.1", "Concealed conduiting & wiring per point, branded wire", 68, "pt", 720),  # vague brand
    ("", "9.2", "Modular switches & sockets, good make", 68, "pt", 310),
    ("", "9.3", "DB with MCBs, single phase", 1, "no", 6800),
    ("10. PLUMBING & SANITARY", "10.1", "CPVC concealed water lines per bathroom set", 3, "set", 11500),
    ("", "10.2", "PVC drainage lines 110mm/75mm", 46, "rm", 385),
    ("", "10.3", "EWC with concealed cistern, standard make", 3, "no", 8200),
    ("", "10.4", "Wash basins with pillar taps", 4, "no", 3400),
    ("", "10.5", "OH tank 1000L triple layer with fittings", 1, "no", 9500),
    ("11. PAINTING", "11.1", "Interior emulsion 2 coats over primer & putty", 805, "sqm", 145),
    ("", "11.2", "Exterior weatherproof paint 2 coats", 310, "sqm", 165),
    ("", "11.3", "Enamel on grills and MS work", 42, "sqm", 120),
    ("12. MISC", "12.1", "Kitchen sink SS single bowl with fittings", 1, "no", 4200),
    ("", "12.2", "MS main gate 4'x7' with painting", 1, "no", 18500),
    ("", "12.3", "Site cleaning and debris disposal on completion", 1, "ls", 12000),
    ("", "12.4", "Water & electricity for construction (borne by owner)", 1, "ls", 0),
]

RAVI_PAYMENT = [
    ("Advance on agreement signing", "20%"),   # F4: 20+15+10 = 45% before slab
    ("On completion of foundation", "15%"),
    ("On completion of plinth", "10%"),
    ("On casting of roof slab", "20%"),
    ("On completion of brickwork & roof", "20%"),
    ("On finishing & handover", "15%"),
]

RAVI_META = {
    "firm": "SRI SAI CONSTRUCTIONS",
    "client": "Mr. Ravi Kumar",
    "site": "Plot 47, Kompally, Hyderabad",
    "area": "1800 sqft",
    "terms": ("Terms: Rates valid 30 days. Any item not listed above will be "
              "charged extra as per actuals. Owner to provide water and "
              "electricity."),
    # deliberately NO GST clause, NO exclusions column, NO penalty clause
    "out": "fixtures/sample_boq.pdf",
}

# ---------------------------------------------------------------- clean case
# Every benchmarked rate within ±15% of rate_benchmarks.csv, full expected
# scope, grades/brands/IS codes named, 25% before slab, GST stated.

CLEAN_ITEMS = [
    ("1. EARTHWORK", "1.1", "Excavation for foundation in ordinary soil incl. disposal", 88, "cum", 260),
    ("", "1.2", "Backfilling with excavated earth, watered and rammed", 52, "cum", 150),
    ("", "1.3", "Sand filling under floors, 100mm", 17, "cum", 1400),
    ("2. FOUNDATION & PLINTH", "2.1", "PCC 1:4:8 with 40mm aggregate below footings", 13, "cum", 5800),
    ("", "2.2", "Size stone masonry in CM 1:6 for foundation", 36, "cum", 4100),
    ("", "2.3", "Plinth beam RCC M20 incl. shuttering", 6.0, "cum", 8300),
    ("", "2.4", "DPC 50mm CC 1:2:4 with waterproof compound", 40, "sqm", 330),
    ("", "2.5", "Anti-termite treatment to foundation & plinth per IS 6313", 180, "sqm", 95),
    ("3. RCC WORK", "3.1", "RCC M25 for columns incl. shuttering & curing", 11.5, "cum", 8200),
    ("", "3.2", "RCC M25 for roof slab 125mm incl. shuttering", 21.5, "cum", 8250),
    ("", "3.3", "RCC M20 for lintels and chajjas", 3.6, "cum", 7800),
    ("", "3.4", "RCC M20 for staircase waist slab", 4.0, "cum", 8200),
    ("4. STEEL", "4.1", "Binding wire", 90, "kg", 78),
    ("", "4.2", "TMT bars Fe500 per IS 1786, cut bent and placed incl. wastage", 4600, "kg", 76),
    ("5. MASONRY", "5.1", "9\" brick wall in CM 1:6, table-moulded bricks", 112, "cum", 5500),
    ("", "5.2", "4.5\" partition wall in CM 1:4", 228, "sqm", 750),
    ("6. PLASTERING", "6.1", "Internal plaster 12mm CM 1:6", 610, "sqm", 190),
    ("", "6.2", "Ceiling plaster 6mm CM 1:4", 158, "sqm", 170),
    ("", "6.3", "External plaster 18mm CM 1:6, double coat", 295, "sqm", 250),
    ("", "6.4", "Terrace waterproofing with APP membrane incl. protection screed", 155, "sqm", 640),
    ("7. FLOORING", "7.1", "Vitrified tiles 600x600, Kajaria or Somany, laid in CM", 145, "sqm", 1100),
    ("", "7.2", "Anti-skid ceramic tiles for toilets, Kajaria", 26, "sqm", 850),
    ("", "7.3", "Granite for kitchen platform, 18mm, Tan Brown", 6.0, "sqm", 2800),
    ("", "7.4", "Skirting 100mm, matching floor tiles", 112, "rm", 155),
    ("8. DOORS & WINDOWS", "8.1", "Seasoned teak wood frame for main door 5\"x3\"", 1, "no", 14500),
    ("", "8.2", "Flush doors 35mm BWR grade, Century or Greenply, painted", 7, "no", 5000),
    ("", "8.3", "UPVC sliding windows with 5mm glass, Fenesta profile", 13, "sqm", 3750),
    ("", "8.4", "MS safety grills for windows, primer + enamel", 13, "sqm", 1400),
    ("9. ELECTRICAL", "9.1", "Concealed conduiting & wiring per point, Finolex FR copper", 64, "pt", 690),
    ("", "9.2", "Modular switches & sockets, Anchor Roma", 64, "pt", 310),
    ("", "9.3", "DB with MCBs, single phase, Havells", 1, "no", 6800),
    ("10. PLUMBING & SANITARY", "10.1", "CPVC concealed water lines per bathroom set, Astral pipes", 3, "set", 11200),
    ("", "10.2", "PVC drainage lines 110mm/75mm, Supreme", 44, "rm", 385),
    ("", "10.3", "EWC with concealed cistern, Hindware", 3, "no", 8200),
    ("", "10.4", "Wash basins with pillar taps, Cera", 4, "no", 3400),
    ("", "10.5", "OH tank 1000L triple layer, Sintex, with fittings", 1, "no", 9500),
    ("11. PAINTING", "11.1", "Interior emulsion 2 coats over primer & putty, Asian Paints", 780, "sqm", 140),
    ("", "11.2", "Exterior weatherproof paint 2 coats, Apex", 295, "sqm", 155),
    ("", "11.3", "Enamel on grills and MS work", 40, "sqm", 120),
    ("12. MISC", "12.1", "Kitchen sink SS single bowl, Nirali, with fittings", 1, "no", 4200),
    ("", "12.2", "MS main gate 4'x7' with painting", 1, "no", 18500),
    ("", "12.3", "Site cleaning and debris disposal on completion", 1, "ls", 12000),
    ("", "12.4", "Water & electricity for construction (borne by owner)", 1, "ls", 0),
]

CLEAN_PAYMENT = [
    ("Advance on agreement signing", "10%"),   # 10+10+5 = 25% before slab
    ("On completion of foundation", "10%"),
    ("On completion of plinth", "5%"),
    ("On casting of roof slab", "25%"),
    ("On completion of brickwork & roof", "30%"),
    ("On finishing & handover", "20%"),
]

CLEAN_META = {
    "firm": "SRI LAKSHMI BUILDERS",
    "client": "Mrs. Ananya Rao",
    "site": "Plot 12, Miyapur, Hyderabad",
    "area": "1750 sqft",
    "terms": ("Terms: Rates valid 30 days and are INCLUSIVE of GST @ 18% "
              "(works contract). Scope limited to items listed; any variation "
              "only via written change order signed by both parties. Owner to "
              "provide water and electricity."),
    "out": "fixtures/clean_boq.pdf",
}

VARIANTS = {
    "ravi": (RAVI_ITEMS, RAVI_PAYMENT, RAVI_META),
    "clean": (CLEAN_ITEMS, CLEAN_PAYMENT, CLEAN_META),
}
