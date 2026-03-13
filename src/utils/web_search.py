"""Web search utilities for the Researcher agent."""

import html as html_module
import re
from urllib.parse import quote

import httpx


def _strip_html_tags(html: str) -> str:
    """Strip HTML tags and convert to plain text."""
    # Convert headers to markdown-style
    html = re.sub(r'<h2[^>]*>([^<]*)</h2>', r'\n\n## \1\n', html)
    html = re.sub(r'<h3[^>]*>([^<]*)</h3>', r'\n\n### \1\n', html)
    html = re.sub(r'<h4[^>]*>([^<]*)</h4>', r'\n\n#### \1\n', html)
    # Convert paragraphs to double newlines
    html = re.sub(r'</p>', '\n\n', html)
    # Convert list items
    html = re.sub(r'<li[^>]*>', '\n- ', html)
    # Remove all other tags
    html = re.sub(r'<[^>]+>', ' ', html)
    # Unescape HTML entities
    html = html_module.unescape(html)
    return html


def _clean_wiki_text(text: str) -> str:
    """Minimal cleanup of Wikipedia text - just basic whitespace normalization."""
    # Clean up multiple whitespace/newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


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

                # Get full content using HTML extraction (better structure than plaintext)
                resolved_title = quote(title.replace(" ", "_"))
                content_url = (
                    f"https://en.wikipedia.org/w/api.php?"
                    f"action=query&prop=extracts&"
                    f"titles={resolved_title}&format=json"
                )
                content_response = await client.get(content_url, follow_redirects=True)

                full_content = ""
                if content_response.status_code == 200:
                    content_data = content_response.json()
                    pages = content_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        html_content = page.get("extract", "")
                        if html_content:
                            # Convert HTML to plain text with structure
                            full_content = _strip_html_tags(html_content)
                        break

                # Clean up any math markup artifacts
                if full_content:
                    full_content = _clean_wiki_text(full_content)

                # Combine summary and content
                result = f"# {title}\n\n"
                if extract:
                    result += f"## Summary\n{extract}\n\n"
                if full_content:
                    # Truncate to reasonable length (50K chars ~= 12-15K tokens)
                    if len(full_content) > 50000:
                        full_content = full_content[:50000] + "...[truncated]"
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
