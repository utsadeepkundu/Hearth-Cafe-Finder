# Hearth — Nearby Places Discovery

Hearth is a location-aware web application that helps users discover nearby places such as cafés, entertainment venues, cultural locations, and historic places.

The frontend is a responsive HTML/CSS/JavaScript interface, while the backend uses FastAPI and OpenStreetMap's Overpass API to find nearby places based on the user's current location, selected category, and search radius.

The application also uses Wikimedia Commons to retrieve potentially relevant place imagery when a sufficiently confident image match is available.

---

## Features

- Browser-based location detection
- Nearby place discovery
- Café discovery
- Fun & games discovery
- Entertainment discovery
- Culture discovery
- Historic-place discovery
- Search radius selection from 2 km to 20 km
- Haversine-based distance calculation
- OpenStreetMap / Overpass place data
- Wikimedia Commons image lookup
- Responsive cards and mobile-friendly layout
- Google Maps directions links
- Graceful image fallback when no trusted image is found
- Backend timeout and HTTP-error handling
- Basic health endpoint
- Frontend served directly by FastAPI

---

## How the application works

```text
User opens Hearth
        |
        v
Browser asks for location permission
        |
        v
Latitude + Longitude
        |
        v
User selects a category
and search radius
        |
        v
FastAPI /api/places
        |
        v
Overpass API / OpenStreetMap
        |
        v
Nearby OSM elements
        |
        v
Coordinates + distance filtering
        |
        v
Internal relevance score
(distance + available metadata)
        |
        v
Top results selected
        |
        +----------------------+
        |                      |
        v                      v
Wikimedia Commons         Result cards
image lookup              with fallback
        |                      |
        +----------+-----------+
                   |
                   v
             Results shown
                   |
                   v
          Google Maps Directions
```

---

## User workflow

### 1. Allow location

Open the application and click:

```text
Use my location
```

The browser requests geolocation permission.

The frontend stores the returned latitude and longitude in memory for the current session.

> Geolocation works reliably on `localhost` and HTTPS. When testing locally, run the application through a local web server instead of opening `UI/index.html` directly as a `file://` URL.

### 2. Choose a category

The user can select one of:

- Cafés
- Fun & games
- Entertainment
- Culture
- Historic places

### 3. Select search radius

The available search radii are:

- 2 km
- 5 km
- 10 km
- 20 km

### 4. Search

After location and category are available, Hearth calls:

```http
GET /api/places?lat=<latitude>&lon=<longitude>&category=<category>&radius=<km>
```

### 5. Review results

Each result can show:

- Place name
- Category
- Subcategory
- Distance
- Address, when available
- Opening hours, when mapped
- Phone, when mapped
- Website, when mapped
- Place image, when found
- Directions link

### 6. Open directions

The Directions button opens Google Maps with the place coordinates as the destination.

---

## Categories and OpenStreetMap queries

The backend maps user-facing categories to OpenStreetMap tags.

### Cafés

```text
amenity=cafe
```

### Fun & games

Includes mapped categories such as:

```text
leisure=bowling_alley
sport=bowling
leisure=amusement_arcade
leisure=escape_game
leisure=miniature_golf
leisure=gaming
```

### Entertainment

Includes:

```text
amenity=cinema
amenity=theatre
amenity=music_venue
amenity=nightclub
amenity=events_venue
tourism=theme_park
tourism=aquarium
leisure=amusement_arcade
leisure=escape_game
```

### Culture

Includes:

```text
tourism=museum
tourism=gallery
tourism=artwork
amenity=arts_centre
amenity=theatre
amenity=library
amenity=community_centre
amenity=exhibition_centre
amenity=music_venue
```

### Historic places

Includes:

```text
historic=castle
historic=ruins
historic=monument
historic=memorial
historic=fort
historic=fortification
historic=archaeological_site
historic=city_gate
historic=manor
historic=palace
historic=yes
heritage=*
```

---

## Backend ranking

Hearth does not invent review ratings.

Instead, it calculates an internal ranking score using:

- Distance from the user
- Address availability
- Website availability
- Phone availability
- Opening-hours availability
- Description availability

The backend explicitly returns:

```json
"rating": null,
"rating_count": null
```

unless real ratings are available from a trusted source.

