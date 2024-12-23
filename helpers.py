import asyncio

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

