"""
How to run this file:
1.  Set the JULEP_API_KEY and BRAVE_API_KEY environment variables.
2.  Run the script from the command line, providing one or more topics as arguments:
    `python working_example.py <topic1> <topic2> ...`

What it does:
This script generates sarcastic news headlines for given topics using the Julep platform and Brave search.
It creates or updates an agent and a task on Julep, then executes the task for each provided topic,
retrieving and printing the generated sarcastic headline.
"""
import os
import uuid
import yaml
import time
import logging
from dotenv import load_dotenv
from julep import Client

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Initialize environment
load_dotenv()
api_key = os.getenv("JULEP_API_KEY")
brave_api_key = os.getenv("BRAVE_API_KEY")

# Use fixed UUIDs so they persist across runs – these match the ones in your notebook
AGENT_UUID = uuid.UUID('a1b2c3d4-1234-5678-9101-abcdef123456')
TASK_UUID = uuid.UUID('d4c3b2a1-4321-8765-1098-fedcba654321')

# Create Julep client
client = Client(api_key=api_key, environment="dev", timeout=30)


def create_agent():
    """Create or update the agent."""
    agent = client.agents.create_or_update(
        agent_id=AGENT_UUID,
        name="Chad",
        about="Sarcastic news headline reporter.",
        model="claude-3.5-sonnet",
    )
    logging.info("Agent created/updated: %s", agent)
    # (Optional) Check the creation timestamp for anomalies relative to local time
    if hasattr(agent, "created_at"):
        logging.info("Agent created_at: %s", agent.created_at)
    return agent


def create_task():
    """Create or update the task."""
    task_def = yaml.safe_load(f"""
    name: Sarcasm Headline Generator
    tools:
    - name: brave_search
      type: integration
      integration:
        provider: brave
        setup:
          api_key: "{brave_api_key}"
    main:
    - tool: brave_search
      arguments:
        query: "{{{{inputs[0].topic}}}} funny news"  # Simplified query format
    - evaluate:
        search_results: |-
          {{
            "results": [
              {{{{
                "snippet": r['snippet'],
                "title": r['title']
              }}}}
              for r in _['result']
            ]
          }}
    - prompt:
      - role: system
        content: >-
          You are {{{{agent.about}}}}.
          The user will send you a topic and search results for that topic.
          Your goal is to write a sarcastic news headlines based on that topic and search results.
      - role: user
        content: >-
          My topic is: {{{{inputs[0].topic}}}}.
          Here are the search results: {{{{_}}}}
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
    """Ensure agent/task exist before execution."""
    try:
        client.agents.get(AGENT_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_agent()
            time.sleep(5)
        else:
            raise

    # Add task validation
    try:
        client.tasks.get(TASK_UUID)
    except Exception as e:
        if "not found" in str(e).lower():
            create_task()
            time.sleep(5)
        else:
            raise


def generate_headline(topic):
    """Generate a sarcastic headline for the given topic."""
    # Ensure the agent and task are present and ready
    ensure_agent_and_task_ready()

    # Create an execution instance
    execution = client.executions.create(
        task_id=TASK_UUID,
        input={"topic": topic}
    )
    logging.info("Execution started (ID: %s) for topic: %s", execution.id, topic)

    # Wait for execution to complete with a timeout
    max_retries = 20
    retries = 0
    while True:
        execution = client.executions.get(execution.id)
        logging.info("Execution status: %s (Retry %d/%d)", execution.status, retries, max_retries)
        if execution.status in ["completed", "succeeded", "failed", "cancelled", "expired"]:
            break
        if retries >= max_retries:
            raise RuntimeError(f"Timeout after {max_retries} retries. Final status: {execution.status}")
        time.sleep(3)
        retries += 1

    logging.info("Final execution status: %s", execution.status)

    # Retrieve and log transitions for debugging
    transitions = client.executions.transitions.list(execution_id=execution.id).items
    if transitions:
        logging.info("Found %d transitions", len(transitions))
        for i, t in enumerate(transitions):
            logging.info("Transition %d: Type: %s, Output: %s", i, t.type, t.output)

    if transitions and transitions[0].output:
        return transitions[0].output
    return "No output generated"


if __name__ == "__main__":
    import argparse

    # Setup command-line interface
    parser = argparse.ArgumentParser(description='Generate sarcastic news headlines')
    parser.add_argument('topics', nargs='+', help='Topics for headline generation')
    args = parser.parse_args()

    # Optionally create/update the agent/task once; they will be reused in generate_headline
    create_agent()
    create_task()

    # Generate headlines for each provided topic
    for topic in args.topics:
        logging.info("Generating headline for topic: %s", topic)
        try:
            result = generate_headline(topic)
            print(f"\nResult for topic '{topic}': {result}")
        except Exception as e:
            logging.error("Error generating headline for topic '%s': %s", topic, e)