This avoids presenting an internal relevance score as a public review rating.

---

## Distance calculation

The backend calculates the distance between the user's location and each place using the Haversine formula.

The formula accounts for the Earth's curvature and returns distance in kilometres.

Results outside the selected radius are discarded.

---

## Image system

Hearth uses Wikimedia Commons for image discovery.

The image lookup:

1. Searches geographically near the place.
2. Looks at candidate file titles.
3. Normalizes text to remove accents and punctuation.
4. Compares the place name against the image title.
5. Requires a confidence threshold.
6. Returns no image when confidence is insufficient.

This is intentional: the application prefers a missing-image fallback over displaying an unrelated photo.

The backend only performs image lookup for the top six results to reduce network overhead.

Image requests are executed concurrently with `asyncio.gather()`.

---

## Error handling

The backend handles common external API problems.

Examples:

```text
504 → Overpass timeout
503 → External API/network request error
502 → Overpass returned an upstream HTTP error
400 → Unsupported category
```

Image retrieval failures do not fail the complete places search. The place can still be shown with the frontend's visual fallback.

---

## Project structure

```text
Hearth/
│
├── Backend/
│   ├── __init__.py
│   ├── main.py
│   ├── places.py
│   └── image_service.py
│
├── UI/
│   └── index.html
│
├── tests/
│   └── test_image_service.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Technology stack

### Python

Used for the backend application and data-processing logic.

### FastAPI

Used to expose the REST API and serve the frontend.

### Uvicorn

Used as the ASGI server for local development and deployment.

### HTTPX

Used for asynchronous HTTP requests to:

- Overpass API
- Wikimedia Commons API

### HTML / CSS / JavaScript

Used for the responsive frontend and client-side location/category/radius interactions.

### OpenStreetMap / Overpass API

Used as the primary nearby-place data source.

### Wikimedia Commons

Used for optional place-image discovery.

### Google Maps

Used for outbound directions links.

---

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Hearth
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run locally

From the repository root:

```bash
uvicorn Backend.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

The backend serves the frontend from:

```text
UI/index.html
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

---

## API

### Health

```http
GET /api/health
```

Example:

```json
{
  "status": "healthy",
  "service": "Hearth API"
}
```

### Nearby places

```http
GET /api/places
```

Query parameters:

| Parameter | Type | Example |
|---|---|---|
| lat | float | 22.5726 |
| lon | float | 88.3639 |
| category | string | cafe |
| radius | float | 5 |

Example:

```text
http://127.0.0.1:8000/api/places?lat=22.5726&lon=88.3639&category=cafe&radius=5
```

---

## Frontend API configuration

The frontend uses the current origin by default:

```javascript
window.location.origin
```

This means the included setup works without changing JavaScript when the FastAPI server serves both the UI and API.

For a separate frontend deployment, an external API base can be supplied before the frontend script executes:

```html
<script>
  window.HEARTH_API_BASE_URL = "https://your-api.example.com";
</script>
```

---

## Testing

Run the included tests with:

```bash
pytest
```

The tests currently cover the pure text normalization and image-title matching logic used by the Wikimedia image service.

---

## Notes about external data

Hearth relies on third-party data services.

OpenStreetMap and Overpass data can be incomplete or outdated in some locations.

Opening hours, phone numbers, websites and place classifications are shown only when present in the source data.

Always verify important information before visiting a place.

---

## Security and deployment notes

- Do not commit `.env` files or secrets.
- Keep generated virtual environments outside Git.
- Use HTTPS in production so browser geolocation works reliably.
- Respect the usage policies and rate limits of Overpass, Wikimedia Commons and other external services.
- For a high-traffic production deployment, consider adding caching, retries with backoff, rate limiting, and a controlled map-data provider.

---

## Future improvements

Possible future improvements include:

- Map view
- Saved places
- Favorites
- Search by place name
- More granular filters
- User accounts
- Review/rating integration from trusted providers
- Open-now filtering
- Better address enrichment
- Caching
- Rate limiting
- Progressive Web App support
- Dedicated mobile UI
- Deployment configuration
- Automated integration tests

---

## Author

**Utsadeep Kundu**

B.Tech — Computer Science & Engineering  
Artificial Intelligence & Machine Learning
