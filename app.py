import pdfplumber
import pandas as pd
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import A3
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os

app = Flask(__name__)

def clean_table(table):
    if not table or len(table) < 2:
        return []
    expected_columns = len(table[0])
    cleaned_table = [row for row in table if len(row) == expected_columns]
    return cleaned_table

def extract_table_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_tables = []
        for page_number, page in enumerate(pdf.pages, start=1):
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

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        serial_number = request.form['serial_number']
        
        if uploaded_file and serial_number:
            pdf_path = "uploaded.pdf"
            uploaded_file.save(pdf_path)
            
            tables = extract_table_from_pdf(pdf_path)
            filtered_data = search_and_extract_serial_number(tables, serial_number)
            
            if filtered_data:
                output_pdf_path = "filtered_data.pdf"
                generate_pdf_with_filtered_data(filtered_data, output_pdf_path)
                return send_file(output_pdf_path, as_attachment=True)
            else:
                return "No matching content found."
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
