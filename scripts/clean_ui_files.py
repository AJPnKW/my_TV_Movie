import os
import re
import chardet

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
INPUT_DIR = r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\web"
OUTPUT_FILE = r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\scripts\cleaned_ui_chunks.txt"

FILES = [
    "index.html",
    "config.html",
    "watchlist.html",
    "wrong.index.html",
    "wrong.config.html",
    "wrong.watchlist.html"
]

CHUNK_SIZE = 8000   # Safe for ChatGPT paste
SEPARATOR = "\n\n===== END OF CHUNK =====\n\n"

# ---------------------------------------------
# HELPERS
# ---------------------------------------------

def detect_encoding(path):
    """Detect file encoding safely."""
    with open(path, "rb") as f:
        raw = f.read()
    return chardet.detect(raw)["encoding"] or "utf-8"

def load_and_clean(path):
    """Load file, normalize encoding, strip dangerous characters, escape HTML."""
    enc = detect_encoding(path)

    with open(path, "r", encoding=enc, errors="replace") as f:
        text = f.read()

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove BOM if present
    text = text.lstrip("\ufeff")

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove invisible Unicode control characters
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F]", "", text)

    # Escape HTML tags so ChatGPT doesn't convert to attachments
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # Ensure no line is too long (split long lines)
    safe_lines = []
    for line in text.split("\n"):
        if len(line) > 500:
            # Break long lines into safe segments
            for i in range(0, len(line), 500):
                safe_lines.append(line[i:i+500])
        else:
            safe_lines.append(line)

    return "\n".join(safe_lines)

def chunk_text(label, text):
    """Split cleaned text into safe chunks with labels."""
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE):
        chunk = text[i:i+CHUNK_SIZE]
        chunks.append(f"===== START {label} (chunk) =====\n{chunk}\n===== END {label} (chunk) =====")
    return chunks

# ---------------------------------------------
# MAIN
# ---------------------------------------------
all_chunks = []

for filename in FILES:
    full_path = os.path.join(INPUT_DIR, filename)
    if not os.path.exists(full_path):
        continue

    cleaned = load_and_clean(full_path)
    chunks = chunk_text(filename, cleaned)
    all_chunks.extend(chunks)

# Write final output
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    for chunk in all_chunks:
        out.write(chunk)
        out.write(SEPARATOR)

print("DONE — cleaned_ui_chunks.txt created successfully.")
