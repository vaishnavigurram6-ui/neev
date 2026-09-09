"""Serving a borrower's site photographs, and to whom.

These are photographs of somebody's half-built home, so the access boundary
matters more than the bytes: the lookup happens *inside* the authorized loan,
never by photo id alone.
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import models
from app.db.session import SessionLocal

OWNER_1001 = {"role": "owner", "phone": "9849012345"}
OWNER_1002 = {"role": "owner", "phone": "9849012345", "loan_id": "1002"}
BANK = {"role": "bank", "phone": "9812345678"}

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
    b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _as(client, login):
    client.cookies.clear()
    assert client.post("/api/auth/session", json=login).status_code == 200


def _report_a_milestone(client) -> int:
    """Upload one photo as the owner of 1001 and return its row id."""
    _as(client, OWNER_1001)
    response = client.post(
        "/api/loans/1001/milestones",
        data={"stage": "slab", "note": "Slab poured on 10 Aug"},
        files=[("photos", ("slab.png", PNG, "image/png"))],
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        photo = db.scalars(
            select(models.Photo).where(models.Photo.stored_path.is_not(None))
            .order_by(models.Photo.id.desc())
        ).first()
        assert photo is not None
        return photo.id


def test_a_reported_photo_comes_back_as_an_image(client):
    photo_id = _report_a_milestone(client)
    response = client.get(f"/api/loans/1001/photos/{photo_id}")
    assert response.status_code == 200, response.text
    assert response.content == PNG
    # Read from the bytes, not from the uploader's content-type header.
    assert response.headers["content-type"] == "image/png"
    # Somebody's home under construction: never a shared cache.
    assert "private" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_lender_can_see_the_evidence_the_borrower_sent(client):
    photo_id = _report_a_milestone(client)
    _as(client, BANK)
    assert client.get(f"/api/loans/1001/photos/{photo_id}").status_code == 200


def test_another_borrower_cannot_read_this_familys_photographs(client):
    photo_id = _report_a_milestone(client)
    _as(client, OWNER_1002)
    # Not 200-with-someone-else's-photo, and not a 404 that leaks existence
    # either: the loan boundary refuses before the photo is ever looked up.
    assert client.get(f"/api/loans/1001/photos/{photo_id}").status_code == 403
    # And it is not reachable by hanging the id off their own loan.
    assert client.get(f"/api/loans/1002/photos/{photo_id}").status_code == 404


def test_anonymous_readers_get_nothing(client):
    photo_id = _report_a_milestone(client)
    client.cookies.clear()
    assert client.get(f"/api/loans/1001/photos/{photo_id}").status_code == 401


def test_a_row_with_no_stored_bytes_is_a_404_not_a_broken_image(client):
    """A row can record what the inspector read without holding the frame.

    The seed gives the golden case's evidence rows real photographs, so this
    builds the other kind: `stored_path` is nullable precisely because a
    checkout without the demo photographs, or a live run that captured a
    reading and not a file, still has to render.
    """
    _as(client, OWNER_1001)
    with SessionLocal() as db:
        tranche = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 4)
        note_only = models.Photo(
            tranche_id=tranche.id,
            slot_key="1001-t4-note",
            caption="Read from the photograph, which was not retained.",
        )
        db.add(note_only)
        db.commit()
        photo_id = note_only.id

    assert client.get(f"/api/loans/1001/photos/{photo_id}").status_code == 404
    # And the view says so rather than pointing a screen at a dead frame.
    photos = [
        p
        for phase in client.get("/api/loans/1001/progress").json()["phases"]
        for p in phase["photos"]
    ]
    assert any(p["src"] is None for p in photos), "a note-only row must carry no src"
    assert any(p["src"] for p in photos), "and a seeded frame must carry one"


def test_a_photo_whose_file_has_gone_is_a_404(client, tmp_path):
    photo_id = _report_a_milestone(client)
    with SessionLocal() as db:
        photo = db.get(models.Photo, photo_id)
        Path(photo.stored_path).unlink()
    assert client.get(f"/api/loans/1001/photos/{photo_id}").status_code == 404


@pytest.mark.parametrize("bad", ["0", "-1", "abc"])
def test_a_photo_id_that_is_not_an_id_is_refused(client, bad):
    _as(client, OWNER_1001)
    assert client.get(f"/api/loans/1001/photos/{bad}").status_code == 422
