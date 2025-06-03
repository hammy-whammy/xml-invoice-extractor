import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io
import zipfile
import os
import tempfile

st.title("UBL Invoice XML Extractor")

st.markdown("""
**Instructions:**
- Please upload a ZIP file containing all the XML files in your invoice folder.
- Only files with a `.xml` extension inside the ZIP will be processed; other files will be ignored.
- For large numbers of files, ensure the ZIP file is not too large to avoid network errors.
""")

# Add extraction mode selection
extraction_mode = st.radio(
    "Choose extraction mode:",
    ["Detailed Line Items", "Total Amounts Only (TTC & HT)"],
    help="Select 'Detailed Line Items' for full invoice line data or 'Total Amounts Only' for just TTC and HT totals"
)

# Display mode-specific information
if extraction_mode == "Detailed Line Items":
    st.info("📋 **Detailed Mode**: Extracts all invoice line items including description, quantity, weight, unit price, total, and designation.")
else:
    st.info("💰 **Total Amounts Mode**: Extracts only the invoice number, total HT (before tax), total TTC (including tax), tax amount, and currency.")

uploaded_file = st.file_uploader(
    "Upload a ZIP file containing UBL XML invoice files",
    type=['zip'], # Specify ZIP type for client-side filtering
    accept_multiple_files=False
)

def extract_data_from_xml_root(root, ns, source_filename):
    """Extracts invoice line data from a parsed XML root."""
    records = []
    for line in root.findall('.//cac:InvoiceLine', ns):
        desc = line.findtext('.//cac:Item/cbc:Description', default='', namespaces=ns)
        qty  = line.findtext('.//cbc:InvoicedQuantity', default='', namespaces=ns)
        weight = ''
        # Iterate over common weight tags
        for tag_name in ['GrossWeightMeasure', 'NetWeightMeasure', 'WeightMeasure', 'Weight']:
            weight_element = line.find(f'.//cbc:{tag_name}', ns)
            if weight_element is not None and weight_element.text:
                weight = weight_element.text
                break
        pu     = line.findtext('.//cac:Price/cbc:PriceAmount', default='', namespaces=ns)
        total  = line.findtext('.//cbc:LineExtensionAmount', default='', namespaces=ns)
        desig  = line.findtext('.//cac:DespatchLineReference/cac:DocumentReference/cbc:ID',
                               default='', namespaces=ns)
        records.append({
            'Description': desc,
            'Quantité':    qty,
            'Poids':       weight,
            'PU':          pu,
            'Total':       total,
            'Designation': desig,
            'SourceFile':  source_filename,
        })
    return records

def extract_totals_from_xml_root(root, ns, source_filename):
    """Extracts only total amounts (TTC and HT) from a parsed XML root."""
    # Extract invoice number for identification
    invoice_number = root.findtext('.//cbc:ID', default='', namespaces=ns)
    
    # Extract total HT (before tax) - commonly found in LegalMonetaryTotal/LineExtensionAmount
    total_ht = root.findtext('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount', default='', namespaces=ns)
    
    # Extract total TTC (including tax) - commonly found in LegalMonetaryTotal/TaxInclusiveAmount or PayableAmount
    total_ttc = root.findtext('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', default='', namespaces=ns)
    if not total_ttc:
        total_ttc = root.findtext('.//cac:LegalMonetaryTotal/cbc:PayableAmount', default='', namespaces=ns)
    
    # Extract tax amount
    tax_amount = root.findtext('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', default='', namespaces=ns)
    if not tax_amount:
        tax_amount = root.findtext('.//cac:TaxTotal/cbc:TaxAmount', default='', namespaces=ns)
    
    # Extract currency if available
    currency = ''
    # First try to get from DocumentCurrencyCode (most reliable)
    currency = root.findtext('.//cbc:DocumentCurrencyCode', default='', namespaces=ns)
    
    # If not found, try to get from currencyID attributes in monetary amounts
    if not currency:
        for xpath in [
            './/cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount',
            './/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', 
            './/cac:LegalMonetaryTotal/cbc:LineExtensionAmount',
            './/cac:LegalMonetaryTotal/cbc:PayableAmount',
            './/cac:TaxTotal/cbc:TaxAmount'
        ]:
            currency_element = root.find(xpath, ns)
            if currency_element is not None and 'currencyID' in currency_element.attrib:
                currency = currency_element.attrib['currencyID']
                break
    
    record = {
        'Invoice Number': invoice_number,
        'Total HT': total_ht,
        'Total TTC': total_ttc,
        'Tax Amount': tax_amount,
        'Currency': currency,
        'SourceFile': source_filename,
    }
    
    return [record] if any([total_ht, total_ttc]) else []

