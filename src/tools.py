import json
from datetime import date

from livekit.agents import FunctionTool, function_tool

from src.api_client import AgentApiClient, AgentApiError
from src.api_models import InvoiceStatusValue
from src.exa import web_search as exa_web_search
from src.logger import log
from src.prompts import GET_INVOICES_TOOL_DESCRIPTION, SEARCH_DOCUMENTS_TOOL_DESCRIPTION, WEB_SEARCH_TOOL_DESCRIPTION


def _unavailable(tool_name: str, exc: AgentApiError) -> str:
    log.warning("agent_tool_unavailable", tool=tool_name, error=repr(exc))
    return json.dumps({"error": f"{tool_name} is temporarily unavailable"})


def build_invoices_function_tool(api: AgentApiClient) -> FunctionTool:
    @function_tool(description=GET_INVOICES_TOOL_DESCRIPTION)
    async def get_invoices(
        start_date: date | None = None,
        end_date: date | None = None,
        status: InvoiceStatusValue | None = None,
    ) -> str:
        try:
            return await api.get_invoices(start_date, end_date, status)
        except AgentApiError as exc:
            return _unavailable("get_invoices", exc)

    return get_invoices


def build_web_search_function_tool() -> FunctionTool:
    @function_tool(description=WEB_SEARCH_TOOL_DESCRIPTION)
    async def web_search(query: str, num_results: int = 5) -> str:
        return await exa_web_search(query, num_results)

    return web_search


def build_search_documents_function_tool(api: AgentApiClient) -> FunctionTool:
    @function_tool(description=SEARCH_DOCUMENTS_TOOL_DESCRIPTION)
    async def search_documents(query: str, top_k: int = 5) -> str:
        try:
            return await api.search_documents(query, top_k)
        except AgentApiError as exc:
            return _unavailable("search_documents", exc)

    return search_documents
