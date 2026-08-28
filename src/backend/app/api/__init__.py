"""The HTTP surface. Routes translate requests into mapper calls and back.

Two rules hold across every module here:

* No route reads NEEV_MODE. Mode is resolved once, in
  `app.services.runner.get_runner`, and everything else depends on the
  PipelineRunner protocol or on persisted state.
* No route is screen-shaped. Endpoints return domain objects; a screen composes
  the two or three it needs.

Auth posture in this phase (spec §6.6, "mocked session, real boundary"): reading
loan data does not require a session, because the cookie is not yet a credential
— it is set by the login screen with no OTP and could be forged by the reader's
own browser. What *is* enforced is the boundary that real auth will keep: an
owner session may only read its own loan, and `GET /api/me` is a genuine 401
without one. Role gating for whole route groups lives in the frontend middleware
until the cookie is signed.
"""
