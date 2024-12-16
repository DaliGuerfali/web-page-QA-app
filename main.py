from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_root(request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse(
        request=request, name="home.html")
        

@app.post("/analyze")
async def generateReport(request: Request):
    form_data = await request.form()
    url = form_data.get("url")
    # Process the URL here
    return {"message": f"URL received: {url}"}
