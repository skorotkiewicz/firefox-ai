import httpx


def get_weather(location: str) -> str:
    """Get current weather for a location."""
    try:
        clean_location = location.strip().replace(" ", "+").replace('<|"|>', "")
        url = f"https://wttr.in/{clean_location}?format=3"
        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            return response.text.strip()
    except Exception as e:
        return f"Error: {e}"
