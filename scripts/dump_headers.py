import openpyxl, json
wb = openpyxl.load_workbook('data/sections.xlsx', data_only=True)
headers = [c.value for c in wb.active[1]]
with open('headers.json', 'w') as f:
    json.dump(headers, f)
