import os
import sys
import xml.etree.ElementTree as ET
import pandas as pd
from xml_extraction import INPUT_FOLDER, OUTPUT_FILE

def extract_invoices():
    xml_files = glob.glob(os.path.join(INPUT_FOLDER, '*.xml'))
    total_files = len(xml_files)

    for idx, xml_path in enumerate(xml_files, 1):
        print(f"Processing file {idx}/{total_files}: {os.path.basename(xml_path)}")
        if os.path.getsize(xml_path) == 0:
            print(f"  Skipping empty file: {xml_path}")
            continue
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  Skipping invalid XML file: {xml_path} ({e})")
            continue
        
        records = []
        for line in root.findall('.//cac:InvoiceLine', ns):
            desc = line.findtext('.//cac:Item/cbc:Description', default='', namespaces=ns)
            qty  = line.findtext('.//cbc:InvoicedQuantity', default='', namespaces=ns)
            weight = ''
            for tag in ('GrossWeightMeasure','NetWeightMeasure','WeightMeasure','Weight'):
                w = line.find(f'.//cbc:{tag}', ns)
                if w is not None:
                    weight = w.text
                    break
            pu     = line.findtext('.//cac:Price/cbc:PriceAmount', default='', namespaces=ns)
            total  = line.findtext('.//cbc:LineExtensionAmount', default='', namespaces=ns)
            desig  = line.findtext('.//cac:DespatchLineReference/cac:DocumentReference/cbc:ID',
                                   default='', namespaces=ns)
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

    df = pd.DataFrame(records)
    df.to_excel(OUTPUT_FILE, index=False)
    print(f'Wrote {len(df)} rows to {OUTPUT_FILE}')

if __name__ == "__main__":
    extract_invoices()