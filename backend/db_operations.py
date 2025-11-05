# backend/db_operations.py

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import time, sys, threading

spinner = ['◐', '◓', '◑', '◒']

def run_db_script(host, username, password, database):
    try:
        engine = create_engine(f"mysql+pymysql://{username}:{password}@{host}/{database}")
        connection = engine.connect()
        print("✅ Connection successful")

        def spinner_loader(msg, stop_event):
            i = 0
            while not stop_event.is_set():
                sys.stdout.write(f"\r{spinner[i % 4]} {msg}")
                sys.stdout.flush()
                time.sleep(0.1)
                i += 1

        file_path = r"C:\Users\lakshmi.hs\Downloads\xx_problem.xlsx"
        stop = threading.Event()
        t = threading.Thread(target=spinner_loader, args=("Reading Excel file...", stop))
        t.start()
        df = pd.read_excel(file_path)
        stop.set()
        t.join()
        print("\rReading Excel file... Done!")

        for c in df.select_dtypes(include='bool').columns:
            df[c] = df[c].astype(str)

        # The rest of your logic will run automatically later
        return {"status": "success", "message": "✅ Connection successful. Excel file loaded."}

    except SQLAlchemyError as e:
        return {"status": "error", "message": "❌ Invalid username or password."}
