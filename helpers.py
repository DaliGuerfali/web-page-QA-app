import json
import models
import asyncio

from langchain_core.prompts import ChatPromptTemplate


MAX_TOKEN_OUTPUT = 500
async def chunk_process(model, data: dict, instructions: str):
    if(isinstance(data, Exception)):
        return data

    prompt_template = ChatPromptTemplate([
        ("system", """
         You are a web page quality assurance expert.
         You will be given a chunk of JSON data about a web page. Your task is to modify it according to the following instrctions: 
         {instructions}
         Only output the JSON and minify it, to save on tokens.
         """),
        ("user", "{chunk}")
    ])

    current_token_count = 0
    chunks = []
    currentChunk = {}
    for key in data.keys():
        key_token_count = len(models.encoding.encode(json.dumps(data[key], separators=(',', ':'))))
        if(current_token_count + key_token_count <= MAX_TOKEN_OUTPUT):
           current_token_count += key_token_count
           currentChunk[key] = data[key]
        else:
            chunks.append(currentChunk)
            currentChunk = {}
            current_token_count = 0
            current_token_count += key_token_count
            currentChunk[key] = data[key]

    if(len(currentChunk) > 0):
        chunks.append(currentChunk)
    
    res = await model.abatch([prompt_template.format_messages(chunk=json.dumps(chunk, separators=(',', ':')),instructions=instructions) for chunk in chunks])
    
    return res

def clean_psi_data(data):
    for key in data["lighthouseResult"]["audits"].keys():
        del data["lighthouseResult"]["audits"][key]["id"]
        del data["lighthouseResult"]["audits"][key]["score"]
        if(data["lighthouseResult"]["audits"][key]["scoreDisplayMode"] == 'binary'):
            del data["lighthouseResult"]["audits"][key]["description"]
        del data["lighthouseResult"]["audits"][key]["scoreDisplayMode"]
        if("details" in data["lighthouseResult"]["audits"][key]):
                del data["lighthouseResult"]["audits"][key]["details"]
    
    temp =  {"loadingExperience": data["loadingExperience"]["metrics"]}
    temp["audits"] = data["lighthouseResult"]["audits"]
    return temp

async def run_parallel_tasks(tasks: dict):
    keys = list(tasks.keys())
    coroutines = [asyncio.gather(*tasks[key]) if isinstance(tasks[key], list) else tasks[key] for key in keys]
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    return {keys[i]: results[i] for i in range(len(keys))}

def flatten(xss):
    return [x for xs in xss for x in xs]

