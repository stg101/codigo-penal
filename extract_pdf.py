import pdfplumber

def extract_columns(pdf_path, start_page=8, output_path="extracted_text.txt"):
    """
    Extract text from a 2-column PDF, detecting boundaries dynamically.
    """
    with pdfplumber.open(pdf_path) as pdf:
        all_text = []

        for page_num in range(start_page - 1, len(pdf.pages)):
            page = pdf.pages[page_num]
            lines = page.lines

            # Find vertical lines (x0 ≈ x1) for column separator
            vertical_lines = [l for l in lines if abs(l['x0'] - l['x1']) < 2]

            # Find full-width horizontal lines for header/footer boundaries
            horizontal_lines = [l for l in lines if abs(l['y0'] - l['y1']) < 2]
            full_width_h_lines = [l for l in horizontal_lines if (l['x1'] - l['x0']) > page.width * 0.8]
            full_width_h_lines.sort(key=lambda l: l['y0'])

            # Detect column separator (longest vertical line)
            if vertical_lines:
                separator = max(vertical_lines, key=lambda l: abs(l['y1'] - l['y0']))
                sep_x = separator['x0']
            else:
                sep_x = page.width / 2

            # Detect header boundary (first full-width line from top)
            if full_width_h_lines:
                header_line = full_width_h_lines[0]
                content_top = header_line['y0'] + 28  # below header text (header line + text height)
            else:
                content_top = page.height * 0.06

            # Detect footer boundary (highest full-width line in bottom 5%)
            footer_lines = [l for l in full_width_h_lines if l['y0'] > page.height * 0.95]
            if footer_lines:
                footer_line = min(footer_lines, key=lambda l: l['y0'])  # topmost line in footer zone
                content_bottom = footer_line['y0'] - 2  # just above footer line
            else:
                content_bottom = page.height * 0.92

            # Define column boundaries
            left_bbox = (0, content_top, sep_x - 3, content_bottom)
            right_bbox = (sep_x + 3, content_top, page.width, content_bottom)

            # Extract text from each column
            left_text = page.within_bbox(left_bbox).extract_text() or ""
            right_text = page.within_bbox(right_bbox).extract_text() or ""

            # Combine: left column first, then right column
            page_text = f"{left_text}\n{right_text}"
            all_text.append(page_text)
            print(f"Processed page {page_num + 1}")

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(all_text))

        print(f"\nDone. Saved to {output_path}")

if __name__ == "__main__":
    extract_columns("source.pdf", start_page=8, output_path="extracted_text.txt")
