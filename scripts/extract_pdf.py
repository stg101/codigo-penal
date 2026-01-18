import pdfplumber
import json
import re

def extract_with_metadata(pdf_path, start_page=8, text_output="extracted_text.txt", json_output="extracted_metadata.json"):
    """
    Extract text and metadata separately:
    - Text: Clean extraction using extract_text() (reliable)
    - Metadata: JSON with line numbers and types of headers/titles
    """

    with pdfplumber.open(pdf_path) as pdf:
        all_text_lines = []
        metadata = {"headers": []}
        current_line_num = 0

        for page_num in range(start_page - 1, len(pdf.pages)):
            page = pdf.pages[page_num]
            lines = page.lines

            # Find boundaries
            vertical_lines = [l for l in lines if abs(l['x0'] - l['x1']) < 2]
            horizontal_lines = [l for l in lines if abs(l['y0'] - l['y1']) < 2]
            full_width_h_lines = [l for l in horizontal_lines if (l['x1'] - l['x0']) > page.width * 0.8]
            full_width_h_lines.sort(key=lambda l: l['y0'])

            if vertical_lines:
                separator = max(vertical_lines, key=lambda l: abs(l['y1'] - l['y0']))
                sep_x = separator['x0']
            else:
                sep_x = page.width / 2

            if full_width_h_lines:
                header_line = full_width_h_lines[0]
                content_top = header_line['y0'] + 28
            else:
                content_top = page.height * 0.06

            footer_lines = [l for l in full_width_h_lines if l['y0'] > page.height * 0.95]
            if footer_lines:
                footer_line = min(footer_lines, key=lambda l: l['y0'])
                content_bottom = footer_line['y0'] - 2
            else:
                content_bottom = page.height * 0.92

            # Process each column
            left_bbox = (0, content_top, sep_x - 3, content_bottom)
            right_bbox = (sep_x + 3, content_top, page.width, content_bottom)

            for bbox in [left_bbox, right_bbox]:
                cropped = page.within_bbox(bbox)

                # Get clean text using extract_text() - reliable method
                text = cropped.extract_text() or ""
                text_lines = text.split('\n')

                # Get words with font info for metadata detection only
                words = cropped.extract_words(extra_attrs=['fontname', 'size'])
                word_lines = group_words_into_lines(words)

                # Process each text line
                for line_text in text_lines:
                    line_text_stripped = line_text.strip()
                    if not line_text_stripped:
                        continue

                    all_text_lines.append(line_text)

                    # Detect line type using font info
                    line_type = detect_line_type(line_text_stripped, word_lines)

                    if line_type:
                        metadata["headers"].append({
                            "line": current_line_num,
                            "type": line_type,
                            "text": line_text_stripped,
                            "page": page_num + 1
                        })

                    current_line_num += 1

            print(f"Processed page {page_num + 1}")

        # Write clean text
        with open(text_output, "w", encoding="utf-8") as f:
            f.write('\n'.join(all_text_lines))

        # Write metadata JSON
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"\nDone.")
        print(f"Text saved to: {text_output}")
        print(f"Metadata saved to: {json_output}")
        print(f"Total lines: {current_line_num}")
        print(f"Headers detected: {len(metadata['headers'])}")


def group_words_into_lines(words, y_tolerance=3):
    """Group words into lines based on y position"""
    if not words:
        return []

    words = sorted(words, key=lambda w: (round(w['top'] / 2) * 2, w['x0']))

    lines = []
    current_line = [words[0]]
    current_y = words[0]['top']

    for w in words[1:]:
        if abs(w['top'] - current_y) <= y_tolerance:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_line = [w]
            current_y = w['top']
    lines.append(current_line)

    # Convert to line info
    result = []
    for line_words in lines:
        text = ' '.join(w['text'] for w in line_words)
        fonts = [w.get('fontname', '') for w in line_words]
        sizes = [w.get('size', 9) for w in line_words]

        is_bold = any('Bold' in f and 'Italic' not in f for f in fonts)
        avg_size = sum(sizes) / len(sizes) if sizes else 9

        result.append({
            'text': text,
            'is_bold': is_bold,
            'size': round(avg_size, 1)
        })

    return result


def detect_line_type(line_text, word_lines):
    """Detect the type of a line based on its content and font info"""
    line_text = line_text.strip()
    if not line_text:
        return None

    # Find matching word line (by text similarity)
    font_info = None
    line_lower = line_text[:30].lower()
    for wl in word_lines:
        wl_lower = wl['text'][:30].lower()
        if line_lower in wl_lower or wl_lower in line_lower:
            font_info = wl
            break

    is_bold = font_info['is_bold'] if font_info else False
    size = font_info['size'] if font_info else 9.0

    # Detect ARTICULO - must have ".-" pattern (actual article definition)
    if re.match(r'^Artículo\s+\d+(?:-[A-Z])?\s*\.-', line_text):
        return "ARTICULO"

    # Detect LIBRO
    if 'LIBRO' in line_text and line_text.isupper():
        return "LIBRO"

    # Detect TITULO
    if 'TÍTULO' in line_text or line_text.startswith('TÍTULO'):
        return "TITULO"

    # Detect CAPITULO
    if 'CAPÍTULO' in line_text or line_text.startswith('CAPÍTULO'):
        return "CAPITULO"

    # Detect SECCION
    if 'SECCIÓN' in line_text or line_text.startswith('SECCIÓN'):
        return "SECCION"

    # Detect H2 (ALL CAPS headers)
    if is_bold and line_text.isupper() and len(line_text) < 60 and len(line_text) > 3:
        return "H2"

    # Detect ART_TITLE (bold, short, capitalized, not all caps)
    if is_bold and size >= 8.5 and size < 10:
        if len(line_text) < 80 and not line_text.isupper():
            if not re.match(r'^\d+\.', line_text):  # not numbered list
                if line_text[0].isupper():
                    return "ART_TITLE"

    return None


if __name__ == "__main__":
    extract_with_metadata(
        "source.pdf",
        start_page=8,
        text_output="extracted_text.txt",
        json_output="extracted_metadata.json"
    )
