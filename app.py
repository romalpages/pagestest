import os
import pdfplumber
from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import A3
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

app = Flask(__name__)

def clean_table(table):
    """Cleans extracted tables by removing rows with mismatched columns."""
    if not table or len(table) < 2:
        return []
    expected_columns = len(table[0])
    return [row for row in table if len(row) == expected_columns]

def extract_table_from_pdf(pdf_path):
    """Extracts tables from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        all_tables = []
        for page in pdf.pages:
            page_tables = []
            tables = page.extract_tables()
            for table in tables:
                cleaned_table = clean_table(table)
                if cleaned_table:
                    page_tables.append(cleaned_table)

            if not page_tables and page.extract_text():
                page_text = page.extract_text()
                single_column_content = [[line] for line in page_text.split("\n")]
                page_tables.append(single_column_content)

            all_tables.append(page_tables)
    return all_tables

def search_and_extract_serial_number(tables, serial_number):
    """Filters extracted tables based on the given serial number."""
    extracted_data = []
    for page_tables in tables:
        for table in page_tables:
            if len(table) < 2:
                continue
            header_row = table[0]
            subheader_row = table[1] if len(table) > 1 else []
            matching_rows = [row for row in table[2:] if str(row[0]).strip().lower() == str(serial_number).strip().lower()]
            if matching_rows:
                extracted_data.append(header_row)
                if subheader_row:
                    extracted_data.append(subheader_row)
                extracted_data.extend(matching_rows)
    return extracted_data

def generate_pdf_with_filtered_data(filtered_data, output_pdf_path):
    """Generates a filtered PDF with the extracted table data."""
    document = SimpleDocTemplate(output_pdf_path, pagesize=A3)
    content = []
    styles = getSampleStyleSheet()
    
    page_width, page_height = A3
    max_table_width = page_width - 0.2 * inch
    
    if filtered_data:
        num_columns = len(filtered_data[0])
        col_widths = [max_table_width / num_columns for _ in range(num_columns)]

        table_object = Table(filtered_data, colWidths=col_widths)
        table_style = TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('WORDWRAP', (0, 0), (-1, -1), 'COLUMNS')
        ])
        table_object.setStyle(table_style)
        
        content.append(table_object)
        content.append(PageBreak())
    else:
        content.append(Paragraph("No matching data found.", styles["BodyText"]))

    document.build(content)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "pdf_file" not in request.files:
            return "No file uploaded", 400
        file = request.files["pdf_file"]
        if file.filename == "":
            return "No selected file", 400

        pdf_path = "uploaded.pdf"
        file.save(pdf_path)

        serial_number = request.form.get("serial_number")
        tables = extract_table_from_pdf(pdf_path)
        filtered_data = search_and_extract_serial_number(tables, serial_number)

        if filtered_data:
            output_pdf_path = "filtered_data.pdf"
            generate_pdf_with_filtered_data(filtered_data, output_pdf_path)
            return send_file(output_pdf_path, as_attachment=True)

    return render_template("upload.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
