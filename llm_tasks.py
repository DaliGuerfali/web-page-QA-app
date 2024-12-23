

import json
import textstat
import models

from helpers import chunk_process

from langchain_core.prompts import ChatPromptTemplate


def process_audits(result_map):
    audit_instructions = """ 
    The data will be audits of Page Speed Insights.
    Remember to process every audit, and output them in the structure you were given.
    And remove audits that do not provide any value. 
    For example: 
    "main-thread-tasks": {
            "title": "Tasks",
            "description": "Lists the toplevel main thread tasks that executed during page load."
        },
    Audits like this should be removed, which means audits that only list non existent data, or non meaningful data should be removed.
    Audits about loading experience metrics such as LCP, FID, CLS, or FCP should be removed.
    If numericValue displays the same thing as displayValue, set it to null. 
    If metric savings are zeros, set it to null.
    Avoid redundancy.
    """


    return [chunk_process(models.audit_model,result_map["psi"][i], audit_instructions) for i in range(0, 4)]
    

def process_html_validation(result_map):
    html_validation_instructions = """
    The data will be HTML validation data.
    Make sure to process every error, and output them in the structure you were given.
    Make the errors user-friendly and non-ambiguous.
    Combine lastline and lastcol into 'position', if they exist otherwise set position to null.
    """

    return chunk_process(models.html_validation_model, result_map["html"], html_validation_instructions)

def process_css_validation(result_map):
    css_validation_instructions = """
        The data will be CSS validation data.
        Make sure to process every file and error type, and output them in the structure you were given.
        Make the error types user-friendly and non-ambiguous.    
        If an error type is not clear, provide a description for it. Do not repeat what is already in the title of the error, avoid redundancy.
        If an error type is clear, set the description to null.
    """

    return chunk_process(models.css_validation_model, result_map["css"], css_validation_instructions)

async def analyze_content(content: str):
    prompt_template = ChatPromptTemplate([
        ("system", """
You are a content analyst.  Analyze the following text based on these criteria:

1. **Key Takeaways**: What are the most important points conveyed in this text?
2. **Readability**: How easy is the text to read for the intended audience? Are there complex sentences or jargon? 
For this criterion, here's the Flesch-Kincaid readability score: {FK_score}. And here's the Flesch reading ease score: {FRE_score}.

3. **Tone and Style**: What is the tone of the text? Is it appropriate and consistent throughout?
4. **Engagement**: Does the text capture interest and maintain engagement? Are there clear calls to action, if relevant?
5. **Grammar and Spelling**: Are there any grammatical errors or typos?
6. **Inclusivity and Accessibility**: Does the text use inclusive language? Is it accessible to a diverse audience?
7. **Clarity and Precision**: Are there ambiguous or redundant statements?
8. **Summary**: Summarize this analysis. 

Make sure that you use 'content' instead of 'text' in your analysis, since the text provided isn't a continuous block but rather multiple ones combined together.
Provide a short and detailed analysis for each criterion, in structured JSON, minify it to save on tokens. 
        """),
        ("user", "Here is the text: {text}")
    ])

    prompt = prompt_template.format_messages(FK_score=textstat.flesch_kincaid_grade(content),
                                           FRE_score=textstat.flesch_reading_ease(content), text=content)
    res = await models.content_analysis_model.ainvoke(prompt)
    
    return res

async def summarize(data: dict, category: str):
    if(isinstance(data, Exception)):
        return f"Could not retrieve {category} data."

    prompt = ChatPromptTemplate([
            ("system", """You are a web page quality assurance expert.
    You will be given JSON data about a web page. Your task is to generate a short summary of the data.
    This should be a high level overview of the data, and should be easy to understand.
    It's going to be a paragraph shown in a website, so make it user friendly.
    Do not mention anything about loading experience metrics such as LCP, FID, CLS, or FCP.
    Only output the text, to save on tokens.
    """),
    ("user", """This is data about the {category} aspects of the page. {json_data}""")
])

    res = await models.generic_model.ainvoke(prompt.format_messages(category=category, json_data=json.dumps(data, separators=(',', ':'))))
    return res.content