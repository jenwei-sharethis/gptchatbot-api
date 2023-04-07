# gptchatbot-api
This API setup a chatbot backed by ChatGPT 3.5 model. With proper initial prompts, this API can trigger assistant mode of ChatGPT with spec and domain knowledge explained in prompt files. 

## Initialize gptchatbot object
`request`: Specify the mode of gptchatbot. Default is "virtual_assistant". Currently this API only have one mode.
`product`: Specify which product to let ChatGPT assistant read relevant prompt files.
`bucket`: Specify the bucket where the initial prompt files are stored on s3.

### Path format of initialization prompt files
* For instruction prompt files, save them under `{bucket}/{product}/init_prompt/instruction/`
* For stage promptfiles, save them under `{bucket}/{product}/init_prompt/{stage}/`

### Structure of initialization prompts
* Instruction prompts: High-level instructions about the background of product, workflow of using a product, and all the do's and don'ts as a virtual assistant.
* Stage prompts: Detailed guideline for chatbot to behave under each stage. Save stage prompt under its own directory respoectively.

You can find a set of example prompt files under `example_prompt` folder.

## Get chatbot response
Use `chatbotResponse(user_input)` to obtain response from virtual assistant ChatGPT./n
`user_input`: str
returns: str

## Move chatbot to next subtask stage
Use `updateChatbotStage(stage)` to notify chatbot move to another subtask stage./n
`stage`: str

For example, the system has detected that a user has uploaded the input file, the UI has changed and been waiting for keyword confirmation. 
Call `updateChatbotStage("keyword")` to make gptchatbot transit into keyword-stage.

## To-do
[2023/04/06]
* Proper comments
* Improve structure
