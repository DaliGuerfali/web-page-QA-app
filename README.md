# Web Page QA App

## Instructions on How to Run Locally

### Environment Variables

Your `.env` file should look like this:
```
PSI_API_KEY=key
OPENAI_API_KEY=key
```

To get a Google Page Speed Insights API key, visit [this link](https://developers.google.com/speed/docs/insights/v5/get-started).

### Setup

1. **Create a Python virtual environment inside the repository:**
    ```sh
    python3 -m venv .venv
    ```

2. **Activate the virtual environment:**
    - On Linux/Mac:
        ```sh
        source .venv/bin/activate
        ```
    - On Windows:
        ```sh
        .venv\Scripts\activate
        ```

3. **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

### Running the Server

Run the server using FastAPI:
```sh
fastapi run main.py
```