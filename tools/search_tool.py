import os, requests
from ..schemas import WebSearchOutput, WebSearchResult

class WebSearchTool:
    def __init__(self, engine: str = "serpapi"):
        self.engine = engine
        self.api_key = os.getenv("SERPAPI_KEY")

    def run(self, query: str, context: dict = None, config: dict = None) -> WebSearchOutput:
        eng = (config or {}).get("engine", self.engine)
        if eng != "serpapi":
            return WebSearchOutput(query=query, results=[
                WebSearchResult(
                    type="error",
                    title="Unsupported engine",
                    snippet=f"Engine '{eng}' not supported",
                    link="",
                )
            ])

        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": self.api_key, "engine": "google", "num": 10},
        ).json()

        results = []
        for item in resp.get("organic_results", []):
            result = WebSearchResult(
                type="article",
                title=item.get("title", "No Title"),
                snippet=item.get("snippet", ""),
                link=item.get("link", ""),
                extra={"position": item.get("position", None)}
            )
            results.append(result)

        return WebSearchOutput(query=query, results=results)
