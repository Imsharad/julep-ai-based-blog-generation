from julep import Client
import os
import uuid
import logging
from dotenv import load_dotenv
import yaml
import time
import argparse

# Setup logging and environment
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Use fixed UUIDs for persistence
AGENT_UUID = uuid.UUID('a1b2c3d4-1234-5678-9101-jinawebreader123')
TASK_UUID = uuid.UUID('d4c3b2a1-4321-8765-1098-jinatask654321')

client = Client(
    api_key=os.getenv("JULEP_API_KEY"),
    environment="dev",
    timeout=30
)

def create_agent():
    """Create or update the Jina web reader agent"""
    agent = client.agents.create_or_update(
        agent_id=AGENT_UUID,
        name="Jina Web Processor",
        about="Specializes in processing web content using Jina Reader",
        model="claude-3.5-sonnet",
    )
    logging.info("Agent created/updated: %s", agent)
    return agent

def create_task():
    """Create or update the Jina processing task"""
    task_def = yaml.safe_load(f"""
    name: Web Content Processor
    description: Process web content with Jina Reader
    tools:
    - name: jina_web_reader
      type: integration
      integration:
        provider: jina-reader
        setup:
          api_key: "{os.getenv('JINA_API_KEY')}"
    main:
    - tool: jina_web_reader
      arguments:
        url: "{{{{inputs[0].url}}}}"
        format: text
        timeout: 30
    - prompt:
      - role: system
        content: >-
          You are a web content analyzer. Process the content from Jina Reader
          and provide a clean summary.
      - role: user
        content: >-
          Please analyze this content: {{{{_}}}}
      unwrap: true
    """)
    
    task = client.tasks.create_or_update(
        task_id=TASK_UUID,
        agent_id=AGENT_UUID,
        **task_def
    )
    logging.info("Task created/updated: %s", task)
    return task

def ensure_agent_and_task_ready():
    """Ensure agent/task exist before execution"""
    try:
        client.agents.get(AGENT_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_agent()
        else:
            raise

    try:
        client.tasks.get(TASK_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_task()
        else:
            raise

def process_url(url):
    """Process a URL through Jina Reader"""
    ensure_agent_and_task_ready()
    
    execution = client.executions.create(
        task_id=TASK_UUID,
        input={"url": url}
    )
    
    # Wait for completion with timeout
    max_retries = 10
    retries = 0
    while retries < max_retries:
        execution = client.executions.get(execution.id)
        if execution.status in ["completed", "succeeded"]:
            transitions = client.executions.transitions.list(execution_id=execution.id).items
            return transitions[0].output if transitions else "No output"
        if execution.status in ["failed", "cancelled"]:
            raise RuntimeError(f"Execution failed with status: {execution.status}")
        time.sleep(2)
        retries += 1
        
    raise TimeoutError("Processing timed out")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process URLs with Jina Reader')
    parser.add_argument('urls', nargs='+', help='URLs to process')
    args = parser.parse_args()

    create_agent()
    create_task()

    for url in args.urls:
        try:
            result = process_url(url)
            print(f"\nURL: {url}\nResult: {result}")
        except Exception as e:
            logging.error("Error processing %s: %s", url, e) 