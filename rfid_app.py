import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import csv
import os
import serial
import threading
from datetime import datetime
import time
import re

SCAN_LOG_FILE = r"C:\Users\willi\OneDrive\Desktop\ITS-3400 Final\scan_log.csv"
SERIAL_PORT = 'COM5' 
BAUDRATE = 9600
RFID_DATABASE_FILE = r"C:\Users\willi\OneDrive\Desktop\ITS-3400 Final\rfid_database.csv"

def is_valid_tag(tag):
    return tag.isalnum() and 8 <= len(tag) <= 16

def clean_tag(tag):
    return ''.join(c for c in tag if c.isalnum())

def get_last_directions(log_output):
    last_direction = {}
    if os.path.exists(log_output):
        with open(log_output, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                last_direction[row['tag']] = row['direction']
    return last_direction

def serial_monitor(rfid_dict, log_output, app, poll_interval=0.2):
    last_processed_tag = None
    last_direction = {}  # key: (tag, location)
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                print(f"Raw serial data: {repr(line)}")
                tag = clean_tag(line)
                print(f"Tag: {tag}, Valid: {is_valid_tag(tag)}")
                if tag and is_valid_tag(tag):
                    location = app.location.get()
                    if location == "bus":
                        enter_msg = "got on the bus"
                        exit_msg = "got off the bus"
                    else:
                        enter_msg = "entered the school building"
                        exit_msg = "left the school building"
                    key = (tag, location)
                    if key not in last_direction or last_direction[key] == exit_msg:
                        direction = enter_msg
                    else:
                        direction = exit_msg
                    last_direction[key] = direction

                    with open(log_output, 'a', newline='') as logfile:
                        log_writer = csv.writer(logfile)
                        if logfile.tell() == 0:
                            log_writer.writerow(['timestamp', 'tag', 'name', 'direction'])
                        name = rfid_dict.get(tag, "Unknown")
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_writer.writerow([timestamp, tag, name, direction])
                    last_processed_tag = tag
                time.sleep(poll_interval)
    except Exception as e:
        print(f"Serial monitor error: {e}")

class RFIDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ITS-3400 Final Project RFID Scanner")
        self.geometry("900x800")

        # Default location
        self.location = tk.StringVar(value="school")

        # Location buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="School", command=lambda: self.set_location("school")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Bus Stop", command=lambda: self.set_location("bus")).pack(side=tk.LEFT, padx=5)

        # Clear scan_log.csv (write header)
        with open(SCAN_LOG_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'tag', 'name', 'direction'])

        # Button to clear scan log
        self.clear_button = ttk.Button(self, text="Clear Scan Log", command=self.clear_scan_log)
        self.clear_button.pack(pady=5)

        # Scan log display
        self.log_display = scrolledtext.ScrolledText(self, width=80, height=20, state='disabled')
        self.log_display.pack(padx=10, pady=10, fill='both', expand=True)

        self.display_scan_log()
        self.auto_refresh_log()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_location(self, loc):
        self.location.set(loc)
        messagebox.showinfo("Location Changed", f"Location set to: {loc.capitalize()}")

    def display_scan_log(self):
        self.log_display.config(state='normal')
        self.log_display.delete(1.0, tk.END)
        if not os.path.exists(SCAN_LOG_FILE):
            self.log_display.insert(tk.END, "No scan_log.csv file found.")
        else:
            with open(SCAN_LOG_FILE, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    self.log_display.insert(tk.END, ', '.join(row) + '\n')
        self.log_display.config(state='disabled')

    def clear_scan_log(self):
        with open(SCAN_LOG_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'tag', 'name', 'direction'])
        self.display_scan_log()
        messagebox.showinfo("Cleared", "Scan log has been cleared.")

    def auto_refresh_log(self):
        self.display_scan_log()
        self.after(2000, self.auto_refresh_log)

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    # Load your RFID database
    rfid_dict = {}
    if os.path.exists(RFID_DATABASE_FILE):
        with open(RFID_DATABASE_FILE, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rfid_dict[row['hex_id'].strip()] = row['name'].strip()

    app = RFIDApp()

    # Pass the app instance to serial_monitor so it can read the location
    serial_thread = threading.Thread(
        target=serial_monitor,
        args=(rfid_dict, SCAN_LOG_FILE, app),
        daemon=True
    )
    serial_thread.start()

    app.mainloop()