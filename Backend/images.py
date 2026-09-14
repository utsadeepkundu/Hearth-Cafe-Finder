import httpx


COMMONS_API = "https://commons.wikimedia.org/w/api.php"


async def find_nearby_image(
    lat: float,
    lon: float,
    radius_m: int = 500,
):
    """
    Find a nearby image on Wikimedia Commons.

    Returns:
        {
            "image_url": "...",
            "image_page": "...",
            "image_title": "..."
        }

    or None when no image is found.
    """

    params = {
        "action": "query",
        "generator": "geosearch",
        "ggsprimary": "all",
        "ggsnamespace": "6",
        "ggsradius": radius_m,
        "ggscoord": f"{lat}|{lon}",
        "ggslimit": "5",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "600",
        "format": "json",
        "origin": "*",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:

            response = await client.get(
                COMMONS_API,
                params=params,
                headers={
                    "User-Agent": (
                        "Hearth/1.0 "
                        "(local development project)"
                    )
                },
            )

        response.raise_for_status()

        data = response.json()

    except (httpx.RequestError, httpx.HTTPStatusError):
        return None

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return None

    for page in pages.values():

        imageinfo = page.get("imageinfo", [])

        if not imageinfo:
            continue

        info = imageinfo[0]

        image_url = info.get("thumburl") or info.get("url")

        if not image_url:
            continue

        return {
            "image_url": image_url,
            "image_page": (
                "https://commons.wikimedia.org/wiki/"
                + page["title"].replace(" ", "_")
            ),
            "image_title": page["title"],
        }

    return None