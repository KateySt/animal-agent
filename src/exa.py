import json
from functools import lru_cache

from exa_py import AsyncExa

from src.config import get_exa_config


@lru_cache
def get_exa_client() -> AsyncExa:
    return AsyncExa(api_key=get_exa_config().EXA_API_KEY)


async def web_search(query: str, num_results: int = 5) -> str:
    client = get_exa_client()

    response = await client.search_and_contents(query, num_results=num_results, text=True)

    items = [{"title": result.title, "url": result.url, "published_date": result.published_date, "text": result.text} for result in response.results]
    return json.dumps({"results": items})
