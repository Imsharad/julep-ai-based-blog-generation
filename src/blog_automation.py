import os
import yaml
from julep import Client
from dotenv import load_dotenv
from pprint import pprint
import asyncio
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
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        
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

            content = content.replace("<SERPER_API_KEY>", self.serper_api_key)
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
                    
                await asyncio.sleep(2)
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

    async def processing_pipeline(self, search_query: str):

        """processing pipeline execution"""

        # Initialize agent once
        self.client.agents.create_or_update(
            agent_id=self.agent_id,
            name="Blog Generation Agent",
            about="Advanced blog generator using Jina AI API",
            model="gpt-4o",
        )

         # Load all task definitions
        self.task_definitions = self.load_task_definitions()

        serper_response = await self.run_task(
            "serper_search_api_call_task",
            {
                "query": search_query
            }
        )

        if serper_response.get('json') and serper_response.get('json').get('organic'):
            organic = serper_response.get('json').get('organic')
        else:
            print("Error: 'organic' key not found in serper_response or 'json' key not present.")
            return "Error: 'organic' key not found in serper_response or 'json' key not present."

        serper_response = await self.run_task(
            "serper_image_api_call_task",
            {
                "query": search_query
            }
        )
        
        if serper_response.get('json') and serper_response.get('json').get('images'):
            images = serper_response.get('json').get('images')
        else:
            print("Error: 'images' key not found in serper_response or 'json' key not present.")
            return "Error: 'images' key not found in serper_response or 'json' key not present."

        blog_post = await self.run_task(
            "blog_prompt_engineering_task",
            {
                "search_results": organic,
                "topic": search_query,
                "image_results": images
            }
        )

        if blog_post:
            output_path = self.base_dir / "generated_blog.md"
            # Directly access the evaluated content
            content = blog_post.get("content", "")
            # Normalize and remove unwanted characters
            cleaned_content = content.encode("utf-8", "ignore").decode("utf-8")

            output_path.write_text(cleaned_content, encoding="utf-8")
            print(f"Blog generated successfully at {output_path}")


# Function to create a search query for a topic with specified sources
def create_search_query(topic, sources):
    # Join the sources with ' OR site:' to format the query
    sources_query = ' OR site:'.join(sources)
    # Combine the topic with the formatted sources
    search_query = f"{topic} site:{sources_query}"
    return search_query

async def main():
    automation = BlogAutomation()
    search_query = os.getenv("SEARCH_QUERY")
    sources = [
    "www.bbc.com", 
    "www.nytimes.com", 
    "www.reuters.com", 
    "www.theguardian.com", 
    "www.washingtonpost.com"
    ]
    
    if not search_query:
        search_query = input("Enter search query: ")
    
    search_query = create_search_query(search_query, sources)

    await automation.processing_pipeline(search_query)

if __name__ == "__main__":
    asyncio.run(main()) 