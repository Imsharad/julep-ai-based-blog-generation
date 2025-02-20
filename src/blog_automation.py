import os
import time
import yaml
from julep import Client
from dotenv import load_dotenv
import urllib.parse
from pprint import pprint
import asyncio
import sys
from pathlib import Path
import uuid  # Add this import to generate valid UUIDs
import logging

class BlogAutomation:
    def __init__(self):
        # Set base_dir first
        self.base_dir = Path(__file__).parent.parent  # Points to project root
        self.tasks_dir = self.base_dir / "tasks"  # Where task YAMLs reside
        
        # Then load environment
        self.load_environment()
        
        # Verify critical directories
        if not self.tasks_dir.exists():
            raise FileNotFoundError(f"Tasks directory not found at: {self.tasks_dir}")
        
        self.client = Client(api_key=self.julep_api_key, environment="production")

    def load_environment(self):
        """Updated to match .env structure"""
        load_dotenv(dotenv_path=self.base_dir / '.env', override=True)
        
        # Required variables from .env
        self.julep_api_key = os.getenv("JULEP_API_KEY")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.agent_id = os.getenv("AGENT_UUID")  # Matches AGENT_UUID in .env
        
        # Validate all required variables exist
        missing = []
        if not self.julep_api_key: missing.append("JULEP_API_KEY")
        if not self.brave_api_key: missing.append("BRAVE_API_KEY")
        if not self.agent_id: missing.append("AGENT_UUID")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Debug output
        print(f"Loaded Agent ID: {self.agent_id}")
        print(f"Using Brave API Key: {'*' * len(self.brave_api_key) if self.brave_api_key else 'MISSING'}")
        # ADD THIS:  Explicitly check if the key is "empty" even if present.
        if self.brave_api_key and not self.brave_api_key.strip():
            raise ValueError("BRAVE_API_KEY is present but empty in .env file.")

        print(f"Tasks directory: {self.tasks_dir}")

    def load_task_definitions(self):
        """Load all task YAMLs from directory with template variables"""
        task_defs = {}
        for yaml_file in self.tasks_dir.glob("*.yaml"):
            print(f"Loading task: {yaml_file.stem}")
            with open(yaml_file, "r") as f:
                content = f.read()
                
            # Replace template variables with actual values
            content = content.replace("<ACTUAL_API_KEY>", self.brave_api_key)
            
            task_defs[yaml_file.stem] = yaml.safe_load(content)
        return task_defs

    async def run_task(self, task_name: str, inputs: dict):
        """Execute a specific task by name"""
        print(f"\n=== Starting task: {task_name} ===")
        task_def = self.task_definitions.get(task_name)
        if not task_def:
            raise ValueError(f"Task {task_name} not found in definitions")
        
        # Matches working example's fixed UUID
        task_id = "d4c3b2a1-4321-8765-1098-fedcba654321"
        
        # Create/update task with proper timeout
        try:
            self.client.tasks.create_or_update(
                task_id=task_id,
                agent_id=self.agent_id,
                **task_def
            )
        except Exception as e:
            logging.error(f"Failed to create/update task {task_name}: {str(e)}")
            raise

        # Create execution with simplified input structure
        execution = self.client.executions.create(
            task_id=task_id,
            input=inputs  # Direct dict like working example
        )

        # Improved execution monitoring with timeout
        max_retries = 15  # Reduced from 20 to fail faster
        retries = 0
        while True:
            try:
                execution = self.client.executions.get(execution.id)
                current_status = execution.status
                print(f"{task_name} status: {current_status} (Retry {retries}/{max_retries})")
                
                if current_status in ["completed", "succeeded", "failed", "cancelled", "expired"]:
                    break
                    
                if retries >= max_retries:
                    raise RuntimeError(f"Timeout after {max_retries} retries. Final status: {current_status}")
                    
                await asyncio.sleep(3)
                retries += 1
                
            except Exception as e:
                logging.error(f"Error checking execution status: {str(e)}")
                raise

        # Add transition logging like working example
        transitions = self.client.executions.transitions.list(execution_id=execution.id).items
        if transitions:
            print(f"Found {len(transitions)} transitions for {task_name}:")
            for i, t in enumerate(transitions):
                print(f"Transition {i}: Type: {t.type}, Output: {t.output}")

        if execution.status == "succeeded":
            # Return the output of the first transition
            return transitions[0].output if transitions else None
        
        print(f"Task {task_name} failed. Final status: {execution.status}")
        return None

    async def run_pipeline(self, search_query: str):
        """Multi-stage pipeline execution"""
        # Initialize agent once
        self.client.agents.create_or_update(
            agent_id=self.agent_id,
            name="Blog Generation Agent",
            about="Advanced blog generator using Brave Search and multi-step processing",
            model="gpt-4o",
        )
        
        # Load all task definitions
        self.task_definitions = self.load_task_definitions()

        # Modified Brave search call
        search_results = await self.run_task(
            "brave_search_task",
            {"topic": search_query}  # Changed from list to dict
        )
        
        if not search_results:
            print("Brave search failed")
            return
        
        # Use get to safely access nested keys
        results = search_results.get('search_results', {}).get('results', None)

        if not results:
            print("No results found in search response")
            return

        print(f"Search results: {results}")

        blog_post = await self.run_task(
            "blog_prompt_engineering_task",
            {
                "search_results": results,
                "topic": search_query
            }
        )

        if blog_post:
            output_path = self.base_dir / "generated_blog.md"
            # Directly access the evaluated content
            content = blog_post.get("content", "")
            output_path.write_text(content)
            print(f"Blog generated successfully at {output_path}")

async def main():
    automation = BlogAutomation()
    search_query = os.getenv("SEARCH_QUERY")
    if not search_query:
        search_query = input("Enter the search query: ")
    await automation.run_pipeline(search_query)

if __name__ == "__main__":
    asyncio.run(main()) 