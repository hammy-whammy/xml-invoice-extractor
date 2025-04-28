import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd

# 1) adjust this to your folder
INPUT_FOLDER = r'/Users/hamza.ahmed/Library/CloudStorage/OneDrive-SharedLibraries-JICAP/Drive - 3- Base XML/'
OUTPUT_FILE = 'xml_out.xlsx'

# 2) UBL namespaces
ns = {
    'inv': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}

records = []

xml_files = glob.glob(os.path.join(INPUT_FOLDER, '*.xml'))
total_files = len(xml_files)

for idx, xml_path in enumerate(xml_files, 1):
    print(f"Processing file {idx}/{total_files}: {os.path.basename(xml_path)}")
    # Skip empty files
    if os.path.getsize(xml_path) == 0:
        print(f"  Skipping empty file: {xml_path}")
        continue
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  Skipping invalid XML file: {xml_path} ({e})")
        continue
    
    # for each invoice line
    for line in root.findall('.//cac:InvoiceLine', ns):
        # Description / Libellé
        desc = line.findtext('.//cac:Item/cbc:Description', default='', namespaces=ns)
        # Quantité
        qty  = line.findtext('.//cbc:InvoicedQuantity', default='', namespaces=ns)
        # Poids — try a few common tags
        weight = ''
        for tag in ('GrossWeightMeasure','NetWeightMeasure','WeightMeasure','Weight'):
            w = line.find(f'.//cbc:{tag}', ns)
            if w is not None:
                weight = w.text
                break
        # Prix unitaire (P.U)
        pu     = line.findtext('.//cac:Price/cbc:PriceAmount', default='', namespaces=ns)
        # Prix total (ligne)
        total  = line.findtext('.//cbc:LineExtensionAmount', default='', namespaces=ns)
        # Designation — here drawn from the DespatchLineReference→DocumentReference→ID
        desig  = line.findtext('.//cac:DespatchLineReference/cac:DocumentReference/cbc:ID',
                               default='', namespaces=ns)
        # Source filename
        src_fn = os.path.basename(xml_path)
        
        records.append({
            'Description': desc,
            'Quantité':    qty,
            'Poids':       weight,
            'PU':          pu,
            'Total':       total,
            'Designation': desig,
            'SourceFile':  src_fn,
        })

# build DataFrame and write out
df = pd.DataFrame(records)
df.to_excel(OUTPUT_FILE, index=False)
print(f'Wrote {len(df)} rows to {OUTPUT_FILE}')