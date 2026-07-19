import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()

# --- Structured Output Schema ---
class TechnicalDigest(BaseModel):
    summary: str = Field(description="High-level architectural overview and direct executive comparison.")
    performance_breakdown: str = Field(description="Deep dive into memory overhead, execution metrics, and latency trade-offs.")
    code_boilerplate: str = Field(description="Production-ready minimal implementation example showing configuration rules.")
    production_risks: list[str] = Field(description="Concrete edge cases, deprecation warnings, or architectural anti-patterns.")

class ResearchEngine:
    def __init__(self):
        # 💡 Runtime Lazy-Evaluation: Checks Streamlit secrets first, then OS environment, then defaults safely to 3.5
        try:
            import streamlit as st
            self.model_id = st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"))
        except Exception:
            self.model_id = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
            
        # Initialize Google GenAI client
        self.client = genai.Client()
        console.print(f"[bold green]✔[/bold green] Research Engine initialized with model: [cyan]{self.model_id}[/cyan]")

    def execute_synthesis(self, query: str) -> TechnicalDigest:
        console.print(f"[bold blue]⚡[/bold blue] Querying knowledge base for: [yellow]'{query}'[/yellow]")
        
        system_prompt = (
            "You are an elite Staff Data Engineer. Synthesize a highly rigorous technical evaluation "
            "based on the user's query. Provide clean production architectural insights. "
            "Ensure the code_boilerplate uses accurate markdown blocks and correct syntax wrappers."
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=TechnicalDigest,
                temperature=0.2
            )
        )
        
        if response.parsed:
            return response.parsed
        else:
            raise ValueError("Failed to parse response into structural target model.")
