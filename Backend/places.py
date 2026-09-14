import asyncio
import math

import httpx
from fastapi import APIRouter, HTTPException, Query

from image_service import find_nearby_image
from cache import TTLCache


router = APIRouter()

# Multiple mirrors: the main public instance (overpass-api.de) gets
# heavily rate-limited and is often slow or briefly unreachable.
# Falling back to other mirrors is what actually fixes requests that
# used to come back empty or time out.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Cache final responses per (category, radius, rounded location) for
# 15 minutes. Rounding the coordinates to ~100m means nearby repeat
# searches hit the cache instead of Overpass, which is both much
# faster and much kinder to the free API we depend on.
places_cache = TTLCache(ttl_seconds=900)


# =========================================================
# CATEGORY QUERIES
# =========================================================

CATEGORY_QUERIES = {
    "cafe": [
        'nwr["amenity"="cafe"]',
    ],

    "fun": [
        # Bowling
        'nwr["leisure"="bowling_alley"]',
        'nwr["sport"="bowling"]',

        # Arcades
        'nwr["leisure"="amusement_arcade"]',

        # Escape rooms
        'nwr["leisure"="escape_game"]',

        # Mini golf
        'nwr["leisure"="miniature_golf"]',

        # Gaming venues
        'nwr["leisure"="gaming"]',
    ],

    "ent": [
        # Cinema
        'nwr["amenity"="cinema"]',

        # Theatre
        'nwr["amenity"="theatre"]',

        # Arcade
        'nwr["leisure"="amusement_arcade"]',

        # Escape room
        'nwr["leisure"="escape_game"]',

        # Theme parks / amusement
        'nwr["tourism"="theme_park"]',
        'nwr["tourism"="aquarium"]',

        # Entertainment venues
        'nwr["amenity"="music_venue"]',
        'nwr["amenity"="nightclub"]',
        'nwr["amenity"="events_venue"]',
    ],

    "culture": [
        # Museums
        'nwr["tourism"="museum"]',

        # Galleries
        'nwr["tourism"="gallery"]',

        # Arts centres
        'nwr["amenity"="arts_centre"]',

        # Theatre
        'nwr["amenity"="theatre"]',

        # Libraries
        'nwr["amenity"="library"]',

        # Community / cultural centres
        'nwr["amenity"="community_centre"]',

        # Exhibition centres
        'nwr["amenity"="exhibition_centre"]',

        # Music venues
        'nwr["amenity"="music_venue"]',

        # Public artwork
        'nwr["tourism"="artwork"]',
    ],

    "history": [
        # Historic places
        'nwr["historic"="castle"]',
        'nwr["historic"="ruins"]',
        'nwr["historic"="monument"]',
        'nwr["historic"="memorial"]',
        'nwr["historic"="fort"]',
        'nwr["historic"="fortification"]',
        'nwr["historic"="archaeological_site"]',
        'nwr["historic"="city_gate"]',
        'nwr["historic"="manor"]',
        'nwr["historic"="palace"]',

        # Generic historic mapping
        'nwr["historic"="yes"]',

        # Heritage mapped objects
        'nwr["heritage"]',
    ],
}


# =========================================================
# RESULT LIMIT
# =========================================================

def get_result_limit(radius: float) -> int:
    """
    Return more results when the user chooses a larger radius.
    """

    if radius <= 2:
        return 8

    if radius <= 5:
        return 12

    if radius <= 10:
        return 20

    if radius <= 20:
        return 30

    return 40


# =========================================================
# DISTANCE
# =========================================================

def distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate distance between two coordinates
    using the Haversine formula.
    """

    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius * c


# =========================================================
# COORDINATES
# =========================================================

def get_coordinates(element):
    """
    Get coordinates from an OSM element.
    """

    # Node
    if "lat" in element and "lon" in element:
        return (
            element["lat"],
            element["lon"],
        )

    # Way / relation
    if "center" in element:
        center = element["center"]

        return (
            center.get("lat"),
            center.get("lon"),
        )

    return None, None


# =========================================================
# ADDRESS
# =========================================================

def build_address(tags):
    """
    Build a readable address from OSM tags.
    """

    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
    ]

    return ", ".join(
        part.strip()
        for part in parts
        if isinstance(part, str)
        and part.strip()
    )


# =========================================================
# SUBCATEGORY
# =========================================================

def determine_subcategory(
    category: str,
    tags: dict,
) -> str:
    """
    Convert OSM tags into a frontend-friendly subcategory.
    """

    # -----------------------------------------------------
    # FUN / ENTERTAINMENT
    # -----------------------------------------------------

    if category in ("fun", "ent"):

        leisure = tags.get("leisure")

        if leisure == "bowling_alley":
            return "bowling"

        if leisure == "amusement_arcade":

            if tags.get("virtual_reality") == "yes":
                return "vr_arcade"

            return "arcade"

        if leisure == "escape_game":
            return "escape_room"

        if leisure == "miniature_golf":
            return "mini_golf"

        if leisure == "gaming":
            return "gaming"

        amenity = tags.get("amenity")

        if amenity == "cinema":
            return "cinema"

        if amenity == "theatre":
            return "theatre"

        if amenity == "music_venue":
            return "music_venue"

        if amenity == "nightclub":
            return "nightclub"

        if amenity == "events_venue":
            return "events_venue"

        tourism = tags.get("tourism")

        if tourism == "theme_park":
            return "theme_park"

        if tourism == "aquarium":
            return "aquarium"

    # -----------------------------------------------------
    # CULTURE
    # -----------------------------------------------------

    if category == "culture":

        tourism = tags.get("tourism")
        amenity = tags.get("amenity")

        if tourism == "museum":
            return "museum"

        if tourism == "gallery":
            return "gallery"

        if tourism == "artwork":
            return "artwork"

        if amenity == "arts_centre":
            return "arts_centre"

        if amenity == "theatre":
            return "theatre"

        if amenity == "library":
            return "library"

        if amenity == "community_centre":
            return "community_centre"

        if amenity == "exhibition_centre":
            return "exhibition_centre"

        if amenity == "music_venue":
            return "music_venue"

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    if category == "history":

        historic_type = tags.get("historic")

        if historic_type:
            return historic_type

        if tags.get("heritage"):
            return "heritage"

    # -----------------------------------------------------
    # CAFE
    # -----------------------------------------------------

    if category == "cafe":
        return "cafe"

    return "place"


# =========================================================
# MATCH SCORE
# =========================================================

def calculate_score(place: dict) -> float:
    """
    Internal ranking score.

    This is NOT a review rating.

    It considers:
    - distance
    - address
    - website
    - phone
    - opening hours
    - description
    """

    distance = place["distance_km"]

    # Base score from distance.
    score = max(
        0,
        100 - (distance * 8),
    )

    # Reward useful information.
    if place["address"]:
        score += 3

    if place["website"]:
        score += 2

    if place["phone"]:
        score += 1

    if place["opening_hours"]:
        score += 2

    if place["description"]:
        score += 2

    return round(
        score,
        2,
    )


# =========================================================
# IMAGE LOOKUP
# =========================================================

async def add_image(place: dict):
    """
    Try to find an image for a place.

    Failure here should NEVER break the places search.
    """

    try:

        image = await find_nearby_image(
            place_name=place["name"],
            lat=place["latitude"],
            lon=place["longitude"],
            radius_m=1000,
        )

        if image:

            place["image_url"] = image.get(
                "image_url"
            )

            place["image_page"] = image.get(
                "image_page"
            )

            place["image_title"] = image.get(
                "image_title"
            )

    except Exception as exc:

        print(
            f"Image lookup failed for "
            f"{place['name']}: {exc}"
        )

    return place


async def add_images_parallel(
    places: list,
):
    """
    Fetch images concurrently rather than
    waiting for every request one by one.
    """

    if not places:
        return places

    tasks = [
        add_image(place)
        for place in places
    ]

    await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    return places


# =========================================================
# OVERPASS FETCH (with retry across mirrors)
# =========================================================

async def fetch_overpass_data(query: str) -> dict:
    """
    Query Overpass, trying each mirror in turn.

    This is the main fix for "no results / no response": a single
    overloaded mirror used to mean the whole search just failed.
    Now we try up to three, and only give up if all of them fail.
    """

    last_error_detail = "unknown error"

    for index, endpoint in enumerate(OVERPASS_ENDPOINTS):

        try:
            async with httpx.AsyncClient(timeout=20) as client:

                response = await client.post(
                    endpoint,
                    data={"data": query},
                    headers={
                        "User-Agent": (
                            "Hearth/1.0 "
                            "(local development project)"
                        ),
                    },
                )

            response.raise_for_status()

            # Guard against a mirror returning an HTML rate-limit
            # page instead of JSON -- this used to crash unhandled.
            return response.json()

        except httpx.TimeoutException:
            last_error_detail = f"{endpoint} timed out"

        except httpx.HTTPStatusError as exc:
            last_error_detail = (
                f"{endpoint} returned "
                f"HTTP {exc.response.status_code}"
            )

        except httpx.RequestError as exc:
            last_error_detail = f"{endpoint} unreachable: {exc}"

        except ValueError:
            last_error_detail = f"{endpoint} returned invalid JSON"

        # Brief pause before trying the next mirror, so we're not
        # hammering everything at once.
        if index < len(OVERPASS_ENDPOINTS) - 1:
            await asyncio.sleep(0.4)

    raise HTTPException(
        status_code=503,
        detail=(
            "All Overpass mirrors failed to respond. "
            f"Last error: {last_error_detail}"
        ),
    )


# =========================================================
# API ENDPOINT
# =========================================================

@router.get("/places")
async def get_places(

    lat: float = Query(
        ...,
        ge=-90,
        le=90,
    ),

    lon: float = Query(
        ...,
        ge=-180,
        le=180,
    ),

    category: str = Query(
        "cafe",
    ),

    radius: float = Query(
        5,
        gt=0,
        le=50,
    ),
):

    # =====================================================
    # VALIDATE CATEGORY
    # =====================================================

    if category not in CATEGORY_QUERIES:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported category "
                f"'{category}'. "
                f"Available categories: "
                f"{', '.join(CATEGORY_QUERIES.keys())}"
            ),
        )

    # =====================================================
    # CACHE LOOKUP
    # =====================================================
    #
    # Coordinates are rounded to ~100m so that repeat or
    # nearby searches hit the cache instead of re-querying
    # Overpass every single time.
    #
    # =====================================================

    cache_key = TTLCache.make_key(
        category,
        radius,
        round(lat, 3),
        round(lon, 3),
    )

    cached_response = places_cache.get(cache_key)

    if cached_response is not None:
        return cached_response

    # =====================================================
    # BUILD OVERPASS QUERY
    # =====================================================

    query_parts = []

    for selector in CATEGORY_QUERIES[category]:

        query_parts.append(
            f"""
            {selector}(
                around:{radius * 1000},
                {lat},
                {lon}
            );
            """
        )

    query = f"""
    [out:json][timeout:25];

    (
        {"".join(query_parts)}
    );

    out center tags;
    """

    # =====================================================
    # CALL OVERPASS (tries multiple mirrors)
    # =====================================================

    data = await fetch_overpass_data(query)

    # =====================================================
    # PARSE RESPONSE
    # =====================================================

    results = []

    seen_ids = set()

    for element in data.get(
        "elements",
        [],
    ):

        element_id = element.get(
            "id"
        )

        element_type = element.get(
            "type",
            "osm",
        )

        unique_id = (
            f"{element_type}_{element_id}"
        )

        # Prevent duplicates.
        if unique_id in seen_ids:
            continue

        seen_ids.add(
            unique_id
        )

        tags = element.get(
            "tags",
            {},
        )

        # -------------------------------------------------
        # NAME
        # -------------------------------------------------

        name = tags.get(
            "name"
        )

        if not name:
            continue

        # -------------------------------------------------
        # COORDINATES
        # -------------------------------------------------

        place_lat, place_lon = get_coordinates(
            element
        )

        if (
            place_lat is None
            or place_lon is None
        ):
            continue

        # -------------------------------------------------
        # DISTANCE
        # -------------------------------------------------

        distance = distance_km(
            lat,
            lon,
            place_lat,
            place_lon,
        )

        # Double-check the radius.
        if distance > radius:
            continue

        # -------------------------------------------------
        # ADDRESS
        # -------------------------------------------------

        address = build_address(
            tags
        )

        # -------------------------------------------------
        # SUBCATEGORY
        # -------------------------------------------------

        subcategory = determine_subcategory(
            category,
            tags,
        )

        # -------------------------------------------------
        # PLACE OBJECT
        # -------------------------------------------------

        place = {

            "id": unique_id,

            "name": name,

            "category": category,

            "subcategory": subcategory,

            "latitude": place_lat,

            "longitude": place_lon,

            "distance_km": round(
                distance,
                2,
            ),

            "address": address,

            "phone": tags.get(
                "phone"
            ),

            "website": tags.get(
                "website"
            ),

            "opening_hours": tags.get(
                "opening_hours"
            ),

            "description": tags.get(
                "description"
            ),

            "cuisine": tags.get(
                "cuisine"
            ),

            "operator": tags.get(
                "operator"
            ),

            "virtual_reality": tags.get(
                "virtual_reality"
            ),

            "wheelchair": tags.get(
                "wheelchair"
            ),

            # We do NOT invent review ratings.
            "rating": None,

            "rating_count": None,

            # Image information.
            "image_url": None,

            "image_page": None,

            "image_title": None,
        }

        # -------------------------------------------------
        # INTERNAL SCORE
        # -------------------------------------------------

        place["match_score"] = calculate_score(
            place
        )

        results.append(
            place
        )

    # =====================================================
    # SORT RESULTS
    # =====================================================

    results.sort(
        key=lambda item: (
            -item["match_score"],
            item["distance_km"],
        )
    )

    # =====================================================
    # DYNAMIC RESULT LIMIT
    # =====================================================

    result_limit = get_result_limit(
        radius
    )

    results = results[:result_limit]

    # =====================================================
    # IMAGE LOOKUP
    # =====================================================
    #
    # Only the best 6 places get image lookups.
    #
    # All 6 requests can happen concurrently.
    #
    # Other places still appear normally with
    # the frontend fallback.
    #
    # =====================================================

    image_candidates = results[:6]

    try:
        # Images are a nice-to-have, never a reason to make the
        # user wait. Cap the whole enrichment step at 5 seconds
        # regardless of how slow Wikimedia is being -- results
        # without images are far better than a stalled request.
        await asyncio.wait_for(
            add_images_parallel(image_candidates),
            timeout=5,
        )
    except asyncio.TimeoutError:
        pass

    # =====================================================
    # RETURN
    # =====================================================

    payload = {

        "category": category,

        "user_location": {
            "latitude": lat,
            "longitude": lon,
        },

        "radius_km": radius,

        "count": len(results),

        "results": results,
    }

    places_cache.set(cache_key, payload)

    return payload