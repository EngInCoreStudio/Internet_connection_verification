# Internet Connection Monitor

This project visualizes your internet connection quality using ping and speedtest logs.

## Usage

1. Make sure you have Python and the required libraries:
   ```sh
   pip install pandas matplotlib
   ```
2. Place your ping logs in `connection_logs/ping_results.csv`.
3. Run the monitor:
   ```sh
   python connection_monitor.py
   ```

## Interpreting the Graph
- **Latency (ms):** Blue line, shows ping time. Lower is better.
- **Rolling Average:** Light blue, smooths out spikes.
- **Packet Loss (%):** Orange dashed line, right axis. Should be near 0%.
- **Red X:** Indicates a lost packet (no response).

If you see only lost packets, your connection was down during logging.

## Improving Data
- Run your logger when the connection is up for more meaningful plots.
- Add speedtest results to `connection_logs/speedtest_results.json` for future dashboard features.

---

Feel free to suggest improvements or request a dashboard for speedtest data!
