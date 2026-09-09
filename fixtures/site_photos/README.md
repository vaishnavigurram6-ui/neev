Site photographs of the golden case — Plot 47, Kompally, at the roof-slab
stage. Supplied by the repo owner in `demo_assets/`, which is git-ignored, so
the four the seed needs live here: `fixtures/` is what the backend image
copies, and `app/db/seed.py` reads this directory to give the seeded evidence
rows real bytes.

  roof_slab_shuttering_wide.jpg        the plot from the road, slab shuttered and propped
  roof_slab_curing.jpg                 the same frame, curing water going on
  footings_and_ground_floor_slab.jpg   the slab from the front, ring beam rebar tied
  first_floor_slab.jpg                 two floors cast, columns standing for the next

They are served only through `GET /api/loans/{id}/photos/{photo_id}`, which
authorizes per loan. Nothing here is reachable without a session — these are
photographs of somebody's house being built, and the earlier copy under
`public/` was world-readable to anyone who guessed the filename.
