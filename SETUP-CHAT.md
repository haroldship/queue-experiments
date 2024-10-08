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
7. Connect browser to chatbot at [http://localhost:5173]()

## TBD: next steps
- [x] configure and run prometheus (docker)
- [ ] figure out how to specify number of GPUs
- [x] write a test driver - need strings, distributions
- [ ] get data and save it, perhaps use S3
- [x] estimate $\hat{\mu}$
- [ ] consider running in experiment from another instance or even from local machine


[^chat-ui]: [https://github.com/huggingface/chat-ui](https://github.com/huggingface/chat-ui)
