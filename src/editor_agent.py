from openai import AsyncAzureOpenAI
from agents import set_default_openai_client
from dotenv import load_dotenv
import os

# # Load environment variables
load_dotenv()

# Load Env var
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Create OpenAI client using Azure OpenAI
openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

# Set the default OpenAI client for the Agents SDK
set_default_openai_client(openai_client)


from agents import Agent
from openai.types.chat import ChatCompletionMessageParam

# Create a banking assistant agent
editor_assistant = Agent(
    name="Editor Shotlist",
    instructions="You are a video editor. Your goal it to edit the provided footage into entertaining short films.",
    model="gpt-4o",  # This will use the deployment specified in your Azure OpenAI/APIM client
    #tools=[check_account_balance]  # A function tool defined elsewhere
)

# Implement tracing
from agents import Agent, HandoffInputData, Runner, function_tool, handoff, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key, add_trace_processor
from agents.tracing.processors import ConsoleSpanExporter, BatchTraceProcessor

# # Set up console tracing
# console_exporter = ConsoleSpanExporter()
# console_processor = BatchTraceProcessor(exporter=console_exporter)
# add_trace_processor(console_processor)


from agents import Runner
import asyncio

async def main():
    # Run the banking assistant
    result = await Runner.run(
        editor_assistant, 
        input="Hi, I'd like to check my account balance."
    )
    
    print(f"Response: {result.response.content}")

if __name__ == "__main__":
    asyncio.run(main())

# from agents import Agent, Runner
# from dotenv import load_dotenv
# import os

# load_dotenv()

# agent = Agent(name="Assistant", instructions="You are a helpful assistant")

# result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
# print(result.final_output)