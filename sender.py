import aiohttp
import asyncio
import random
import time
import numpy as np

# Inference server details
INFERENCE_URL = "http://127.0.0.1:8080/generate"

# Number of requests to send
NUM_REQUESTS = 20_000  # 20,000 requests

# Mean wait time in microseconds (100 microseconds)
MEAN_WAIT_TIME_MICROSECONDS = 100e-6

# Zipf distribution parameters
ZIPF_PARAM = 2.0  # Zipf distribution parameter
MAX_TOKENS_RANGE = 8000  # Maximum range of tokens
MIN_TOKENS = 5  # Minimum number of tokens

# List of 100 tourist points of interest
POINTS_OF_INTEREST = [
    "Eiffel Tower, Paris", "Statue of Liberty, New York", "Great Wall of China",
    "Colosseum, Rome", "Machu Picchu, Peru", "Sydney Opera House, Sydney",
    "Taj Mahal, India", "Mount Fuji, Japan", "Christ the Redeemer, Rio de Janeiro",
    "Big Ben, London", "Grand Canyon, Arizona", "Santorini, Greece",
    "Niagara Falls, Canada/USA", "The Louvre, Paris", "Forbidden City, Beijing",
    "Burj Khalifa, Dubai", "Golden Gate Bridge, San Francisco", "Mount Kilimanjaro, Tanzania",
    "Pyramids of Giza, Egypt", "Acropolis, Athens", "Table Mountain, South Africa",
    # (more points can be added as needed up to 100)
]

# Pre-compute max_tokens using Zipf distribution for all requests
precomputed_max_tokens = [max(np.random.zipf(ZIPF_PARAM), MIN_TOKENS) for _ in range(NUM_REQUESTS)]

# Pre-compute sleep times using exponential distribution with mean 100 microseconds for all requests
precomputed_sleep_times = [random.expovariate(1 / MEAN_WAIT_TIME_MICROSECONDS) for _ in range(NUM_REQUESTS)]

# Function to send a request to the inference server
async def send_request(session, prompt, max_tokens):
    """Sends a POST request to the Hugging Face inference server."""
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens
        }
    }
    
    try:
        async with session.post(INFERENCE_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Response: {data}")
            else:
                print(f"Request failed with status: {response.status}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Function to run the requests with precomputed max tokens and sleep times
async def run_requests():
    """Runs the loop to send requests with precomputed delays and max tokens."""
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()  # Track the start time

        for i in range(NUM_REQUESTS):
            max_tokens = precomputed_max_tokens[i]
            prompt = f"Tell me more about {random.choice(POINTS_OF_INTEREST)}."
            
            # Schedule the request
            task = asyncio.create_task(send_request(session, prompt, max_tokens))
            tasks.append(task)
            
            # Wait for the precomputed sleep time
            await asyncio.sleep(precomputed_sleep_times[i])
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        end_time = time.time()  # Track the end time
        total_time_taken = end_time - start_time
        print(f"Total number of requests sent: {NUM_REQUESTS}")
        print(f"Total time taken: {total_time_taken:.2f} seconds")

# Main function to run requests
async def main():
    """Runs the requests."""
    await run_requests()

# Entry point for running the async requests
if __name__ == "__main__":
    asyncio.run(main())

