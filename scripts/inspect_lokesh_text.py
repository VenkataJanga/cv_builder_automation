from pathlib import Path

from src.infrastructure.parsers.docx_extractor import extract_docx


def main() -> None:
    upload_dir = Path("data/storage/uploads")
    files = sorted(upload_dir.glob("*Lokesh Kumar Resume.docx"))
    if not files:
        print("No files found")
        return

    for file_path in files:
        print("=" * 120)
        print(f"FILE: {file_path}")
        text = extract_docx(str(file_path))
        lines = text.splitlines()
        print(f"TOTAL_LINES: {len(lines)}")
        print("--- FIRST 220 LINES ---")
        for idx, line in enumerate(lines[:220], start=1):
            print(f"{idx:03d}: {line}")


if __name__ == "__main__":
    main()
