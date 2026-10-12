"""Tests for the inline iframe preview feature (BACKLOG B006).

External links from whitelisted hosts (Google Docs/Drive, Dropbox, YouTube,
Vimeo) are rendered in an iframe on the notice detail page. Non-whitelisted
hosts still show only a clickable link.
"""

import re
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.batch import Batch
from app.models.notice import Notice, NoticeCategory, NoticeStatus


def _make_published_notice(
    session: Session, link: str | None, title: str = "Preview Test"
) -> int:
    """Create and return a published notice id; ensures a batch exists."""
    batch = session.get(Batch, 1)
    if not batch:
        batch = Batch(name="Preview-Batch")
        session.add(batch)
        session.commit()
        session.refresh(batch)
    n = Notice(
        title=title,
        body="Preview body",
        category=NoticeCategory.GENERAL,
        batch_id=batch.id,
        external_link=link,
        status=NoticeStatus.PUBLISHED,
        published_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(n)
    session.commit()
    session.refresh(n)
    return n.id


def test_preview_host_recognizes_whitelisted_hosts():
    from app.utils import preview_host

    assert (
        preview_host("https://docs.google.com/document/d/ABC/edit") == "docs.google.com"
    )
    assert (
        preview_host("https://drive.google.com/file/d/ABC/view") == "drive.google.com"
    )
    assert preview_host("https://www.dropbox.com/s/abc/foo.pdf") == "www.dropbox.com"
    assert preview_host("https://www.youtube.com/watch?v=ID") == "www.youtube.com"
    assert preview_host("https://youtu.be/ID") == "youtu.be"
    assert preview_host("https://vimeo.com/12345") == "vimeo.com"


def test_preview_host_rejects_non_whitelisted_hosts():
    from app.utils import preview_host

    assert preview_host("https://example.com/foo.pdf") is None
    assert preview_host("https://malicious.com/x") is None
    assert preview_host("https://docs.google.com.evil.com/x") is None
    # scheme is a separate concern, handled by is_safe_external_url
    assert preview_host("http://docs.google.com/x") == "docs.google.com"
    assert preview_host("") is None
    assert preview_host(None) is None


def test_embed_url_rewrites_google_docs_edit_to_preview():
    from app.utils import embed_url

    assert (
        embed_url(
            "https://docs.google.com/document/d/16ntnFXq8__n05I_EaYPUjd1HIUHOyEBWP8PIOxF0NEs/edit?usp=sharing"
        )
        == "https://docs.google.com/document/d/16ntnFXq8__n05I_EaYPUjd1HIUHOyEBWP8PIOxF0NEs/preview"
    )


def test_embed_url_rewrites_google_drive_view_to_preview():
    from app.utils import embed_url

    assert (
        embed_url("https://drive.google.com/file/d/ABC123/view")
        == "https://drive.google.com/file/d/ABC123/preview"
    )


def test_embed_url_rewrites_youtube_watch_to_embed():
    from app.utils import embed_url

    assert embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == (
        "https://www.youtube.com/embed/dQw4w9WgXcQ"
    )
    assert embed_url("https://youtu.be/dQw4w9WgXcQ") == (
        "https://www.youtube.com/embed/dQw4w9WgXcQ"
    )


def test_embed_url_rewrites_vimeo_to_player():
    from app.utils import embed_url

    assert embed_url("https://vimeo.com/123456789") == (
        "https://player.vimeo.com/video/123456789"
    )


def test_embed_url_returns_none_for_non_whitelisted():
    from app.utils import embed_url

    assert embed_url("https://example.com/foo.pdf") is None
    assert embed_url("") is None
    assert embed_url(None) is None


def test_embed_url_passes_through_other_whitelisted_hosts():
    from app.utils import embed_url

    dropbox = "https://www.dropbox.com/s/abc/foo.pdf?dl=0"
    assert embed_url(dropbox) == dropbox


def test_csp_allows_whitelisted_frame_hosts(client: TestClient):
    """CSP must include frame-src entries for the preview hosts."""
    resp = client.get("/")
    csp = resp.headers.get("content-security-policy", "")
    assert "frame-src" in csp
    assert "https://docs.google.com" in csp
    assert "https://drive.google.com" in csp
    assert "https://*.dropbox.com" in csp
    assert "https://www.youtube.com" in csp
    assert "https://player.vimeo.com" in csp


def test_csp_does_not_allow_inline_scripts(client: TestClient):
    """The CSP relaxation must not regress the no-inline-scripts rule."""
    resp = client.get("/")
    csp = resp.headers.get("content-security-policy", "")
    assert "script-src 'self' 'unsafe-inline'" not in csp


def test_notice_detail_renders_iframe_for_google_docs(
    client: TestClient, session: Session
):
    """A Google Docs notice detail page should embed the preview iframe."""
    url = "https://docs.google.com/document/d/ABC/edit?usp=sharing"
    nid = _make_published_notice(session, url, "Google Doc Notice")
    resp = client.get(f"/notices/{nid}")
    assert resp.status_code == 200
    assert "detail-preview-frame" in resp.text
    # Iframe src should be the rewritten /preview URL
    m = re.search(r'<iframe[^>]*src="([^"]+)"', resp.text)
    assert m is not None
    assert m.group(1).endswith("/preview")
    assert "ABC" in m.group(1)
    # Sandbox attribute for security
    assert "sandbox=" in resp.text


def test_notice_detail_renders_iframe_for_youtube(client: TestClient, session: Session):
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    nid = _make_published_notice(session, url, "YouTube Notice")
    resp = client.get(f"/notices/{nid}")
    assert resp.status_code == 200
    m = re.search(r'<iframe[^>]*src="([^"]+)"', resp.text)
    assert m is not None
    assert m.group(1) == "https://www.youtube.com/embed/dQw4w9WgXcQ"


def test_notice_detail_skips_iframe_for_non_whitelisted_host(
    client: TestClient, session: Session
):
    """Non-whitelisted link: no iframe, but the link is still shown."""
    url = "https://example.com/some-page.html"
    nid = _make_published_notice(session, url, "Generic Link Notice")
    resp = client.get(f"/notices/{nid}")
    assert resp.status_code == 200
    # External link shown
    assert url in resp.text
    # No iframe
    assert "<iframe" not in resp.text
    assert "detail-preview-frame" not in resp.text


def test_notice_detail_skips_iframe_when_no_link(client: TestClient, session: Session):
    nid = _make_published_notice(session, None, "Plain Notice")
    resp = client.get(f"/notices/{nid}")
    assert resp.status_code == 200
    assert "<iframe" not in resp.text
