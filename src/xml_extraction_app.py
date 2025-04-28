import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

st.title("UBL Invoice XML Extractor")

uploaded_files = st.file_uploader(
    "Upload one or more UBL XML invoice files", 
    type="xml", 
    accept_multiple_files=True
)

def extract_invoice_data(xml_file):
    ns = {
        'inv': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    }
    records = []
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError:
        return []
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
        src_fn = xml_file.name if hasattr(xml_file, "name") else "uploaded_file.xml"
        records.append({
            'Description': desc,
            'Quantité':    qty,
            'Poids':       weight,
            'PU':          pu,
            'Total':       total,
            'Designation': desig,
            'SourceFile':  src_fn,
        })
    return records

if uploaded_files:
    all_records = []
    for xml_file in uploaded_files:
        records = extract_invoice_data(xml_file)
        all_records.extend(records)
    if all_records:
        df = pd.DataFrame(all_records)
        st.dataframe(df)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name="xml_out.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No valid invoice lines found in the uploaded files.")
else:
    st.info("Please upload one or more XML files.")