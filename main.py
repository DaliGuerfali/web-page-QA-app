import os
import json
import asyncio
import tiktoken
from lru import LRU
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from apis import async_PSI, validate_css, validate_html
from helpers import run_parallel_tasks, flatten


MAX_CACHE_SIZE = 100
MODEL = "gpt-4o"
MAX_TOKEN_OUTPUT = 500


load_dotenv()
PSI_API_KEY = os.getenv("PSI_API_KEY")
templates = Jinja2Templates(directory="templates")

data_cache = LRU(MAX_CACHE_SIZE)

encoding = tiktoken.encoding_for_model(MODEL)
generic_model = ChatOpenAI(model=MODEL, streaming=False)
audit_model = ChatOpenAI(model=MODEL, streaming=False).with_structured_output({
  "name": "get_audits",
  "description": "Processes audits from Page Speed Insights",
  "strict": True,
  "schema": {
      "type": "object",
      "properties": {
          "audits": {
              "type": "array",
              "description": "A list of audits, each classified and with details formatted",
              "items": {
                  "type": "object",
                  "properties": {
                      "title": {
                            "type": "string",
                            "description": "The title of the audit"
                        },
                        "description": {
                            "type": "string",
                            "description": "The description of the audit, with links removed"
                        },
                        "displayValue": {
                            "type": ["string", "null"],
                            "description": "The value to be displayed"
                        },
                        "numericValue": {
                            "type": ["string", "null"],
                            "description": "Readable format combining numericValue and numericUnit, if present"
                        },
                        "metricSavings": {
                            "type": ["object", "null"],
                            "description": "Null if not present or if the values are zeros",
                            "properties": {
                                "LCP": {
                                    "type": ["string", "null"],
                                    "description": "Largest Contentful Paint"
                                },
                                "CLS": {
                                    "type": ["string", "null"],
                                    "description": "Cumulative Layout Shift"
                                },
                                "FID": {
                                    "type": ["string", "null"],
                                    "description": "First Input Delay"
                                },
                                "FCP": {
                                    "type": ["string", "null"],
                                    "description": "First Contentful Paint"
                                },
                            },
                            "additionalProperties": False,
                            "required": ["LCP", "CLS", "FID", "FCP"]
                        },
                        "class": {
                            "type": "string",
                            "enum": ["good", "bad", "neutral"],
                            "description": "Classifies the audit as 'good', 'bad', or 'neutral'"
                        }
                  },
                  "additionalProperties": False,
                  "required": ["title", "description", "displayValue", "metricSavings", "numericValue", "class"]
              }
          }
      },
      "additionalProperties": False,
      "required": ["audits"]
  }
}, method="json_schema")
html_validation_model = ChatOpenAI(model=MODEL, streaming=False).with_structured_output({
  "name": "get_html_validation",
  "description": "Processes HTML Validation data.",
  "strict": True,
  "schema": {
      "type": "object",
      "properties": {
          "errors": {
              "type": "array",
              "description": "A list of html errors.",
              "items": {
                  "type": "object",
                  "properties": {
                      "position": {
                            "type": ["string", "null"],
                            "description": "the position of the error in the file"
                        },
                        "message": {
                            "type": "string",
                            "description": "The the message of the error."
                        }
                  },
                  "additionalProperties": False,
                  "required": ["position", "message"]
              }
          }
      },
      "additionalProperties": False,
      "required": ["errors"]
  }
}, method="json_schema")
css_validation_model = ChatOpenAI(model=MODEL, streaming=False).with_structured_output({
  "name": "get_css_validation",
  "description": "Processes CSS validation data",
  "strict": True,
  "schema": {
      "type": "object",
      "properties": {
          "files": {
              "type": "array",
              "description": "A list of CSS files, each containing error types and their counts",
              "items": {
                  "type": "object",
                  "properties": {
                      "fileName": { 
                            "type": "string", 
                            "description": "The name of the CSS file" 
                            },
                      "errors": {
                            "type": "array",
                            "description": "A list of error types and their counts",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "The type of the error, make it user-friendly and non ambiguous, this will be displayed in a website"
                                    },
                                    "count": {
                                        "type": "integer",
                                        "description": "The number of errors of this type, in this file"
                                    },
                                    "description": {
                                        "type": ["string", "null"],
                                        "description": "If an error type is not clear, provide a description, otherwise set it to null"
                                    }
                                },
                                "additionalProperties": False,
                                "required": ["error", "count", "description"]
                            },
                      },
                  },
                    "additionalProperties": False,
                    "required": ["fileName", "errors"]
              }
          }
      },
      "additionalProperties": False,
      "required": ["files"]
  }
}, method="json_schema")

app = FastAPI()

