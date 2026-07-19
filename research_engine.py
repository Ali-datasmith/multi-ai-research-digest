import os
import time
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from rich.console import Console
from rich.logging import RichHandler

# --- Rich Logging Configuration ---
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("research_engine")
console = Console()

# --- Environment Configuration ---
# Read the model ID exactly once from the environment. 
# Do not hardcode the string in the initialization block.
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# --- Pydantic Schema Definitions ---
class ExecutiveSummary(BaseModel):
    high_level_synthesis: str = Field(description="High-level synthesis of the research")
    performance_breakdown: str = Field(description="Detailed performance breakdown and metrics")

class CodeBoilerplate(BaseModel):
    language: str = Field(description="Primary programming language of the snippet")
    snippet: str = Field(description="Implementation-ready code snippet")
    explanation: str = Field(description="Brief technical explanation of the code")

class ProductionRisk(BaseModel):
    title: str = Field(description="Short title of the risk or edge case")
    description: str = Field(description="Detailed description of the production risk")

class ResearchReport(BaseModel):
    executive_summary: ExecutiveSummary
    code_boilerplate: CodeBoilerplate
    production_risks: List[ProductionRisk]


class ResearchEngine:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            log.warning("GOOGLE_API_KEY not found in environment variables. API calls will fail.")
        
        # Initialize the modern google-genai client
        self.client = genai.Client(api_key=api_key)
        log.info(f"ResearchEngine initialized. Target Model: [bold cyan]{MODEL_ID}[/bold cyan]")

    def execute_research(self, query: str) -> dict:
        log.info(f"Executing single-call structured research for query: '{query}'")
        start_time = time.time()
        
        prompt = f"""
        You are an elite technical researcher. Analyze the following query and provide a structured, deeply analytical report.
        
        Query: {query}
        
        Ensure the output strictly conforms to the required JSON schema. Focus on factual 2025/2026 benchmarks, memory scaling characteristics, and production-grade edge cases.
        """
        
        try:
            # Rich terminal status for server-side logs
            with console.status(f"[bold green]Contacting {MODEL_ID} via structured output API...[/bold green]") as status:
                response = self.client.models.generate_content(
                    model=MODEL_ID,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ResearchReport
                    )
                )
                
            elapsed = time.time() - start_time
            log.info(f"API call successful. Time taken: {elapsed:.2f}s")
            
            # google-genai automatically parses Pydantic models into response.parsed
            if hasattr(response, "parsed") and response.parsed is not None:
                return response.parsed.model_dump()
            
            # Fallback for raw text if schema parsing fails silently in older SDK versions
            if hasattr(response, "text"):
                return json.loads(response.text)
                
            raise ValueError("Response object did not contain parsed schema data or raw text.")
            
        except Exception as e:
            elapsed = time.time() - start_time
            log.error(f"API call failed after {elapsed:.2f}s. Error: {type(e).__name__} - {str(e)}")
            raise e
