import json
import re
import os


def is_likely_title(line_text):
    """Check if a line looks like a title even if not in metadata."""
    if not line_text:
        return False
    # Short lines that start with quotes (ASCII or Unicode) are likely titles
    quote_chars = ['"', chr(8220), chr(8221), '«', '»']  # ASCII and Unicode quotes
    if any(line_text.startswith(q) for q in quote_chars) and len(line_text) < 80:
        return True
    # Short capitalized lines without typical content endings
    if len(line_text) < 60 and line_text[0].isupper():
        if not line_text.endswith((',', ';', ':')):
            if not re.match(r'^\d+\.', line_text):  # not numbered list
                return True
    return False


def split_articles(text_file="extracted_text.txt", metadata_file="extracted_metadata.json", output_dir="codigo_penal_split/articulos"):
    """
    Split extracted text into individual article files using metadata.
    """
    # Read text and metadata
    with open(text_file, "r", encoding="utf-8") as f:
        lines = f.read().split('\n')

    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    # Build line -> metadata map
    line_meta = {h["line"]: h for h in metadata["headers"]}

    # Find all ARTICULO entries
    articles = []
    for h in metadata["headers"]:
        if h["type"] == "ARTICULO":
            match = re.match(r'Artículo\s+(\d+(?:-[A-Z])?)', h["text"])
            if match:
                articles.append({
                    "num": match.group(1),
                    "line": h["line"],
                    "page": h["page"]
                })

    print(f"Found {len(articles)} articles")

    # Process each article
    for i, art in enumerate(articles):
        art_line = art["line"]
        art_num = art["num"]

        # Find end: the line BEFORE the next article's title block starts
        if i + 1 < len(articles):
            next_art_line = articles[i + 1]["line"]

            # Scan backwards from next article to find where its title block starts
            title_block_start = next_art_line
            for j in range(next_art_line - 1, art_line, -1):
                line_text = lines[j].strip() if j < len(lines) else ""

                if j in line_meta:
                    meta = line_meta[j]
                    if meta["type"] in ["ART_TITLE", "H2", "CAPITULO", "SECCION", "TITULO", "LIBRO"]:
                        title_block_start = j
                    else:
                        break
                elif line_text == "":
                    continue
                elif is_likely_title(line_text):
                    # Short line that looks like a title - continue scanning
                    title_block_start = j
                    continue
                else:
                    # Content line - stop here
                    break

            end_line = title_block_start
        else:
            end_line = len(lines)

        # Find start: scan backwards for this article's title block
        title_start = art_line
        for j in range(art_line - 1, max(0, art_line - 30), -1):
            line_text = lines[j].strip() if j < len(lines) else ""

            if j in line_meta:
                meta = line_meta[j]
                if meta["type"] in ["ART_TITLE", "H2", "CAPITULO", "SECCION", "TITULO", "LIBRO"]:
                    title_start = j
                else:
                    break
            elif line_text == "":
                continue
            elif is_likely_title(line_text):
                title_start = j
                continue
            else:
                break

        # Don't go past previous article's end
        if i > 0:
            prev_art_line = articles[i - 1]["line"]
            title_start = max(title_start, prev_art_line + 1)

        # Extract content
        content = '\n'.join(lines[title_start:end_line]).strip()

        # Save
        if '-' in art_num:
            base_num = int(art_num.split('-')[0])
            suffix = art_num.split('-')[1]
            filename = f"articulo_{base_num:03d}_{suffix}.txt"
        else:
            filename = f"articulo_{int(art_num):03d}.txt"

        with open(f"{output_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(content)

    print(f"Saved {len(articles)} articles to {output_dir}/")
    return articles


def verify_articles(output_dir="codigo_penal_split/articulos", sample_articles=[60, 61, 62]):
    """Verify a few articles to check the split is correct."""
    print("\n=== Verification ===\n")

    for art_num in sample_articles:
        filename = f"{output_dir}/articulo_{art_num:03d}.txt"
        if os.path.exists(filename):
            with open(filename) as f:
                content = f.read()
            print(f"--- Article {art_num} ---")
            print(content[:400])
            print("\n")
        else:
            print(f"Article {art_num}: NOT FOUND")


if __name__ == "__main__":
    articles = split_articles()
    verify_articles()