if uploaded_file:
    st.info("ZIP file uploaded. Extracting contents...")

    # Create a temporary directory to extract the ZIP file
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Collect all XML files from the extracted contents
            xml_files_to_process = []
            for root_dir, _, files in os.walk(temp_dir):
                for file in files:
                    # Filter out hidden files (e.g., macOS AppleDouble files starting with '._')
                    if not file.lower().startswith('._') and file.lower().endswith('.xml'):
                        xml_files_to_process.append(os.path.join(root_dir, file))

            if not xml_files_to_process:
                st.warning("No XML files found in the uploaded ZIP file. Please ensure the ZIP contains valid XML files.")
            else:
                st.write(f"Attempting to process {len(xml_files_to_process)} XML file(s)...")

                all_records = []
                successfully_parsed_files = []
                failed_to_parse_files = [] # Stores (filename, error_message)
                files_with_no_invoice_lines = []

                # Define namespaces here to be used by extract_data_from_xml_root
                ns = {
                    'inv': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
                    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                }

                progress_bar = st.progress(0)

                for i, xml_file_path in enumerate(xml_files_to_process):
                    file_name = os.path.basename(xml_file_path)
                    try:
                        tree = ET.parse(xml_file_path)
                        root = tree.getroot()

                        # Choose extraction function based on selected mode
                        if extraction_mode == "Detailed Line Items":
                            records_from_file = extract_data_from_xml_root(root, ns, file_name)
                        else:  # Total Amounts Only
                            records_from_file = extract_totals_from_xml_root(root, ns, file_name)

                        if records_from_file:
                            all_records.extend(records_from_file)
                        else:
                            if extraction_mode == "Detailed Line Items":
                                files_with_no_invoice_lines.append(file_name)
                            else:
                                files_with_no_invoice_lines.append(file_name)

                        successfully_parsed_files.append(file_name)

                    except ET.ParseError as e:
                        failed_to_parse_files.append((file_name, str(e)))
                    except Exception as e: # Catch other potential errors during file processing
                        failed_to_parse_files.append((file_name, f"An unexpected error occurred: {str(e)}"))

                    progress_bar.progress((i + 1) / len(xml_files_to_process))

                progress_bar.empty() # Clear the progress bar after completion

                st.subheader("Processing Summary")
                st.write(f"- Total files in ZIP: {len(xml_files_to_process)}")
                st.write(f"- Successfully parsed files: {len(successfully_parsed_files)}")

                if files_with_no_invoice_lines:
                    data_type = "invoice lines" if extraction_mode == "Detailed Line Items" else "total amounts"
                    st.write(f"- Files parsed but with no {data_type} found: {len(files_with_no_invoice_lines)}")
                    with st.expander(f"Show files parsed with no {data_type}"):
                        for fname in files_with_no_invoice_lines:
                            st.info(fname)

                if failed_to_parse_files:
                    st.write(f"- Files that failed to parse or process: {len(failed_to_parse_files)}")
                    with st.expander("Show files that failed parsing/processing and their errors"):
                        for fname, error_msg in failed_to_parse_files:
                            st.error(f"{fname}: {error_msg}")

                if all_records:
                    data_title = "Extracted Invoice Data" if extraction_mode == "Detailed Line Items" else "Extracted Total Amounts"
                    st.subheader(data_title)
                    df = pd.DataFrame(all_records)
                    st.dataframe(df)

                    output = io.BytesIO()
                    sheet_name = 'InvoiceData' if extraction_mode == "Detailed Line Items" else 'TotalAmounts'
                    file_name = "extracted_invoice_data.xlsx" if extraction_mode == "Detailed Line Items" else "extracted_total_amounts.xlsx"
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name=sheet_name)

                    st.download_button(
                        label="Download Excel",
                        data=output.getvalue(),
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                elif successfully_parsed_files and not all_records and not failed_to_parse_files:
                    data_type = "invoice line data" if extraction_mode == "Detailed Line Items" else "total amount data"
                    st.info(f"All XML files were parsed successfully, but no {data_type} was found in any of them.")
                elif not successfully_parsed_files and failed_to_parse_files and not all_records:
                    st.warning("No data extracted. All attempted XML files failed to parse.")
                elif not all_records and not failed_to_parse_files and not successfully_parsed_files and xml_files_to_process:
                    st.warning("No data was extracted, and no files were recorded as successfully parsed or failed. Please check the input files.")

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file. Please upload a valid ZIP file.")
else:
    st.info("Please upload a ZIP file containing XML files.")
