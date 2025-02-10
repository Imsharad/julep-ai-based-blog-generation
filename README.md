# Blog Automation Project

This project automates the creation of blog posts using a multi-step pipeline. It uses the [Julep](https://github.com/) API to interact with various task definitions provided as YAML files. The pipeline includes steps like query formation, executing a Brave Search, and generating a blog post based on prompt engineering.

## Project Structure 


## Task Definitions

Task definitions are stored as YAML files in the `tasks/` directory. Each task file defines a step in the pipeline and includes:

- **name & description:** A brief overview of the task.
- **input_schema:** JSON-schema for expected inputs.
- **tools:** Any integrations that the task might rely on.
- **main:** Instructions (often using templating) for processing the inputs and generating outputs.

For example, `brave_search_task.yaml` contains the necessary information to perform a search via the Brave Search API. Similarly, the other tasks handle query formation and blog prompt creation.

## How It Works

1. **Environment Loading:**  
   The `BlogAutomation` class in `src/blog_automation.py` loads the environment variables from the `.env` file using `python-dotenv`.

2. **Loading Task Definitions:**  
   All YAML files in the `tasks/` directory are loaded. These define the individual steps in the automation pipeline.

3. **Execution Pipeline:**  
   The `run_pipeline` function:
   - Initiates the agent via Julep.  
   - Executes the tasks sequentially (e.g., query formation, then Brave search, then blog prompt engineering).
   - Each task creates an execution with the Julep API, polls for its status, and then collects the output.
   - Finally, the generated blog post is saved to a file (e.g., `generated_blog.md`).

4. **Running the Automation:**

   To run the blog automation, ensure your virtual environment is active and then run:

   ```bash
   python src/blog_automation.py
   ```

   You will be prompted for a `SEARCH_QUERY` if it's not set in the `.env` file.

## Additional Functions and Tools

- **Client Setup:**  
  The project uses the `julep` Python package for API interactions (client agents, tasks, and execution management).

- **UUID Generation:**  
  A deterministic UUID is generated for each task based on the agent ID and the task name using Python's `uuid.uuid5`.

- **Async Execution:**  
  The tasks are executed asynchronously with Python's `asyncio`, which polls for task completion before proceeding to the next step.

## Contributing

Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss your ideas.

## License

[MIT License](LICENSE) 