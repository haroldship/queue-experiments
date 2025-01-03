import atexit
import time
from datetime import datetime
import os
import subprocess
import inspect
import yaml
import argparse


def print_parameters():
    frame = inspect.currentframe().f_back
    args, _, _, values = inspect.getargvalues(frame)
    print(" ".join(f"{arg}={repr(values[arg])}" for arg in args))


def run_experiment(mc=1, poll_interval=5, q_fname="queue_size.csv", prom_url="http://localhost:9090/api/v1/query",
                   num_clients="1", num_requests_per_client=20_000, rt_fname="round_trips.csv", max_output_tokens=100,
                   inf_url="http://127.0.0.1:8080/generate", mean_interarrival_micro_s=1_000_000):
    print_parameters()
    print(f"Starting metrics.py to {q_fname}")
    metrics_args = ["python", "metrics.py", "-i", str(poll_interval), "-o", q_fname, "-u", prom_url]
    metrics_process = subprocess.Popen(metrics_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    atexit.register(metrics_process.terminate)

    seed = mc * 100
    sender_args = ["python", "sender.py", "-C", str(num_clients), "-n", str(num_requests_per_client), "-o", rt_fname,
                   "-t", str(max_output_tokens), "-u", inf_url, "-w", str(mean_interarrival_micro_s), "-s", str(seed)]

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
            atexit.unregister(metrics_process.terminate)


def ensure_docker_network_exists(network_name):
    """Ensure that a Docker network exists; create it if it does not."""
    try:
        # Check if the network already exists
        result = subprocess.run(
            ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        existing_networks = result.stdout.splitlines()

        if network_name not in existing_networks:
            # Create the network if it does not exist
            subprocess.run(["docker", "network", "create", network_name], check=True)
            print(f"Docker network '{network_name}' created.")
        else:
            print(f"Docker network '{network_name}' already exists.")
    except subprocess.CalledProcessError as e:
        print(f"Error managing Docker network '{network_name}': {e}")


def stop_and_remove_container(container_name):
    """Stop and remove the Docker container."""
    print(f"Stopping and removing container '{container_name}'.")
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        existing_networks = result.stdout.splitlines()

        if container_name in existing_networks:
            # Stop the container if it's running
            subprocess.run(["docker", "stop", container_name], check=True)
            print(f"Container '{container_name}' stopped.")

            # Remove the container
            subprocess.run(["docker", "rm", container_name], check=True)
            print(f"Container '{container_name}' removed.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping or removing the container '{container_name}': {e}")


def run_docker_container(max_batch_size=1):
    """Run the Docker container."""
    model = "TheBloke/Mistral-7B-Instruct-v0.1-AWQ"
    volume = os.path.join(os.getcwd(), "data")
    docker_image = "ghcr.io/huggingface/text-generation-inference:latest"
    container_name = "tgis"
    network = "param-est"

    # Ensure the Docker network exists
    ensure_docker_network_exists(network)

    # Build the docker command
    docker_command = [
        "docker", "run",
        "--gpus", "\"device=0\"",
        "-e", "CUDA_VISIBLE_DEVICES=0",
        "-e", "MAX_CONCURRENT_REQUESTS=1000",
        "--shm-size", "1g",
        "-d",
        "-p", "8080:80",
        "-v", f"{volume}:/dat",
        "--name", container_name,
        "--network", network,
        docker_image,
        "--model-id", model,
        "--quantize", "awq",
        "--max-concurrent-requests", "1000",
        "--max-input-tokens", "16385",
        "--max-total-tokens", "32768",
        "--max-batch-prefill-tokens", "16385",
        "--max-batch-size", str(max_batch_size),
        "--disable-custom-kernels"
    ]

    try:
        print(f"Starting docker container: {docker_command}.")
        res = subprocess.run(docker_command, check=True)
        if res.returncode == 0:
            print("Docker container started successfully.")
            return container_name
        else:
            print(f"Error while starting the Docker container: {res.stderr}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error while starting the Docker container: {e}")
        return None


def wait_for_container(container_name, check_word='Connected', timeout=120):
    start_time = time.time()
    while True:
        log_cmd = ["docker", "logs", container_name]
        logs_result = subprocess.run(log_cmd, capture_output=True, text=True)

        if check_word in logs_result.stdout:
            print(f"'{check_word}' found in logs. Proceeding...")
            return True

        if time.time() - start_time > timeout:
            print(f"Timeout waiting for '{check_word}' in logs.")
            return False

        time.sleep(1)  # Check logs every second


# Main process
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="experiment runner")
    parser.add_argument("-c", help="config file name (config.yaml)", type=str, default='config.yaml')
    parser.add_argument("-r", help="replica number", type=int, default=1)
    parser.add_argument("-m", help="number of monte carlo simulations", type=int, default=1)

    args = parser.parse_args()

    config_file = args.c
    replicas = args.r
    MC = args.m

    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    date_dname = f'data_{datetime.now().strftime("%d%b")}'
    if not os.path.exists(date_dname):
        os.makedirs(date_dname)

    batch_sizes = config.get('batch_sizes', [1])
    num_clients = config.get('num_clients', [1])
    max_output_tokens = config.get('max_output_tokens', [200])
    lambdas = config.get('lambdas', [0.1, 0.7, 1.0, 1.4, 2.0])
    ws = [int(1_000 / lam) * 1_000 for lam in lambdas]
    deltas = config.get('deltas', [2])

    atexit.register(stop_and_remove_container, 'tgis')

    for B in batch_sizes:

        container_name = run_docker_container(max_batch_size=B)
        if container_name is None:
            print('failed to start container!')
            break

        print(f'waiting for container with max-batch-size={B} to be ready...')
        ok = wait_for_container(container_name)
        if not ok:
            print('failed to start tgi server')
            break

        for C in num_clients:
            for t in max_output_tokens:
                for w in ws:
                    for d in deltas:
                        for mc in range(1, MC + 1):
                            n = max(110, 16 * 60 * 1_000_000 // w // C)
                            name_part = f'MB_{B}_C{C}_w{w}_t{t}_n{n}_d{d}_mc_{mc}'
                            q_fname = f'{date_dname}/queue_size_{name_part}.csv'
                            rt_fname = f'{date_dname}/round_trips_{name_part}.csv'
                            run_experiment(q_fname=q_fname, num_clients=C, num_requests_per_client=n,
                                           max_output_tokens=t, poll_interval=d, mean_interarrival_micro_s=w,
                                           rt_fname=rt_fname, mc=mc)

        if container_name:
            stop_and_remove_container(container_name)
            time.sleep(10)
