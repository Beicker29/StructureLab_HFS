import os
import openpyxl

def create_mock_sections(filepath):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sections"
    
    # Headers based on our model
    headers = ["Name", "Type", "A", "d", "bf", "tf", "tw", "Ix", "Iy", "Sx", "Sy", "Zx", "Zy", "rx", "ry", "J", "Cw"]
    ws.append(headers)
    
    # W14x90 data (approximated/standard values)
    # A=26.5, d=14.0, bf=14.5, tf=0.710, tw=0.440, Ix=999, Iy=362, Sx=143, Sy=49.9, Zx=157, Zy=75.6, rx=6.14, ry=3.7, J=4.06, Cw=16000
    w14x90 = ["W14x90", "W", 26.5, 14.0, 14.5, 0.710, 0.440, 999, 362, 143, 49.9, 157, 75.6, 6.14, 3.7, 4.06, 16000]
    
    # W14x22 light section
    w14x22 = ["W14x22", "W", 6.49, 13.7, 5.0, 0.335, 0.230, 199, 7.0, 29.0, 2.8, 33.2, 4.31, 5.54, 1.04, 0.2, 310]
    
    ws.append(w14x90)
    ws.append(w14x22)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    print(f"Created {filepath}")

if __name__ == "__main__":
    create_mock_sections("data/mock_sections.xlsx")
