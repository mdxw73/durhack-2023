# MacOS executable setup: chmod +x qrt_data_extraction-MacOS

import pandas as pd
import subprocess
import streamlit as st
import time
import os
from glob import glob
from datetime import datetime
import re
import threading
from queue import Queue

liveTrack = False
tasks = Queue()

log_directory = '.'  # Replace with your log directory
log_files = glob(os.path.join(log_directory, 'qrt_data_extraction_analysis_*.log')) # Get a list of log files in the directory
st.dataframe(pd.DataFrame(log_files))

# most_recent_log = max(log_files, key=os.path.getctime) # Find the most recent log file based on the timestamp in the filename
# LOG_FILE_PATH = most_recent_log # Set the path to your log file

columns = ['Timestamp', 'Log Level', 'Message']
dfs = []
placeholders = []

def update_dataframe(log_entry, index):
    # Parse the log entry and update the DataFrame accordingly
    pattern = re.compile(r'(?P<timestamp>\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}.\d{7}|\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}.\d{9}) (?P<log_level>\w+): (?P<message>.+)')
    match = pattern.match(log_entry)

    if match:
        timestamp = match.group('timestamp')
        log_level = match.group('log_level')
        message = match.group('message')
        
        # Update the DataFrame
        dfs[index].loc[len(dfs[index])] = [timestamp, log_level, message]

def plot_graph(index):
    # Ensure 'Timestamp' column is of type datetime
    dfs[index]['Timestamp'] = pd.to_datetime(dfs[index]['Timestamp'])

    # Set 'Timestamp' as the index in a copy of the DataFrame
    df_copy = dfs[index].set_index('Timestamp').copy()

    # Create a new DataFrame for plotting (resample data to get counts per minute)
    plot_df = df_copy.resample('1T').size().reset_index(name='Count')

    # Plot the graph
    placeholders[index].line_chart(plot_df.set_index('Timestamp'))

def run_thread(index, log_file, stop_event):
    try:
        with open(log_file) as file:
            while not stop_event.is_set():
                where = file.tell()
                lines = file.readlines()
                if not lines:
                    time.sleep(1)
                    file.seek(where)
                else:
                    for line in lines:
                        update_dataframe(line, index)
                    tasks.put(index)
    except KeyboardInterrupt:
        pass

def main():
    # Create a separate thread for each log file
    threads = []
    stop_events = []
    for index, log_file in enumerate(log_files):
        dfs.append(pd.DataFrame(columns=columns))
        placeholders.append(st.empty())
        stop_event = threading.Event()
        stop_events.append(stop_event)
        thread = threading.Thread(target=run_thread, args=(index, log_file, stop_event,))
        threads.append(thread)
        thread.start()

    try:
        print("Live track started")
        while liveTrack:
            if tasks.qsize() > 0:
                next_task = tasks.get()
                print('Executing update {} on main thread'.format(next_task))
                plot_graph(next_task)
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Set stop events to stop the threads
        for stop_event in stop_events:
            stop_event.set()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()
        print("Live track stopped")

liveTrackButton = st.empty()

if liveTrackButton.button("Live Track"):
    if liveTrackButton.button("Stop Live Track"):
        liveTrack = False
    liveTrack = True
    main()