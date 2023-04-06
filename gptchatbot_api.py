import os
import datetime
import openai
import json
import boto3
import botocore

def s3_upload(bucket, data, folder, timestamp): ##name
    s3Client = boto3.client('s3')
    try:
        s3Client.put_object(
            Body=data,
            Bucket=bucket,
            Key=f'resources/ChatGPT-chatbot/chat-history/{folder}/chat-{timestamp}.json'
        )
    except botocore.exceptions.ClientError as error:
        print(f"Error uploading file to S3: {error}")
        raise


def list_s3_files(bucket, folder):
    s3Client = boto3.client('s3')
    response = s3Client.list_objects_v2(Bucket=bucket, Prefix=folder)
    fileList = []
    for obj in response['Contents']:
        if obj['Key'].endswith(".txt"):
            fileList.append(obj['Key'])
    return fileList

def s3_read_file(bucket, key):
    try:
        s3Client = boto3.resource('s3')
        obj = s3Client.Object(bucket, key)
        body = obj.get()['Body'].read().decode('utf-8')
        return body
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print(f"The object {key} does not exist in {bucket}.")
            raise Exception(f"The object {key} does not exist in {bucket}.")
        else:
            print(f"Error reading file from S3: {e}")
            raise e

class GPTCHATBOT():
    def __init__(self, request='virtual_assistant', product = 'contextual_similarity', bucket='sharethis-daas'):
        openai.api_key = os.environ["GPT_SECRET"]
        self.request = request
        self.product = product
        self.bucket = bucket
        self.chatbot_state = {
            "stage": "introduction",
            "prompts": "",
            "history": "",
            "response": [],
            "prompt_cnt": 0
        }
        self.init_prompt_set = self._loadInitPrompts()
        self.chatbot_state["prompts"] = self.init_prompt_set
        self.prompt_cnt_threshold = 20

    def _callChatGPT(self, prompt):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt
        )
        return response.choices[0].message["content"]

    def _callGPTComplete(self, prompt):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages= [{"role": "user",
                        "content": prompt
                        }]
        )
        return response.choices[0].message["content"]

    def chatbotResponse(self, user_input):
        # input update
        self._updateChatbotState("user", user_input)

        response = self._callChatGPT(
            self.chatbot_state["prompts"]
        )
        self.chatbot_state["response"] = response
        # response update
        self._updateChatbotState("assistant", response)

    def _updateChatbotState(self, role, content):
        self.chatbot_state["prompts"].append({
            "role": role,
            "content": content
        })

        self.chatbot_state["history"] += f"{role}: {content}. "

        self.chatbot_state["prompt_cnt"] += 1

        if self.chatbot_state["prompt_cnt"] > self.prompt_cnt_threshold:
            self._summarizeCurrentPrompt()

    def _loadInitPrompts(self):
        init_prompts = []
        ## load instruction prompts
        instruction_files = {
            "file_content": [],
            "file_name": list_s3_files(self.bucket, self.product + "/init_prompt/instruction/")
        }

        for i in range(len(instruction_files["file_name"])):
            prefix = instruction_files["file_name"][i]
            instruction_files["file_content"].append(s3_read_file(self.bucket, prefix))

        init_prompts.extend(self._processInitPrompts(instruction_files["file_content"]))

        ## load stage prompts
        stage = self.chatbot_state["stage"]
        stage_files = {
            "file_content": [],
            "file_name": list_s3_files(self.bucket, self.product + f"/init_prompt/stage/{stage}/")
        }

        for i in range(len(stage_files["file_name"])):
            prefix = stage_files["file_name"][i]
            stage_files["file_content"].append(s3_read_file(self.bucket, prefix))

        init_prompts.extend(self._processInitPrompts(stage_files["file_content"]))

        return init_prompts

    def _processInitPrompts(self, init_prompt_content):
        init_prompts = []
        for i in range(len(init_prompt_content)):
            init_prompts.append(
                {"role": "system",
                 "content": init_prompt_content[i]}
            )

        return init_prompts

    def _summarizeCurrentPrompt(self):
        self._saveChatHistory()

        response = self._callGPTComplete(
            "To let the next assistant take over the past conversation quickly, can you summarize mainly on user's input in the chat history? Please only provide summary in your response. Here are the conversation history:"
            + self.chatbot_state["history"]
        )

        # update chatbot status with new prompt
        self.chatbot_state["prompts"] = self.init_prompt_set
        self.chatbot_state["history"] = response

        self.chatbot_state["prompts"].append(
            {"role": "system",
             "content": "Here is the summary of previous conversation with the user: " + response.choices[0].text}
        )
        self.chatbot_state["prompts"].append(
            {"role": "system",
             "content": "Now you may continue the conversation with the same user."
            }
        )
        self.chatbot_state["prompt_cnt"] = 0

    def _chatbotWorkflowLogic(self):
        ## contextual similarity ##
        if self.product == "contextual_similarity":
            ## seed_url
            if self.chatbot_state["stage"] == "seed_url":
                print("Please provide a list of seed URLs by clicking Create New Seed button.")
            elif self.chatbot_state["stage"] == "keyword":
                print("Here is a list of recommended keywords from seed URLs. Please review the keywords, remove or add any keywords to the list.")
            elif self.chatbot_state["stage"] == "preview":
                print("Based on the information you provided, here are the example similar URLs from ShareThis data.")
                print("Please choose one of the accuracy options and click Accept to start the full search in one month of data.")

            elif self.chatbot_state["stage"] == "end":
                print("Thank you for using Contextual Similarity platform. The search has started...")
        else:
            print(f"Product workflow {self.product} has not been implemented...")

    def _stageTransit(self):
        self._saveChatHistory()

        ## reset chatbot
        self.init_prompt_set = self._loadInitPrompts()
        self.chatbot_state["prompts"] = self.init_prompt_set
        self.chatbot_state["prompt_cnt"] = 0

        self._chatbotWorkflowLogic()

    def _saveChatHistory(self):
        chat_history = json.dumps(self.chatbot_state["prompts"])
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%H:%M:%S')
        s3_upload(self.bucket, chat_history, self.request, self.chatbot_state["stage"] + timestamp)

    def updateChatbotStage(self, stage):
        self.chatbot_state["stage"] = stage
        try:
            self._stageTransit()
        except:
            print(f"The stage {stage} is not a valid stage for {self.product}!")