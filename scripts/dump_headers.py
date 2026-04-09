import json
from pathlib import Path

import openpyxl


def main() -> None:
    workbook = openpyxl.load_workbook("data/sections.xlsx", data_only=True)
    by_sheet = {}
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        by_sheet[sheet_name] = [cell.value for cell in sheet[1]]

    Path("headers.json").write_text(
        json.dumps(by_sheet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Wrote headers.json with per-sheet headers.")


if __name__ == "__main__":
    main()
