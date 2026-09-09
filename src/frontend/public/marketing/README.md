Public marketing assets. Everything here is world-readable by design — this is
the one part of the product with no session behind it.

  hero-family.jpg   the Landing hero, 1400x990, 153 KB

Derived from `figures/landing image.png` (2444x1728 RGBA, 7.5 MB), which is
left out of git: a hero that ships at 7.5 MB is a hero nobody on a phone sees.
To regenerate after replacing the source:

    src/backend/.venv/bin/python - <<'PY'
    from PIL import Image
    src = Image.open('figures/landing image.png')
    w = 1400
    out = src.convert('RGB').resize((w, round(src.height * w / src.width)), Image.LANCZOS)
    out.save('src/frontend/public/marketing/hero-family.jpg',
             'JPEG', quality=82, optimize=True, progressive=True)
    PY

Site photographs do NOT belong here. They are somebody's house being built, and
they live in `fixtures/site_photos/`, served through
`GET /api/loans/{id}/photos/{photo_id}`, which authorizes per loan.
