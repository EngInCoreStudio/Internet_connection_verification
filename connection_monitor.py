"""
Dependencies:
- pip install speedtest-cli
- pip install pandas
- pip install schedule (optional)
- tkinter (included with Python)

This script provides a GUI for real-time internet connection monitoring.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import pandas as pd
import json
import subprocess
from datetime import datetime

# --- ICMP Ping Functionality ---
def ping_host(host):
    """Ping the host once and return latency in ms, or -1 if failed."""
    try:
        # Windows ping: -n 1 (one ping), -w 1000 (timeout ms)
        output = subprocess.check_output([
            'ping', host, '-n', '1', '-w', '1000'
        ], universal_newlines=True)
        for line in output.splitlines():
            # English: 'Average = 99ms', Italian: 'Media = 99ms', 'Medio = 99ms'
            if 'Average' in line or 'Media' in line or 'Medio' in line:
                # Find the last '=' and extract the number before 'ms'
                try:
                    latency = int(line.split('=')[-1].replace('ms', '').replace(' ', '').strip())
                    return latency
                except Exception:
                    continue
    except Exception:
        return -1
    return -1

def compute_jitter(latencies):
    if len(latencies) < 2:
        return 0
    diffs = [abs(latencies[i] - latencies[i-1]) for i in range(1, len(latencies))]
    return sum(diffs) / len(diffs)

def compute_packet_loss(latencies):
    if not latencies:
        return 100.0
    lost = sum(1 for l in latencies if l == -1)
    return 100.0 * lost / len(latencies)

# --- Speedtest Functionality ---
def run_speedtest(server_id=None):
    cmd = ['speedtest', '--json']  # Use --json for compatibility
    if server_id:
        cmd += ['--server', str(server_id)]  # Use --server for speedtest-cli
    try:
        result = subprocess.check_output(cmd, universal_newlines=True)
        return json.loads(result)
    except Exception as e:
        return {'error': str(e)}

# --- Logger Functions ---
def log_ping(log_dir, timestamp, latency, jitter, packet_loss):
    print(f"[PING] {timestamp} | Latency: {latency} ms | Jitter: {jitter:.1f} ms | Packet Loss: {packet_loss:.1f}%")
    log_path = os.path.join(log_dir, 'ping_results.csv')
    header = not os.path.exists(log_path)
    with open(log_path, 'a') as f:
        if header:
            f.write('Timestamp,Latency (ms),Jitter (ms),Packet Loss (%)\n')
        f.write(f'{timestamp},{latency},{jitter},{packet_loss}\n')

def log_speedtest(log_dir, result):
    print(f"[SPEEDTEST] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Result: {result}")
    log_path = os.path.join(log_dir, 'speedtest_results.json')
    with open(log_path, 'a') as f:
        f.write(json.dumps(result) + '\n')

# --- GUI Application ---
class ConnectionMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Connection Monitoring Program')
        self.running = False
        self.ping_thread = None
        self.speedtest_thread = None
        self.latencies = []
        self.log_dir = tk.StringVar(value=os.path.abspath('connection_logs'))
        self._build_gui()

    def _build_gui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(row=0, column=0, sticky='nsew')
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Input fields
        ttk.Label(frm, text='Host to Ping:').grid(row=0, column=0, sticky='e')
        self.host_entry = ttk.Entry(frm)
        self.host_entry.insert(0, '8.8.8.8')
        self.host_entry.grid(row=0, column=1)

        ttk.Label(frm, text='Ping Interval (s):').grid(row=1, column=0, sticky='e')
        self.ping_interval_entry = ttk.Entry(frm)
        self.ping_interval_entry.insert(0, '2')
        self.ping_interval_entry.grid(row=1, column=1)

        ttk.Label(frm, text='Speedtest Interval (min):').grid(row=2, column=0, sticky='e')
        self.speedtest_interval_entry = ttk.Entry(frm)
        self.speedtest_interval_entry.insert(0, '10')
        self.speedtest_interval_entry.grid(row=2, column=1)

        ttk.Label(frm, text='Latency Threshold (ms):').grid(row=3, column=0, sticky='e')
        self.latency_threshold_entry = ttk.Entry(frm)
        self.latency_threshold_entry.insert(0, '100')
        self.latency_threshold_entry.grid(row=3, column=1)

        ttk.Label(frm, text='Speedtest Server ID (optional):').grid(row=4, column=0, sticky='e')
        self.server_id_entry = ttk.Entry(frm)
        self.server_id_entry.grid(row=4, column=1)

        ttk.Label(frm, text='Log Directory:').grid(row=5, column=0, sticky='e')
        self.log_dir_entry = ttk.Entry(frm, textvariable=self.log_dir)
        self.log_dir_entry.grid(row=5, column=1)
        ttk.Button(frm, text='Browse', command=self._browse_log_dir).grid(row=5, column=2)

        # Real-time display
        self.status_label = ttk.Label(frm, text='Status: Idle', font=('Arial', 12, 'bold'))
        self.status_label.grid(row=6, column=0, columnspan=3, pady=10)
        self.latency_var = tk.StringVar(value='-')
        self.jitter_var = tk.StringVar(value='-')
        self.packet_loss_var = tk.StringVar(value='-')
        self.download_var = tk.StringVar(value='-')
        self.upload_var = tk.StringVar(value='-')
        ttk.Label(frm, text='Latency (ms):').grid(row=7, column=0, sticky='e')
        ttk.Label(frm, textvariable=self.latency_var).grid(row=7, column=1, sticky='w')
        ttk.Label(frm, text='Jitter (ms):').grid(row=8, column=0, sticky='e')
        ttk.Label(frm, textvariable=self.jitter_var).grid(row=8, column=1, sticky='w')
        ttk.Label(frm, text='Packet Loss (%):').grid(row=9, column=0, sticky='e')
        ttk.Label(frm, textvariable=self.packet_loss_var).grid(row=9, column=1, sticky='w')
        ttk.Label(frm, text='Download (Mbit/s):').grid(row=10, column=0, sticky='e')
        ttk.Label(frm, textvariable=self.download_var).grid(row=10, column=1, sticky='w')
        ttk.Label(frm, text='Upload (Mbit/s):').grid(row=11, column=0, sticky='e')
        ttk.Label(frm, textvariable=self.upload_var).grid(row=11, column=1, sticky='w')

        # Start/Stop buttons
        self.start_btn = ttk.Button(frm, text='Start', command=self.start_monitoring)
        self.start_btn.grid(row=12, column=0, pady=10)
        self.stop_btn = ttk.Button(frm, text='Stop', command=self.stop_monitoring, state='disabled')
        self.stop_btn.grid(row=12, column=1, pady=10)
        self.history_btn = ttk.Button(frm, text='Show History', command=self._show_history_window)
        self.history_btn.grid(row=12, column=2, pady=10)

    def _browse_log_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.log_dir.set(d)

    def start_monitoring(self):
        self.running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text='Status: Running')
        self.latencies = []
        os.makedirs(self.log_dir.get(), exist_ok=True)
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()
        self.speedtest_thread = threading.Thread(target=self._speedtest_loop, daemon=True)
        self.speedtest_thread.start()

    def stop_monitoring(self):
        self.running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text='Status: Stopped')

    def _ping_loop(self):
        host = self.host_entry.get()
        interval = float(self.ping_interval_entry.get())
        latency_threshold = float(self.latency_threshold_entry.get())
        while self.running:
            latency = ping_host(host)
            self.latencies.append(latency)
            if len(self.latencies) > 10:
                self.latencies.pop(0)
            jitter = compute_jitter(self.latencies)
            packet_loss = compute_packet_loss(self.latencies)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_ping(self.log_dir.get(), timestamp, latency, jitter, packet_loss)
            self.root.after(0, lambda l=latency, j=jitter, p=packet_loss: self._update_ping_display(l, j, p))
            # Trigger speedtest if latency threshold exceeded
            if len(self.latencies) >= 5 and sum(self.latencies[-5:])/5 > latency_threshold:
                self._trigger_speedtest()
            time.sleep(interval)

    def _update_ping_display(self, latency, jitter, packet_loss):
        self.latency_var.set(f'{latency:.1f}' if latency != -1 else 'Lost')
        self.jitter_var.set(f'{jitter:.1f}')
        self.packet_loss_var.set(f'{packet_loss:.1f}')

    def _speedtest_loop(self):
        interval = float(self.speedtest_interval_entry.get()) * 60
        server_id = self.server_id_entry.get() or None
        while self.running:
            self._trigger_speedtest(server_id)
            time.sleep(interval)

    def _trigger_speedtest(self, server_id=None):
        result = run_speedtest(server_id)
        log_speedtest(self.log_dir.get(), result)
        if 'download' in result and 'upload' in result:
            download = result['download'] / 1e6
            upload = result['upload'] / 1e6
            self.root.after(0, lambda d=download, u=upload: self._update_speedtest_display(d, u))
        else:
            self.root.after(0, lambda: self._update_speedtest_display('-', '-'))

    def _update_speedtest_display(self, download, upload):
        self.download_var.set(f'{download:.2f}' if isinstance(download, float) else '-')
        self.upload_var.set(f'{upload:.2f}' if isinstance(upload, float) else '-')

    def _show_history_window(self):
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import pandas as pd
        import os
        # Load ping data
        ping_path = os.path.join(self.log_dir.get(), 'ping_results.csv')
        if not os.path.exists(ping_path):
            messagebox.showerror('Error', 'No ping_results.csv found!')
            return
        df = pd.read_csv(ping_path)
        if df.empty or df['Latency (ms)'].isnull().all():
            messagebox.showinfo('Info', 'No historical ping data to show.')
            return
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        # Plot
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax1 = plt.subplots(figsize=(12, 6))
        valid = df['Latency (ms)'] != -1
        ax1.plot(df['Timestamp'][valid], df['Latency (ms)'][valid], label='Latency (ms)', color='tab:blue', marker='o', markersize=3)
        ax1.set_ylabel('Latency (ms)', color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        # Mark lost packets
        lost = df['Latency (ms)'] == -1
        if lost.any():
            ax1.scatter(df['Timestamp'][lost], [0]*lost.sum(), color='red', label='Packet Lost', marker='x', s=40)
        # Plot Packet Loss on secondary axis
        ax2 = ax1.twinx()
        ax2.plot(df['Timestamp'], df['Packet Loss (%)'], label='Packet Loss (%)', color='tab:orange', alpha=0.5, linestyle='--')
        ax2.set_ylabel('Packet Loss (%)', color='tab:orange')
        ax2.tick_params(axis='y', labelcolor='tab:orange')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()
        plt.title('Historical Internet Connection Quality')
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        fig.legend(lines1 + lines2, labels1 + labels2, loc='upper center', ncol=3, frameon=True, fontsize=11, bbox_to_anchor=(0.5, 1.04))
        plt.tight_layout(rect=[0, 0, 1, 0.97])
        plt.show()

if __name__ == '__main__':
    root = tk.Tk()
    app = ConnectionMonitorApp(root)
    root.mainloop()
