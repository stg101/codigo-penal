import json
import re
import os


def is_likely_title(line_text):
    """Check if a line looks like a title even if not in metadata."""
    if not line_text:
        return False
    if is_footnote_line(line_text):
        return False
    # Short lines that start with quotes (ASCII or Unicode) are likely titles
    quote_chars = ['"', chr(8220), chr(8221), '«', '»']  # ASCII and Unicode quotes
    if any(line_text.startswith(q) for q in quote_chars) and len(line_text) < 80:
        return True
    # ALL CAPS headers are likely titles
    if line_text.isupper() and len(line_text) < 80:
        return True
    return False


def is_footnote_line(line_text):
    """Detect lines that look like footnote continuations."""
    text = line_text.strip()
    if not text:
        return False
    if re.match(r'^(N[º°]\s*\d+|Ley\s+N[º°]\s*\d+|No\.\s*\d+)', text):
        return True
    lowered = text.lower()
    if "publicada el" in lowered:
        return True
    if "modificado por" in lowered or "incorporado por" in lowered or "sustituido por" in lowered:
        return True
    if "(*)" in text:
        return True
    return False


def is_title_continuation_line(lines, line_meta, idx):
    """Detect wrapped title lines that follow an ART_TITLE line."""
    if idx <= 0 or idx >= len(lines):
        return False
    if idx - 1 not in line_meta:
        return False
    if line_meta[idx - 1]["type"] != "ART_TITLE":
        return False
    text = lines[idx].strip()
    if not text or is_footnote_line(text):
        return False
    if text.startswith("Artículo"):
        return False
    return True


def build_title_block_candidates(lines):
    """Mark wrapped title lines that precede an Articulo line."""
    candidates = set()
    for i, line in enumerate(lines):
        if not is_likely_title(line):
            continue
        for k in range(i + 1, min(i + 6, len(lines))):
            if re.match(r'^Artículo\s+\d+(?:-[A-Z])?\s*\.-', lines[k].strip()):
                for j in range(i, k):
                    if lines[j].strip() and not is_footnote_line(lines[j]):
                        candidates.add(j)
                break
    return candidates


def split_articles(text_file="extracted_text.txt", metadata_file="extracted_metadata.json", output_dir="codigo_penal_split/articulos"):
    """
    Split extracted text into individual article files using metadata.
    """
    # Read text and metadata
    with open(text_file, "r", encoding="utf-8") as f:
        lines = f.read().split('\n')
    title_block_candidates = build_title_block_candidates(lines)

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
    prev_end_line = 0
    order_width = len(str(len(articles)))
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
                elif is_title_continuation_line(lines, line_meta, j):
                    title_block_start = j - 1
                    continue
                elif j in title_block_candidates:
                    title_block_start = j
                    continue
                elif is_footnote_line(line_text):
                    # Footnote continuation belongs to current article content
                    break
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
            elif is_title_continuation_line(lines, line_meta, j):
                title_start = j - 1
                continue
            elif j in title_block_candidates:
                title_start = j
                continue
            elif is_footnote_line(line_text):
                break
            else:
                break

        # Don't include content that belongs to the previous article
        if i > 0:
            title_start = max(title_start, prev_end_line)

        # Extract content
        content = '\n'.join(lines[title_start:end_line]).strip()

        # Save
        order_prefix = f"{i + 1:0{order_width}d}"
        if '-' in art_num:
            base_num = int(art_num.split('-')[0])
            suffix = art_num.split('-')[1]
            filename = f"{order_prefix}_articulo_{base_num:03d}_{suffix}.txt"
        else:
            filename = f"{order_prefix}_articulo_{int(art_num):03d}.txt"

        with open(f"{output_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(content)

        prev_end_line = end_line

    print(f"Saved {len(articles)} articles to {output_dir}/")
    return articles


def verify_articles(output_dir="codigo_penal_split/articulos", sample_articles=[60, 61, 62]):
    """Verify a few articles to check the split is correct."""
    print("\n=== Verification ===\n")

    for art_num in sample_articles:
        pattern = f"*_articulo_{art_num:03d}*.txt"
        matches = sorted(
            name for name in os.listdir(output_dir) if name.endswith(".txt")
            and re.match(pattern.replace("*", ".*"), name)
        )
        if matches:
            filename = os.path.join(output_dir, matches[0])
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
