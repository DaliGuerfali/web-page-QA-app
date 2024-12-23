import tiktoken
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL = "gpt-4o"
encoding = tiktoken.encoding_for_model(MODEL)

generic_model = ChatOpenAI(model=MODEL, streaming=False)

#Models with structured output
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
                            "description": "Readable format combining numericValue and numericUnit, if present, or null if it's the same as displayValue"
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
                        }
                  },
                  "additionalProperties": False,
                  "required": ["title", "description", "displayValue", "metricSavings", "numericValue"]
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
content_analysis_model = ChatOpenAI(model=MODEL, streaming=False).with_structured_output({
  "name": "get_content_analysis",
  "description": "Processes text from web page",
  "strict": True,
  "schema": {
      "type": "object",
      "properties": {
            "Key Takeaways": {
                "type": "string"
            },
          "Readability": {
              "type": "string"
          },
            "Tone and Style": {
                "type": "string"
            },
            "Engagement": {
                "type": "string"
            },
            "Grammar and Spelling": {
                "type": "string"
            },
            "Inclusivity and Accessibility": {
                "type": "string"
            },
            "Clarity and Precision": {
                "type": "string"
            },
            "Summary": {
                "type": "string"
            }
      },
      "additionalProperties": False,
      "required": ["Key Takeaways", "Readability", "Tone and Style", "Engagement", "Grammar and Spelling", "Inclusivity and Accessibility", "Clarity and Precision", "Summary"]
  }
}, method="json_schema")
