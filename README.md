# XML Invoice Extractor

This project provides a simple solution for extracting invoice data from XML files. It is designed for non-technical users to easily upload XML files and retrieve structured invoice data in an Excel format.

## Project Structure

```
xml-invoice-extractor
├── src
│   ├── xml_extraction.py  # Logic for extracting invoice data from XML files
│   └── app.py             # Main application entry point for user interaction
├── requirements.txt        # List of dependencies required for the project
└── README.md               # Documentation for the project
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd xml-invoice-extractor
   ```

2. **Set up a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Prepare your XML files:**
   Place your XML invoice files in a designated input folder.

2. **Run the application:**
   You can run the application using the command line:
   ```bash
   python src/app.py
   ```

3. **Follow the prompts:**
   The application will guide you through the process of uploading XML files and extracting the invoice data.

## Troubleshooting

- Ensure that your XML files are well-formed and adhere to the expected schema.
- If you encounter any issues, check the console output for error messages that can help diagnose the problem.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.