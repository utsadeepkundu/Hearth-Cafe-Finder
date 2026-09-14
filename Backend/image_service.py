import re
import unicodedata

import httpx


COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def normalize_text(text: str) -> str:
    """
    Normalize text so that we can compare a place name
    with a Wikimedia Commons file title.
    """

    text = unicodedata.normalize("NFKD", text)

    text = text.lower()

    # Remove accents
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    # Replace punctuation with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse repeated spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def name_match_score(place_name: str, image_title: str) -> float:
    """
    Compare the place name with the Wikimedia file title.

    Returns a score between 0 and 1.
    """

    place = normalize_text(place_name)

    title = normalize_text(image_title)

    if not place or not title:
        return 0.0

    # Exact phrase
    if place in title:
        return 1.0

    place_words = set(place.split())
    title_words = set(title.split())

    if not place_words:
        return 0.0

    common_words = place_words.intersection(title_words)

    score = len(common_words) / len(place_words)

    return score


async def find_nearby_image(
    place_name: str,
    lat: float,
    lon: float,
    radius_m: int = 1000,
):
    """
    Search Wikimedia Commons for an image that is both:

    1. geographically near the place
    2. reasonably related to the place name

    Returns image information when confidence is good.
    Otherwise returns None.
    """

    # --------------------------------------------
    # First search geographically
    # --------------------------------------------

    params = {
        "action": "query",
        "generator": "geosearch",

        # Files only
        "ggsnamespace": "6",

        "ggscoord": f"{lat}|{lon}",
        "ggsradius": radius_m,
        "ggslimit": "20",

        "prop": "imageinfo",
        "iiprop": "url",

        # Thumbnail
        "iiurlwidth": "700",

        "format": "json",
        "origin": "*",
    }

    try:

        async with httpx.AsyncClient(
            timeout=5
        ) as client:

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

    except httpx.TimeoutException:
        print(
            f"Wikimedia timeout for: {place_name}"
        )
        return None

    except httpx.RequestError as exc:
        print(
            f"Wikimedia request error for "
            f"{place_name}: {exc}"
        )
        return None

    except httpx.HTTPStatusError as exc:
        print(
            f"Wikimedia HTTP error: "
            f"{exc.response.status_code}"
        )
        return None

    pages = data.get(
        "query",
        {}
    ).get(
        "pages",
        {}
    )

    if not pages:
        return None

    # --------------------------------------------
    # Find best candidate
    # --------------------------------------------

    best_match = None
    best_score = 0.0

    for page in pages.values():

        title = page.get("title", "")

        if not title:
            continue

        imageinfo = page.get("imageinfo", [])

        if not imageinfo:
            continue

        info = imageinfo[0]

        image_url = (
            info.get("thumburl")
            or info.get("url")
        )

        if not image_url:
            continue

        score = name_match_score(
            place_name,
            title,
        )

        if score > best_score:

            best_score = score

            best_match = {
                "image_url": image_url,

                "image_page": (
                    "https://commons.wikimedia.org/wiki/"
                    + title.replace(" ", "_")
                ),

                "image_title": title,

                "match_score": round(
                    score,
                    2
                ),
            }

    # --------------------------------------------
    # Confidence threshold
    # --------------------------------------------
    #
    # We don't want random nearby images.
    #
    # 0.60 means at least ~60% of the meaningful
    # place-name words matched.
    #

    if best_match is None:
        return None

    if best_score < 0.60:
        return None

    return best_match