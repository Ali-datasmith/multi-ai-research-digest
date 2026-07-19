import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()

# --- Structured Output Schema matching app.py keys precisely ---
class ExecutiveSummary(BaseModel):
    high_level_synthesis: str = Field(description="High-level architectural overview and direct executive comparison.")
    performance_breakdown: str = Field(description="Deep dive into memory overhead, execution metrics, and latency trade-offs.")

class CodeBoilerplate(BaseModel):
    snippet: str = Field(description="Production-ready minimal implementation example showing configuration rules inside standard markdown code blocks.")
    explanation: str = Field(description="Brief explanation of the optimization logic inside the code snippet.")

class ProductionRisk(BaseModel):
    title: str = Field(description="Short descriptive title of the risk or edge case.")
    description: str = Field(description="Detailed architectural mitigation strategy.")

class ResearchReport(BaseModel):
    executive_summary: ExecutiveSummary
    code_boilerplate: CodeBoilerplate
    production_risks: list[ProductionRisk]

class ResearchEngine:
    def __init__(self):
        # Runtime Lazy-Evaluation targeting the active 3.5-flash model
        try:
            import streamlit as st
            self.model_id = st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"))
        except Exception:
            self.model_id = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
            
        self.client = genai.Client()
        console.print(f"[bold green]✔[/bold green] Research Engine initialized with model: [cyan]{self.model_id}[/cyan]")

    def execute_research(self, query: str) -> dict:
        """Executes a structured query against Gemini and returns a verified dictionary format."""
        console.print(f"[bold blue]⚡[/bold blue] Querying knowledge base for: [yellow]'{query}'[/yellow]")
        
        system_prompt = (
            "You are an elite Staff Data Engineer. Synthesize a highly rigorous technical evaluation "
            "based on the user's query. Provide clean production architectural insights."
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ResearchReport,
                temperature=0.2
            )
        )
        
        if response.parsed:
            # Dump to primitive dict to satisfy 'isinstance(report, dict)' verification in app.py
            return response.parsed.model_dump()
        else:
            raise ValueError("Failed to parse response into structural target schema.")
