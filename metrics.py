import argparse
import time
import csv
import requests
from datetime import datetime

# Prometheus server details
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
METRICS_INTERVAL_SECONDS = 5  # Query every 5 seconds
CSV_FILE = 'queue_size.csv'

# List of metrics to query
METRICS = [
    "tgi_queue_size",
    "tgi_batch_current_size",
    "rate(tgi_request_count[5s])"
]


# Function to query Prometheus for metrics
def query_prometheus(metric_name):
    """Query Prometheus and return the latest value and timestamp for the given metric."""
    query = f"{metric_name}"
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query})
        if response.status_code == 200:
            result = response.json()
            if result['status'] == 'success' and result['data']['result']:
                metric_data = result['data']['result'][0]
                # Check if 'value' or 'values' is present
                if 'value' in metric_data:  # Scalar output
                    timestamp, value = metric_data['value']
                    return float(timestamp), float(value)
                elif 'values' in metric_data:  # Vector output (time series)
                    values = metric_data['values']
                    if values:
                        timestamp, value = values[-1]  # Get the latest timestamp and value
                        return float(timestamp), float(value)
                    else:
                        print(f"No data points found in 'values' for {metric_name}")
            else:
                print(f"No result for query: {metric_name}")
        else:
            print(f"Failed to query Prometheus for {metric_name}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error querying Prometheus for {metric_name}: {e}")
    return None, None


# Function to periodically gather Prometheus metrics and store in CSV
def gather_metrics():
    """Gathers Prometheus metrics every 5 seconds and writes them to a CSV file."""
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)

        # If the file is new, write the header
        if file.tell() == 0:
            writer.writerow(["timestamp", "queue_size", "batch_current_size", "request_rate"])

        while True:
            try:
                print(f"Gathering metrics at {datetime.now()}")

                # Query each metric from Prometheus
                timestamp_data = None
                metrics_data = []
                for metric in METRICS:
                    timestamp, value = query_prometheus(metric)
                    if timestamp_data is None:
                        timestamp_data = timestamp
                    metrics_data.append(value)

                # If valid data is retrieved from Prometheus, write to CSV
                if all(metric is not None for metric in metrics_data):
                    timestamp = datetime.fromtimestamp(timestamp_data)
                    print(f"Timestamp: {timestamp}, Data: {metrics_data}")

                    # Write the data to CSV
                    writer.writerow([timestamp] + metrics_data)
                    file.flush()  # Ensure data is written immediately
                else:
                    print("No data from Prometheus query.")
            except Exception as e:
                print(f"Error gathering metrics: {e}")

            # Wait for 5 seconds before querying again
            time.sleep(METRICS_INTERVAL_SECONDS)


# Entry point for running the script
if __name__ == "__main__":
    global PROMETHEUS_URL, CSV_FILE, METRICS_INTERVAL_SECONDS
    parser = argparse.ArgumentParser("prometheus metrics gathering tool")
    parser.add_argument("-i", "--int", help="polling interval in seconds (5)", type=int)
    parser.add_argument("-o", "--output", help="output file name (queue_size.csv)", type=str)
    parser.add_argument("-u", "--url", help="url of prometheus server", type=str)
    args = parser.parse_args()

    if args.int:
        METRICS_INTERVAL_SECONDS = args.int
    if args.output:
        CSV_FILE = args.output
    if args.url:
        PROMETHEUS_URL = args.url

    gather_metrics()
