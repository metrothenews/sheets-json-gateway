import os
from sheets_json_gateway.sheets import read_key_value_tab

def main():
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    cfg = read_key_value_tab(sheet_id=sheet_id, tab_name="Publer Config")
    print("Loaded keys:", sorted(cfg.keys()))

if __name__ == "__main__":
    main()
