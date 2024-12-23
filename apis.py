import httpx
import asyncio
from PythonPSI.api import PSI
from helpers import clean_psi_data

async def async_PSI(url, api_key, category):
    res = await asyncio.to_thread(PSI, url, api_key, category)
    res = clean_psi_data(res)
    return res

async def validate_html(URL):
    async with httpx.AsyncClient() as client:
        try:    
            response = await client.get("https://validator.w3.org/nu/", params={"out": "json", "doc": URL, "level": "error"})
            
            json_data = response.json()
    
            for message in json_data["messages"]:
                if "hiliteStart" in message:
                    del message["hiliteStart"]

                if "hiliteLength" in message:
                    del message["hiliteLength"]

                if "extract" in message:
                    del message["extract"]
                del message["type"]
            del json_data["url"]
            return json_data
        except Exception as e:
            print(e)
            return e

async def validate_css(URL):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("https://jigsaw.w3.org/css-validator/validator",
                params={"uri": URL,
                "warning": "no",
                "lang": "en",
                "usermedium": "all",
                "profile": "css3svg",
                "output": "json"})
            
                json_data = response.json()

                errors = {}

                for error in json_data.get("cssvalidation", {}).get("errors", []):
                    source = error["source"].split("/")[-1]
                    message = error["message"]
                    context = error["context"]
                    
                    if source not in errors:
                        errors[source] = {}
                    if message not in errors[source]:
                        errors[source][message] = []
                    errors[source][message].append(context)
                
                for key in errors.keys():
                    for key2 in errors[key].keys():
                        errors[key][key2] = len(errors[key][key2])
                errors["errorCount"] = json_data.get("cssvalidation", {}).get("result", {}).get("errorcount", 0)
                return errors
            except Exception as e:
                print(e)
                return e