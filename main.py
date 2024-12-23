import os
import json
import httpx
import models
import asyncio
import textstat
from lru import LRU
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from helpers import run_parallel_tasks, flatten

from apis import async_PSI, check_for_dead_links, extract_text_and_links, validate_css, validate_html
from llm_tasks import process_audits, process_html_validation, process_css_validation, analyze_content, summarize

MAX_CACHE_SIZE = 100

load_dotenv()
PSI_API_KEY = os.getenv("PSI_API_KEY")
templates = Jinja2Templates(directory="templates")

data_cache = LRU(MAX_CACHE_SIZE)

app = FastAPI()

@app.get("/")
async def read_root(request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse(
        request=request, name="home.html")
        

@app.post("/analyze")
async def generateReport(request: Request, response_class=HTMLResponse):
    form_data = await request.form()
    url = form_data.get("url")
    
    async with httpx.AsyncClient() as client:
        try:
            await client.get(url)
        except Exception as e:
            return templates.TemplateResponse(
                request=request, name="home.html", context={"error": "Please enter a valid URL."})
    

    data = None
    if data_cache.has_key(url):
        data = data_cache[url]
    else:
        data = await get_report_data(url)
        data_cache[url] = data

    return templates.TemplateResponse(
        request=request, name="home.html", context={"data": data, "URL": url})


async def get_report_data(URL):
    extracted_text, links = extract_text_and_links(URL)

    dead_link_count = check_for_dead_links(links)

    api_calls = [
            async_PSI(url=URL, api_key=PSI_API_KEY, category="performance"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="seo"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="accessibility"),
            async_PSI(url=URL, api_key=PSI_API_KEY, category="best_practices"),
            validate_html(URL),
            validate_css(URL),
        ]

    api_call_results = await asyncio.gather(*api_calls, return_exceptions=True)
    summary_categories = ["Performance", "SEO", "Accessibility", "Best Practices", "HTML Validation", "CSS Validation"]
    summaries = [summarize(api_call_results[i],summary_categories[i]) for i in range(0, len(api_call_results))]

    api_call_map = {
        "psi": [api_call_results[i] for i in range(0, 4)],
        "html": api_call_results[4],
        "css": api_call_results[5]
    }

    parallel_tasks = {
        "summaries": summaries,
        "audit_chunking": process_audits(api_call_map),
        "html_chunking": process_html_validation(api_call_map),
        "css_chunking": process_css_validation(api_call_map),
        "content_analysis": analyze_content(extracted_text),
        "dead_link_count": dead_link_count
    }

    final_results = await run_parallel_tasks(parallel_tasks)
    
    handle_errors(final_results, summary_categories)
             
    return create_final_data(final_results, api_call_map, summary_categories)
    
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

    if(isinstance(final_results["content_analysis"], Exception)):
        final_results["content_analysis"] = "Could not analyze content."

    if(isinstance(final_results["dead_link_count"], Exception)):
        final_results["dead_link_count"] = "Could not check for dead links."

def get_loading_experience(result_map):
    res = "Could not retrieve loading experience data."
    for i in range(0, 4):
        if(not isinstance(result_map["psi"][i], Exception)):
            res = result_map["psi"][i]["loadingExperience"]
            del result_map["psi"][i]["loadingExperience"]
            result_map["psi"][i] = result_map["psi"][i]["audits"]
    return res

def get_error_count(result_map):
    res = None
    if(not isinstance(result_map["css"], Exception)):
        res = result_map["css"]["errorCount"]
        del result_map["css"]["errorCount"]
    return res

def create_final_data(final_results, result_map, categories):
    data = {
        "psi_sections": [],
        "loading_section": get_loading_experience(result_map)
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
        "errorCount": get_error_count(result_map)
    }

    data["content_analysis"] = final_results["content_analysis"]
    data["dead_link_count"] = final_results["dead_link_count"]

    return data


    





