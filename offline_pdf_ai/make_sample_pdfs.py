# Generates the 10 fictional "Lakeview Residences" sample PDFs. Needs: pip install reportlab
import random
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
random.seed(4)
ss=getSampleStyleSheet()
filler=["The contractor shall coordinate all works with the site engineer and maintain daily records of progress, labour and materials delivered to site.",
"All dimensions are in millimetres unless noted otherwise and shall be verified on site before fabrication begins.",
"Materials not conforming to the approved samples shall be removed from site at the contractor's cost within seven days of notice.",
"Drawings shall be read together with the structural, electrical and plumbing drawings, and any discrepancy shall be reported in writing.",
"The client reserves the right to vary the quantities of any item without any change in the quoted unit rates.",
"Workmanship shall be of the best quality and shall comply with the relevant Indian Standard codes of practice.",
"Scaffolding shall be double-tied, inspected weekly and certified safe before any work at height is carried out."]
docs={
"01_Lakeview_Tender_Specification.pdf":("Tender Specification - Lakeview Residences",{}),
"02_Structural_Design_Basis.pdf":("Structural Design Basis Report",{3:"The basic wind speed adopted for design is 44 metres per second for the site location, with terrain category 2. Seismic zone III has been considered with an importance factor of 1.2 for the residential towers."}),
"03_MEP_Services_Brief.pdf":("MEP Services Design Brief",{2:"Domestic water storage is planned at 135 litres per person per day. The overhead tank on each tower holds one day of demand plus fire reserve."}),
"04_Fire_Safety_Report.pdf":("Fire and Life Safety Report - Tower B",{9:"Each residential tower is served by two enclosed staircases. The minimum clear width of each fire escape staircase shall be 1500 mm, measured between the handrail and the wall, and no landing shall be narrower than the flight it serves. Fire doors to the staircase shall be self-closing with a rating of 120 minutes. The maximum travel distance to the nearest exit shall not exceed 30 metres."}),
"05_Landscape_Design_Notes.pdf":("Landscape Design Notes",{4:"Native species such as neem, pongamia and bougainvillea are selected for low water demand. Drip irrigation is provided to all planters."}),
"06_Site_Meeting_Minutes_Aug.pdf":("Site Meeting Minutes - August",{2:"The client agreed to change the lobby flooring from granite to large-format vitrified tiles to save cost."}),
"07_Interior_Finishes_Schedule.pdf":("Interior Finishes Schedule",{5:"Bathroom walls receive ceramic tiles up to a height of 2100 mm; kitchens receive a 600 mm high backsplash above the counter."}),
"08_Contract_General_Conditions.pdf":("General Conditions of Contract",{6:"The defects liability period is twelve months from the date of practical completion. Retention money of five percent is released at the end of this period."}),
"09_Energy_Compliance_Report.pdf":("Energy Conservation Compliance Report",{3:"The roof assembly achieves a U-value of 0.33 W per square metre kelvin using 75 mm extruded polystyrene insulation."}),
"10_Parking_and_Traffic_Study.pdf":("Parking and Traffic Study",{2:"A total of 312 car parking spaces are provided across two basement levels, including 8 accessible bays near the lift cores."}),
}
for fn,(title,special) in docs.items():
    story=[Paragraph(title,ss["Title"]),Paragraph("Sample project document - Lakeview Residences (fictional)",ss["Italic"])]
    npages=random.randint(6,14)
    for p in range(1,npages+1):
        story.append(Paragraph(f"Section {p}",ss["Heading2"]))
        for _ in range(4):
            story.append(Paragraph(" ".join(random.sample(filler,3)),ss["BodyText"]))
            story.append(Spacer(1,6))
        if p in special:
            story.append(Paragraph(special[p],ss["BodyText"]))
        for _ in range(2):
            story.append(Paragraph(" ".join(random.sample(filler,3)),ss["BodyText"]))
        story.append(PageBreak())
    SimpleDocTemplate(f"sample_pdfs/{fn}",pagesize=A4).build(story)
print("done")
