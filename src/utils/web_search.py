"""Web search utilities for the Researcher agent."""

import re
from urllib.parse import quote

import httpx


async def fetch_wikipedia(topic: str) -> str:
    """Fetch Wikipedia content for a physics topic.

    Args:
        topic: The topic to search (e.g., "Schrödinger equation").

    Returns:
        Extracted text content from Wikipedia, or error message.
    """
    # Try to get the Wikipedia page
    search_term = quote(topic.replace(" ", "_"))

    headers = {
        "User-Agent": "TheoriaProject/1.0 (https://github.com/theoria-project; educational physics dataset)"
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # First try the Wikipedia API for summary
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search_term}"

        try:
            response = await client.get(api_url, follow_redirects=True)

            if response.status_code == 200:
                data = response.json()
                title = data.get("title", topic)
                extract = data.get("extract", "")

                # Also try to get the full content
                content_url = (
                    f"https://en.wikipedia.org/w/api.php?"
                    f"action=query&prop=extracts&exintro=0&explaintext=1&"
                    f"titles={search_term}&format=json"
                )
                content_response = await client.get(content_url, follow_redirects=True)

                full_content = ""
                if content_response.status_code == 200:
                    content_data = content_response.json()
                    pages = content_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        full_content = page.get("extract", "")
                        break

                # Combine summary and content
                result = f"# {title}\n\n"
                if extract:
                    result += f"## Summary\n{extract}\n\n"
                if full_content:
                    # Truncate to reasonable length
                    if len(full_content) > 10000:
                        full_content = full_content[:10000] + "...[truncated]"
                    result += f"## Full Content\n{full_content}\n"

                return result

            elif response.status_code == 404:
                # Try search instead
                return await _search_wikipedia(client, topic)

        except Exception as e:
            return f"Error fetching Wikipedia: {e}"

    return f"No Wikipedia content found for: {topic}"


async def _search_wikipedia(client: httpx.AsyncClient, topic: str) -> str:
    """Search Wikipedia for a topic when direct lookup fails."""
    search_url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&srsearch={quote(topic)}&format=json&srlimit=3"
    )

    try:
        response = await client.get(search_url)
        if response.status_code == 200:
            data = response.json()
            results = data.get("query", {}).get("search", [])

            if results:
                # Get the first result
                first_title = results[0].get("title", "")
                if first_title:
                    # Recursively fetch this page
                    return await fetch_wikipedia(first_title)

    except Exception:
        pass

    return f"No Wikipedia results found for: {topic}"


async def search_derivation_context(topic: str) -> str:
    """Search for derivation context from multiple sources.

    Args:
        topic: The physics topic.

    Returns:
        Combined context from Wikipedia and other sources.
    """
    results = []

    # Get Wikipedia content
    wiki_content = await fetch_wikipedia(topic)
    if wiki_content and "Error" not in wiki_content:
        results.append(f"## Wikipedia: {topic}\n\n{wiki_content}")

    # Also search for derivation-specific content
    derivation_content = await fetch_wikipedia(f"{topic} derivation")
    if derivation_content and "Error" not in derivation_content and derivation_content != wiki_content:
        results.append(f"## Wikipedia: {topic} derivation\n\n{derivation_content}")

    if not results:
        return f"No web context found for: {topic}"

    return "\n\n---\n\n".join(results)
