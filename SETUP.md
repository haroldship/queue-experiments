## Goal
The goal is to run an LLM on Amazon cloud such that I can write code to generate requests at a high rate and measure the performance of the LLM's response.

## Expected result
The end result should be an LLM model such as llama or mistral running inference on the cloud with a corresponding chatbot.

## Sources
How to run Mistral 7B Model with Chat-UI💬 on Amazon EC2 [^how-to-run-mistral]

[^how-to-run-mistral]: [https://medium.com/@dminhk/how-to-run-mistral-7b-model-with-chat-ui-on-amazon-ec2-eef6554cd456](https://medium.com/@dminhk/how-to-run-mistral-7b-model-with-chat-ui-on-amazon-ec2-eef6554cd456)

## Amazon instance details
- Image: "Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.3 (Ubuntu 20.04)" (ami-0c24c447880015773)[^deep-learning-ami]
- g5.xlarge instance, see instance comparison tool [^instance-comparison-tool]
![[attachments/Pasted image 20240925112857.png]]
- key pair: created new `harold-aws-rsa`
- ssh, 8080 ports open
- 512GB storage

[^deep-learning-ami]: [https://docs.aws.amazon.com/dlami/latest/devguide/appendix-ami-release-notes.html](https://docs.aws.amazon.com/dlami/latest/devguide/appendix-ami-release-notes.html)

[^instance-comparison-tool]: [https://eu-north-1.console.aws.amazon.com/ec2/home?region=eu-north-1#InstanceTypes:v=3;gpus=%3E0;sort=default-otherLinux](https://eu-north-1.console.aws.amazon.com/ec2/home?region=eu-north-1#InstanceTypes:v=3;gpus=%3E0;sort=default-otherLinux)

# Summary of steps
- Create an Amazon EC2 Instance running: Mistral 7B Instruct model in TGI container using Docker and AWQ Quantization
- Install and run Chat-UI
- Run prometheus
- Run queries

## Create an instance running tgis
The following are from [^how-to-run-mistral] with modifications indicated.

1. Create an EC2 instance with image `ami-0c24c447880015773` (Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.3 (Ubuntu 20.04)), with instance type `g5.xlarge`, 512GB of storage, and a new or existing keypair  for ssh, and ssh and 8080 ports open
2. Log in to the instance: `$ ssh -i "~/secrets/harold-aws-rsa.pem" ubuntu@ec2-16-171-8-83.eu-north-1.compute.amazonaws.com` - this one runs tgi
3. Set up a docker network so that prometheus can scrape tgis:
```bash
$ docker network create param-est 
```
4. Start docker container of tgis running mistral-7b with AWQ quantization:
```bash
$ model=TheBloke/Mistral-7B-Instruct-v0.1-AWQ
$ volume=$PWD/data
$ docker run --gpus all --shm-size 1g -d -p 8080:80 -v $volume:/dat --name tgis --network param-est ghcr.io/huggingface/text-generation-inference:latest --model-id $model --quantize awq --max-input-length 8191 --max-total-tokens 8192 --max-batch-prefill-tokens 8191
```


## Run Prometheus 
1. Log in a third session: `$ ssh -i "~/secrets/harold-aws-rsa.pem" ubuntu@ec2-16-171-8-83.eu-north-1.compute.amazonaws.com`
2. Create a directory and config file for prometheus
```bash
$ mkdir prometheus`
$ cd prometheus/
```
2. Create `prometheus.yml` with the following contents:
```yaml
# my global config
global:
  scrape_interval: 15s # Set the scrape interval to every 15 seconds. Default is every 1 minute.
  evaluation_interval: 15s # Evaluate rules every 15 seconds. The default is every 1 minute.
  # scrape_timeout is set to the global default (10s).

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: "prometheus"

    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.

    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "tgis"
    scrape_interval: 1s
    static_configs:
      - targets: ["tgis:80"]

```
   3. Run prometheus docker container:
```bash
$ docker run -d -p 9090:9090 \
-v ${PWD}/prometheus.yml:/etc/prometheus/prometheus.yml \
--name prometheus \
--network param-est \
prom/prometheus
```
4. Check prometheus in browser at [http://localhost:9090](http://localhost:9090)

## Run experiments
1. Start a fourth session - this one is on same instance for now
2. Create a directory and install prerequisites
```bash
$ mkdir experiments
$ cd experiments/
$ pip install aiohttp numpy requests
```
3. Copy the code below into experiments.py:
```python

```

## Install and run chat-ui
1. Log in a second session - this one runs chat-ui
2. Query the GPU:
```bash
$ nvidia-smi --query-gpu=name,gpu_bus_id,memory.total,memory.used --format=csv

name, pci.bus_id, memory.total [MiB], memory.used [MiB]
NVIDIA A10G, 00000000:00:1E.0, 23028 MiB, 18506 MiB

$ nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

pid, process_name, used_gpu_memory [MiB]
29200, /opt/conda/bin/python3.11, 18498 MiB
```
3. Install chatui[^chat-ui]
```bash
# Clone the repo  
$ git clone https://github.com/huggingface/chat-ui  
  
# Start a Mongo Database  
$ docker run -d -p 27017:27017 --name mongo-chatui mongo:latest  
  
# install nvm & npm  
$ wget https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh  
$ bash install.sh  
  
# Close and reopen your terminal to start using nvm or run the following to use it now:  
$ export NVM_DIR="$HOME/.nvm"  
$ [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm  
$ [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion  
  
# nvm install node  
$ nvm install node  
$ npm --version  
10.8.3
  
# npm install  
$ cd chat-ui  
$ npm install
```
4. In the same session, create a file `.env.local` with the following content ==Note: this is different than original in that then endpoint.type is specified as "tgi"==:
```bash
MONGODB_URL=mongodb://localhost:27017/  
PUBLIC_APP_NAME="Mistral 7B Instruct Chat UI 💬"  
PUBLIC_APP_ASSETS=chatui  
PUBLIC_APP_COLOR=yellow  
  
MODELS=`[
{  
	"name": "mistralai/Mistral-7B-Instruct-v0.1",  
	"displayName": "mistralai/Mistral-7B-Instruct-v0.1",  
	"description": "Mistral 7B is a new Apache 2.0 model, released by Mistral AI that outperforms Llama2 13B in benchmarks.",  
	"websiteUrl": "https://mistral.ai/news/announcing-mistral-7b/",  
	"preprompt": "",  
	"chatPromptTemplate" : "<s>{{#each messages}}{{#ifUser}}[INST] {{#if @first}}{{#if @root.preprompt}}{{@root.preprompt}}\n{{/if}}{{/if}}{{content}} [/INST]{{/ifUser}}{{#ifAssistant}}{{content}}</s>{{/ifAssistant}}{{/each}}",  
	"parameters": {  
		"temperature": 0.1,  
		"top_p": 0.95,  
		"repetition_penalty": 1.2,  
		"top_k": 50,  
		"truncate": 1000,  
		"max_new_tokens": 2048,  
		"stop": ["</s>"]  
	},  
	"promptExamples": [  
	{  
	"title": "Write an email from bullet list",  
	"prompt": "As a restaurant owner, write a professional email to the supplier to get these products every week: \n\n- Wine (x10)\n- Eggs (x24)\n- Bread (x12)"  
	}, {  
	"title": "Code a snake game",  
	"prompt": "Code a basic snake game in python, give explanations for each step."  
	}, {  
	"title": "Assist in a task",  
	"prompt": "How do I make a delicious lemon cheesecake?"  
	}  
	],  
	"endpoints": [{
		"type": "tgi",
		"url": "http://127.0.0.1:8080"  
	}]  
}  
]`
```
5. Run chat-ui: `$ npm run dev`
6. In another terminal, open chat-ui and prometheus ports to localhost using ssh tunnel: `$ ssh -i "~/secrets/harold-aws-rsa.pem" -N -L 5173:localhost:5173 -L 9090:localhost:9090 ubuntu@ec2-16-171-8-83.eu-north-1.compute.amazonaws.com`
7. Connect browser to chatbot at [http://localhost:5173]()

## TBD: next steps
- [x] configure and run prometheus (docker)
- [ ] figure out how to specify number of GPUs
- [x] write a test driver - need strings, distributions
- [ ] get data and save it, perhaps use S3
- [x] estimate $\hat{\mu}$
- [ ] consider running in experiment from another instance or even from local machine


[^chat-ui]: [https://github.com/huggingface/chat-ui](https://github.com/huggingface/chat-ui)


## References