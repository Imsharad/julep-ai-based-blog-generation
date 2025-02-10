from julep import Client
import os
import uuid
import logging
from dotenv import load_dotenv
import yaml
import time
import argparse
import requests
from typing import Dict, Any
import json
from ast import literal_eval

# Setup logging and environment
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Check for required environment variables
if not os.getenv("JINA_API_KEY"):
    raise EnvironmentError("The JINA_API_KEY environment variable must be set.")
if not os.getenv("JULEP_API_KEY"):
    raise EnvironmentError("The JULEP_API_KEY environment variable must be set.")

# Use fixed UUIDs for persistence (you can change these if needed)
AGENT_UUID = uuid.UUID("a1b2c3d4-1234-5678-9101-abcdef123456")
TASK_UUID = uuid.UUID("d4c3b2a1-4321-8765-1098-fedcba654321")

# Initialize Julep Client
client = Client(
    api_key=os.getenv("JULEP_API_KEY"),
    environment="dev",  # Or "prod", depending on your setup
    timeout=30,
)

def create_julep_agent() -> None:
    """Creates or updates the Julep agent and registers the Jina tool."""
    agent = client.agents.create_or_update(
        agent_id=AGENT_UUID,
        name="Jina Web Content Processor",
        about="Processes web content using Jina AI Reader and summarizes it.",
        model="claude-3.5-sonnet",
    )
    
    # Create/update the Jina Reader tool definition (custom function tool)
    client.agents.tools.create(
        agent_id=AGENT_UUID,
        name="fetch_web_content",
        type="function",
        function={
            "description": "Fetch web content using the Jina AI Reader API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch content from."
                    }
                },
                "required": ["url"]
            }
        }
    )
    logging.info("Julep Agent created/updated with tool: %s", agent)

def fetch_content_with_jina(url: str) -> str:
    """Fetches content from a URL using the Jina AI Reader API."""
    headers: Dict[str, str] = {'Authorization': f'Bearer {os.getenv("JINA_API_KEY")}'}
    jina_url: str = f'https://r.jina.ai/{url}'

    logging.info(f"Starting Jina fetch for: {url}")
    for attempt in range(3):
        try:
            logging.debug(f"Attempt {attempt+1} - GET {jina_url}")
            start_time: float = time.time()
            response: requests.Response = requests.get(jina_url, headers=headers, timeout=30)
            response.raise_for_status()
            logging.info(f"Jina success in {time.time()-start_time:.2f}s - Status {response.status_code}")
            return response.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt+1} failed: {str(e)}")
            if attempt == 2:
                logging.error(f"Final Jina failure for: {url}")
                raise
            time.sleep(2 ** attempt)

def create_julep_task() -> None:
    """Creates or updates the Julep task to use the registered tool."""
    task_def = yaml.safe_load(f"""
input_schema:
  type: object
  properties:
    url:
      type: string
  required: [url]
name: Web Content Processing and Summarization
description: Fetches web content using Jina AI Reader and then summarizes it.
main:
- tool: fetch_web_content
  arguments:
    url: "'{{inputs.url}}'"  # Wrapped as a Python string literal expression
- prompt: |
    You are a helpful assistant specializing in summarizing web content. Provide a concise and informative summary of the following text: {{_}}
  unwrap: true
output_schema:
  type: string
  description: The summarized text.
""")
    task = client.tasks.create_or_update(
        task_id=TASK_UUID,
        agent_id=AGENT_UUID,
        **task_def
    )
    logging.info("Julep Task created/updated: %s", task)

def ensure_agent_and_task_ready() -> None:
    """Ensure agent and task exist."""
    try:
        client.agents.get(AGENT_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_julep_agent()
            time.sleep(5)  # Allow some time for the agent to be registered
        else:
            raise

    try:
        client.tasks.get(TASK_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_julep_task()
            time.sleep(5)  # Allow some time for the task to be registered
        else:
            raise

def process_url_with_julep(url: str) -> str:
    """Processes a URL using Julep, fetching content via the registered Jina tool and summarizing it."""
    logging.debug(f"Starting execution for URL: {url}")
    try:
        execution = client.executions.create(
            task_id=TASK_UUID,
            input={"url": url}
        )
    except Exception as e:
        logging.error(f"Julep execution creation failed: {e}")
        raise
    logging.info(f"Created execution ID: {execution.id} with input: {{\"url\": {url}}}")

    max_retries: int = 15
    retries: int = 0
    while retries < max_retries:
        logging.debug(f"Checking execution status (attempt {retries+1}/{max_retries})")
        execution = client.executions.get(execution.id)
        logging.debug(f"Current status: {execution.status}")

        if execution.status == "requires_action":
            logging.info("Execution requires action - checking tool calls")
            for tool_call in execution.tool_calls:  # Using 'tool_calls' as per official patterns
                logging.debug(f"Processing tool call: {tool_call.id}")
                if tool_call.function.name == "fetch_web_content":
                    logging.info(f"Handling fetch_web_content call with args: {tool_call.function.arguments}")
                    try:
                        # Safely evaluate the arguments (which are Python expressions)
                        args = literal_eval(tool_call.function.arguments)
                        result: str = fetch_content_with_jina(**args)
                        logging.debug(f"Jina response length: {len(result)} characters")
                        if not result.strip():
                            raise ValueError("Received empty content from Jina AI Reader")
                    except Exception as e:
                        logging.error(f"Failed to fetch content: {e}")
                        raise

                    logging.info("Submitting tool outputs back to Julep")
                    time.sleep(1)  # Short delay before submission
                    client.executions.submit_tool_outputs(
                        execution_id=execution.id,
                        outputs=[{
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"content": result})  # Structured output
                        }]
                    )
                    logging.debug("Tool output submitted successfully")
                    retries = 0  # Reset retry counter after successful submission

        elif execution.status in ["completed", "succeeded"]:
            logging.info("Execution completed successfully")
            transitions = client.executions.transitions.list(execution_id=execution.id).items
            if transitions and hasattr(transitions[0], "output"):
                logging.debug(f"Transition output (first 200 characters): {transitions[0].output[:200]}...")
                return transitions[0].output
            else:
                logging.warning("No transitions found in completed execution")
                return "No output"

        elif execution.status in ["failed", "cancelled"]:
            logging.error(f"Execution failed with status: {execution.status}")
            if hasattr(execution, "last_error") and execution.last_error:
                logging.error(f"Error details: {execution.last_error}")
            raise RuntimeError(f"Execution failed: {execution.status}")

        else:
            logging.debug(f"Still processing... (status: {execution.status})")

        time.sleep(3)
        retries += 1

    logging.error(f"Timeout after {max_retries} retries")
    raise TimeoutError("Processing timed out")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process URLs with Julep and Jina Reader")
    parser.add_argument("urls", nargs="+", help="URLs to process")
    args = parser.parse_args()

    # Ensure agent and task are ready before processing
    ensure_agent_and_task_ready()

    for url in args.urls:
        try:
            result = process_url_with_julep(url)
            print(f"\nURL: {url}\nSummary: {result}")
        except Exception as e:
            logging.error(f"Error processing {url}: {e}")