@app.get("/")
async def read_root(request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse(
        request=request, name="home.html")
        

@app.post("/analyze")
async def generateReport(request: Request, response_class=HTMLResponse):
    form_data = await request.form()
    url = form_data.get("url")
    
    data = None
    if data_cache.has_key(url):
        data = data_cache[url]
    else:
        data = await get_report_data(url)
        data_cache[url] = data

    return templates.TemplateResponse(
        request=request, name="home.html", context={"data": data, "URL": url})


async def get_report_data(URL):
    json_data = [
            async_PSI(url=URL, api_key=PSI_API_KEY, category="performance"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="seo"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="accessibility"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="best_practices"),
            validate_html(URL),
            validate_css(URL),
        ]

    results = await asyncio.gather(*json_data, return_exceptions=True)

    chunk_prompt = ChatPromptTemplate([
        ("system", """
         You are a web page quality assurance expert.
         You will be given a chunk of JSON data about a web page. Your task is to modify it according to the following instrctions: 
         {instructions}
         Only output the JSON and minify it, to save on tokens.
         """),
        ("user", "{chunk}")
    ])

    audit_instructions = """ 
    The data will be audits of Page Speed Insights.
    Remember to process every audit, and output them in the structure you were given.
    And remove audits that do not provide any value. 
    For example: 
    "main-thread-tasks": {
            "title": "Tasks",
            "description": "Lists the toplevel main thread tasks that executed during page load."
        },
    Audits like this should be removed.
    Audits about loading experience metrics such as LCP, FID, CLS, or FCP should be removed.
    """

    html_validation_instructions = """
    The data will be HTML validation data.
    Make sure to process every error, and output them in the structure you were given.
    Make the errors user-friendly and non-ambiguous.
    Combine lastline and lastcol into 'position', if they exist otherwise set position to null.
    """

    css_validation_instructions = """
    The data will be CSS validation data.
    Make sure to process every file and error type, and output them in the structure you were given.
    Make the error types user-friendly and non-ambiguous.    
    If an error type is not clear, provide a description for it. Do not repeat what is already in the title of the error, avoid redundancy.
    If an error type is clear, set the description to null.
"""

    summary_prompt = ChatPromptTemplate([
            ("system", """You are a web page quality assurance expert.
    You will be given JSON data about a web page. Your task is to generate a short summary of the data.
    This should be a high level overview of the data, and should be easy to understand.
    It's going to be a paragraph shown in a website, so make it user friendly.
    Do not mention anything about loading experience metrics such as LCP, FID, CLS, or FCP.
    Only output the text, to save on tokens.
    """),
    ("user", """This is data about the {category} aspects of the page. {json_data}""")
])
    

    categories = ["Performance", "SEO", "Accessibility", "Best Practices", "HTML Validation", "CSS Validation"]

    summaries = [summarize(results[i],categories[i], summary_prompt) for i in range(0, len(results))]
    audit_chunking = [chunk_process(audit_model,results[i], chunk_prompt, audit_instructions) for i in range(0, 4)]
    
    
    parallel_tasks = {
        "summaries": summaries,
        "audit_chunking": audit_chunking,
        "html_chunking": chunk_process(html_validation_model, results[4], chunk_prompt, html_validation_instructions),
        "css_chunking": chunk_process(css_validation_model, results[5], chunk_prompt, css_validation_instructions)
    }

    final_results = await run_parallel_tasks(parallel_tasks)
    
    handle_errors(final_results, categories)
             
    return create_final_data(final_results, results, categories)
    
def handle_errors(final_results, categories):
    if(isinstance(final_results["summaries"], Exception)):
        final_results["summaries"] = ["Could not retrieve summary for this section." for i in range(0, 6)]
    else:
        for summary in final_results["summaries"]:
            if isinstance(summary, Exception):
                summary = "Could not retrieve summary for this section."
    
    if(isinstance(final_results["audit_chunking"], Exception)):
        final_results["audit_chunking"] = [f"Could not retrieve {categories[i]} data." for i in range(0, 4)]
    else:
        for i in range(0, 4):
            if(isinstance(final_results["audit_chunking"][i], Exception)):
                final_results["audit_chunking"][i] = f"Could not retrieve {categories[i]} data."
            else:
                final_results["audit_chunking"][i] = flatten([final_results["audit_chunking"][i][j]["audits"] for j in range(0, len(final_results["audit_chunking"][i]))])
        

    if(isinstance(final_results["html_chunking"], Exception)):
        final_results["html_chunking"] = "Could not retrieve HTML validation data."
    else:
        final_results["html_chunking"] = flatten([final_results["html_chunking"][i]["errors"] for i in range(0, len(final_results["html_chunking"]))])

    if(isinstance(final_results["css_chunking"], Exception)):
        final_results["css_chunking"] = "Could not retrieve CSS validation data."
    else:
        final_results["css_chunking"] = flatten([final_results["css_chunking"][i]["files"] for i in range(0, len(final_results["css_chunking"]))])

def get_loading_experience(results):
    res = "Could not retrieve loading experience data."
    for i in range(0, 4):
        if(not isinstance(results[i], Exception)):
            res = results[i]["loadingExperience"]
            del results[i]["loadingExperience"]
            results[i] = results[i]["audits"]
    return res

def get_error_count(results):
    res = None
    if(len(results) > 5 and not isinstance(results[5], Exception)):
        res = results[5]["errorCount"]
        del results[5]["errorCount"]
    return res

def create_final_data(final_results, results, categories):
    data = {
        "psi_sections": [],
        "loading_section": get_loading_experience(results)
    }

    for i in range(0, 4):
        data["psi_sections"].append({
            "title": categories[i],
            "summary": final_results["summaries"][i],
            "audits": final_results["audit_chunking"][i]
        })
    
    data["html_section"] = {
        "summary": final_results["summaries"][4],
        "errors": final_results["html_chunking"]
    }

    data["css_section"] = {
        "summary": final_results["summaries"][5],
        "files": final_results["css_chunking"],
        "errorCount": get_error_count(results)
    }
    return data

async def summarize(data: dict, category: str, prompt: ChatPromptTemplate):
    if(isinstance(data, Exception)):
        return f"Could not retrieve {category} data."

    res = await generic_model.ainvoke(prompt.format_messages(category=category, json_data=json.dumps(data, separators=(',', ':'))))
    return res.content

async def chunk_process(model, data: dict, prompt: ChatPromptTemplate, instructions: str):
    if(isinstance(data, Exception)):
        return data

    current_token_count = 0
    chunks = []
    currentChunk = {}
    for key in data.keys():
        key_token_count = len(encoding.encode(json.dumps(data[key], separators=(',', ':'))))
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
    
    res = await model.abatch([prompt.format_messages(chunk=json.dumps(chunk, separators=(',', ':')),instructions=instructions) for chunk in chunks])
    
    return res



