import os
import re


def join_article_texts(articles_dir):
    files = sorted(
        [f for f in os.listdir(articles_dir) if f.endswith(".txt")],
        key=lambda name: (
            int(re.search(r"articulo_(\d+)", name).group(1)),
            name,
        ),
    )
    parts = []
    for name in files:
        path = os.path.join(articles_dir, name)
        with open(path, encoding="utf-8") as f:
            parts.append(f.read().strip())
    return "\n".join(p for p in parts if p)


def join_libro_texts(libro_files):
    parts = []
    for path in libro_files:
        with open(path, encoding="utf-8") as f:
            parts.append(f.read().strip())
    return "\n".join(p for p in parts if p)


def verify_joined_texts(
    articles_dir="codigo_penal_split/articulos",
    libro_files=None,
):
    if libro_files is None:
        libro_files = [
            "codigo_penal_split/4_libro_1_parte_general.txt",
            "codigo_penal_split/5_libro_2_parte_especial.txt",
            "codigo_penal_split/6_libro_3_faltas.txt",
        ]

    articles_text = join_article_texts(articles_dir)
    libros_text = join_libro_texts(libro_files)

    print(f"Joined articles chars: {len(articles_text)}")
    print(f"Joined libros chars:   {len(libros_text)}")
    print(f"Exact match: {articles_text == libros_text}")

    if articles_text != libros_text:
        min_len = min(len(articles_text), len(libros_text))
        diff_at = None
        for i in range(min_len):
            if articles_text[i] != libros_text[i]:
                diff_at = i
                break
        if diff_at is None:
            diff_at = min_len
        print(f"First diff at: {diff_at}")
        print("Articles snippet:", repr(articles_text[diff_at : diff_at + 200]))
        print("Libros snippet:  ", repr(libros_text[diff_at : diff_at + 200]))


if __name__ == "__main__":
    verify_joined_texts()
