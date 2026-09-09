Site photographs for the golden case (loan 1001, Plot 47, Kompally), from
`demo_assets/`. Served by Next from `public/`, so the paths below are stable
and need no image endpoint:

  1001-slab-wide.jpg     the whole plot from the road — slab shuttering and props
  1001-slab-work.jpg     the slab from the front, ring beam reinforcement laid
  1001-slab-angle.jpg    the same frame, curing water going on
  1001-slab-columns.jpg  two floors cast, columns standing for the next

`src/frontend/Dockerfile` copies this directory explicitly: Next's standalone
output does not include public/.
