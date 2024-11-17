from datetime import datetime
import os
import subprocess


def run_experiment(poll_interval=5, q_fname="queue_size.csv", prom_url="http://localhost:9090/api/v1/query", num_clients="1",
                   num_requests_per_client=20_000, rt_fname="round_trips.csv", max_output_tokens=100,
                   inf_url="http://127.0.0.1:8080/generate", mean_interarrival_micro_s=1_000_000):

    print(f"Starting metrics.py to {q_fname}")
    metrics_args = ["python", "metrics.py", "-i", str(poll_interval), "-o", q_fname, "-u", prom_url]
    metrics_process = subprocess.Popen(metrics_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    sender_args = ["python", "sender.py", "-C", str(num_clients), "-n", str(num_requests_per_client), "-o",
                   rt_fname, "-t", str(max_output_tokens), "-u",
                   inf_url, "-w", str(mean_interarrival_micro_s)]

    try:
        print(f"Running sender.py to {rt_fname}")
        subprocess.run(sender_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"sender.py exited with an error: {e}")
    finally:
        print("Terminating metrics.py...")
        metrics_process.terminate()

        try:
            metrics_process.wait(timeout=5)  # Wait for it to terminate
            print("metrics.py terminated successfully.")
        except subprocess.TimeoutExpired:
            print("metrics.py did not terminate in time, killing it forcefully.")
            metrics_process.kill()


if __name__ == "__main__":
    Cs = [1, 2, 4, 8]
    ts = [100]
    ws = [50_000, 100_000, 200_000, 400_000, 800_000]
    date_dname = "data_" + datetime.now().strftime("%d%b")
    if not os.path.exists(date_dname):
        os.makedirs(date_dname)

    for C in Cs:
        for t in ts:
            for w in ws:
                n = 800_000 // w * 60
                name_part = f'C{C}_w{w}_t{t}_n{n}'
                q_fname = f'{date_dname}/queue_size_{name_part}.csv'
                rt_fname = f'{date_dname}/round_trips_{name_part}.csv'
                run_experiment(q_fname=q_fname, num_clients=C, num_requests_per_client=n, max_output_tokens=t,
                               mean_interarrival_micro_s=w, rt_fname=rt_fname)