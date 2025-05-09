import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

st.title("UBL Invoice XML Extractor")

st.markdown("""
**Instructions:**
- Please select all the XML files in your invoice folder when uploading.
- Only files with a `.xml` extension will be processed; other files will be ignored.
- For large numbers of files, consider uploading in smaller batches if you encounter network errors.
""")

uploaded_files = st.file_uploader(
    "Upload UBL XML invoice files from your folder",
    type=['xml'], # Specify XML type for client-side filtering
    accept_multiple_files=True
)

#namespaces = { # Defined globally or passed around; let's define in main processing block
#    'inv': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
#    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
#    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
#}

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

if uploaded_files:
    st.info(f"{len(uploaded_files)} file(s) selected in the uploader.")
    
    # Filter for .xml extension on the server-side as well
    xml_files_to_process = [f for f in uploaded_files if f.name.lower().endswith('.xml')]

    if not xml_files_to_process:
        st.warning("No files with .xml extension found among the uploaded files. Please upload valid XML files.")
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
        # status_text = st.empty() # Optional: for more granular status updates

        for i, xml_file in enumerate(xml_files_to_process):
            file_name = xml_file.name
            # status_text.text(f"Processing: {file_name}")
            try:
                xml_file.seek(0)  # Ensure reading from the start of the file
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                records_from_file = extract_data_from_xml_root(root, ns, file_name)
                
                if records_from_file:
                    all_records.extend(records_from_file)
                else:
                    # Parsed successfully, but no relevant InvoiceLine items found
                    files_with_no_invoice_lines.append(file_name)
                
                successfully_parsed_files.append(file_name)

            except ET.ParseError as e:
                failed_to_parse_files.append((file_name, str(e)))
            except Exception as e: # Catch other potential errors during file processing
                failed_to_parse_files.append((file_name, f"An unexpected error occurred: {str(e)}"))
            
            progress_bar.progress((i + 1) / len(xml_files_to_process))

        # status_text.text("Processing complete!")
        progress_bar.empty() # Clear the progress bar after completion

        st.subheader("Processing Summary")
        st.write(f"- Total files received by uploader: {len(uploaded_files)}")
        st.write(f"- XML files attempted for processing: {len(xml_files_to_process)}")
        st.write(f"- Successfully parsed files: {len(successfully_parsed_files)}")
        
        if files_with_no_invoice_lines:
            st.write(f"- Files parsed but with no invoice lines found: {len(files_with_no_invoice_lines)}")
            with st.expander("Show files parsed with no invoice lines"):
                for fname in files_with_no_invoice_lines:
                    st.info(fname)
        
        if failed_to_parse_files:
            st.write(f"- Files that failed to parse or process: {len(failed_to_parse_files)}")
            with st.expander("Show files that failed parsing/processing and their errors"):
                for fname, error_msg in failed_to_parse_files:
                    st.error(f"{fname}: {error_msg}")
        
        if not uploaded_files and not xml_files_to_process: # Redundant due to earlier checks, but for completeness
             st.info("No files were uploaded or no XML files were found.")

        if all_records:
            st.subheader("Extracted Invoice Data")
            df = pd.DataFrame(all_records)
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='InvoiceData')
            
            st.download_button(
                label="Download Excel",
                data=output.getvalue(),
                file_name="extracted_invoice_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif successfully_parsed_files and not all_records and not failed_to_parse_files:
            st.info("All XML files were parsed successfully, but no invoice line data was found in any of them.")
        elif not successfully_parsed_files and failed_to_parse_files and not all_records:
             st.warning("No data extracted. All attempted XML files failed to parse.")
        elif not all_records and not failed_to_parse_files and not successfully_parsed_files and xml_files_to_process :
             st.warning("No data was extracted, and no files were recorded as successfully parsed or failed. Please check the input files.")


else:
    st.info("Please upload XML files from your invoice folder.")
