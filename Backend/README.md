# Hearth

Location-based nearby place discovery using:
- FastAPI
- OpenStreetMap / Overpass
- Wikimedia Commons (only for conservative exact-name image matches)
- Existing HTML/CSS/JS frontend

## Run

From `Backend`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend:
`http://127.0.0.1:8000`

Docs:
`http://127.0.0.1:8000/docs`

Open `UI/Final Ui.html` with VS Code Live Server.

## Notes

- No paid API is required by this project.
- Ratings are not fabricated. OSM is not treated as a review database.
- A place without a trustworthy photo gets the UI fallback instead of an unrelated image.
- Search radius is passed directly to Overpass.
