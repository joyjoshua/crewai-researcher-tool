"""
Custom tools extending agent capabilities beyond CrewAI's built-in tools.
"""

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CitationCheckerInput(BaseModel):
    url: str = Field(description="The URL to verify is accessible and returns a valid response")


class CitationCheckerTool(BaseTool):
    name: str = "Citation Checker"
    description: str = (
        "Verifies that a URL is real and accessible. Use this to check "
        "any source URL referenced in the report before finalising."
    )
    args_schema: type[BaseModel] = CitationCheckerInput

    def _run(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Research Report Generator; citation-check)"
        }
        try:
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=True,
                stream=True,
                headers=headers,
            )
            response.close()
            if response.status_code < 400:
                return f"VALID — URL returned status {response.status_code}"
            return f"BROKEN — URL returned status {response.status_code}"
        except requests.exceptions.Timeout:
            return "BROKEN — URL timed out after 10 seconds"
        except requests.exceptions.ConnectionError:
            return "BROKEN — Could not connect to URL"
        except Exception as e:
            return f"ERROR — {str(e)}"
