"""The HTTP surface. Routes translate requests into mapper calls and back.

Two rules hold across every module here:

* No route reads NEEV_MODE. Mode is resolved once, in
  `app.services.runner.get_runner`, and everything else depends on the
  PipelineRunner protocol or on persisted state.
* No route is screen-shaped. Endpoints return domain objects; a screen composes
  the two or three it needs.

Private APIs require signed sessions, role checks and owner/loan checks.
Demo sign-in is disabled unless NEEV_DEMO_AUTH=true; it is not a real identity
provider. See docs/Review_Remediation.md for production deployment gates.
"""
