import html
import re
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.models.batch import Batch
from app.models.notice import Notice, NoticeCategory, NoticeStatus
from app.models.user import User


def get_authenticated_client(
    client: TestClient, session: Session
) -> tuple[TestClient, str]:
    # Create admin
    user = session.exec(
        select(User).where(User.email == "noticeadmin@example.com")
    ).first()
    if not user:
        user = User(
            email="noticeadmin@example.com",
            password_hash=get_password_hash("AdminPass123!"),
        )
        session.add(user)
        session.commit()

    resp = client.get("/auth/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)

    client.post(
        "/auth/login",
        data={
            "email": "noticeadmin@example.com",
            "password": "AdminPass123!",
            "csrf_token": csrf_token,
        },
    )
    return client, csrf_token


def test_pinned_notices_first_and_stable_ordering(client: TestClient, session: Session):
    now = datetime.now(UTC)
    # Notice 1: unpinned, newest
    n1 = Notice(
        title="Regular Notice New",
        body="Body 1",
        category=NoticeCategory.GENERAL,
        is_pinned=False,
        status=NoticeStatus.PUBLISHED,
        published_at=now,
    )
    # Notice 2: unpinned, older
    n2 = Notice(
        title="Regular Notice Old",
        body="Body 2",
        category=NoticeCategory.GENERAL,
        is_pinned=False,
        status=NoticeStatus.PUBLISHED,
        published_at=now - timedelta(hours=2),
    )
    # Notice 3: pinned, older
    n3 = Notice(
        title="Pinned Notice Old",
        body="Body 3",
        category=NoticeCategory.GENERAL,
        is_pinned=True,
        status=NoticeStatus.PUBLISHED,
        published_at=now - timedelta(hours=1),
    )
    # Notice 4: pinned, newest
    n4 = Notice(
        title="Pinned Notice New",
        body="Body 4",
        category=NoticeCategory.GENERAL,
        is_pinned=True,
        status=NoticeStatus.PUBLISHED,
        published_at=now + timedelta(minutes=5),
    )
    session.add_all([n1, n2, n3, n4])
    session.commit()

    resp = client.get("/")
    assert resp.status_code == 200

    # In response text, pinned notices must appear before regular notices
    pos_pinned_new = resp.text.find("Pinned Notice New")
    pos_pinned_old = resp.text.find("Pinned Notice Old")
    pos_reg_new = resp.text.find("Regular Notice New")
    pos_reg_old = resp.text.find("Regular Notice Old")

    assert pos_pinned_new != -1
    assert pos_pinned_old != -1
    assert pos_reg_new != -1
    assert pos_reg_old != -1

    assert pos_pinned_new < pos_pinned_old
    assert pos_pinned_old < pos_reg_new
    assert pos_reg_new < pos_reg_old


def test_search_filters_and_pagination(client: TestClient, session: Session):
    batch1 = Batch(name="Batch 2026-A")
    batch2 = Batch(name="Batch 2026-B")
    session.add_all([batch1, batch2])
    session.commit()

    now = datetime.now(UTC)
    # Create 15 notices to test pagination
    for i in range(15):
        notice = Notice(
            title=f"Academic Notice {i}",
            body=f"Content details for notice number {i}",
            category=NoticeCategory.ACADEMIC if i % 2 == 0 else NoticeCategory.EVENT,
            batch_id=batch1.id if i < 10 else batch2.id,
            status=NoticeStatus.PUBLISHED,
            published_at=now - timedelta(minutes=i),
        )
        session.add(notice)
    session.commit()

    # Page 1: 10 items
    resp_p1 = client.get("/")
    assert resp_p1.status_code == 200
    assert "Academic Notice 0" in resp_p1.text
    assert "Page 1 of 2" in resp_p1.text

    # Page 2: 5 items
    resp_p2 = client.get("/?page=2")
    assert resp_p2.status_code == 200
    assert "Academic Notice 14" in resp_p2.text

    # Out of range page redirects to last page (Decision D002)
    resp_out = client.get("/?page=999", follow_redirects=False)
    assert resp_out.status_code == 303
    assert "page=2" in resp_out.headers["location"]

    # Search filter: case-insensitive query
    resp_search = client.get("/?q=notice+number+5")
    assert resp_search.status_code == 200
    assert "Academic Notice 5" in resp_search.text
    assert "Academic Notice 6" not in resp_search.text

    # Category filter
    resp_cat = client.get(f"/?category={NoticeCategory.EVENT}")
    assert resp_cat.status_code == 200
    assert "Academic Notice 1" in resp_cat.text  # i=1 is EVENT
    assert "Academic Notice 0" not in resp_cat.text  # i=0 is ACADEMIC

    # Batch filter
    resp_batch = client.get(f"/?batch_id={batch2.id}")
    assert resp_batch.status_code == 200
    assert "Academic Notice 10" in resp_batch.text
    assert "Academic Notice 0" not in resp_batch.text


def test_html_escaping_and_unsafe_links(client: TestClient, session: Session):
    # Notice with HTML/scripts
    malicious_body = "<script>alert('xss')</script><b>BoldText</b>"
    malicious_title = "<script>alert('title')</script>SafeTitle"
    notice = Notice(
        title=malicious_title,
        body=malicious_body,
        category=NoticeCategory.GENERAL,
        status=NoticeStatus.PUBLISHED,
        published_at=datetime.now(UTC),
    )
    session.add(notice)
    session.commit()

    # Home page check
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert "<script>" not in resp_home.text
    escaped_tag = html.escape("<script>")
    assert escaped_tag in resp_home.text or "&lt;script&gt;" in resp_home.text

    # Detail page check
    resp_detail = client.get(f"/notices/{notice.id}")
    assert resp_detail.status_code == 200
    assert "<script>" not in resp_detail.text
    assert "&lt;script&gt;" in resp_detail.text

    # Admin attempt to post javascript: or data: link must be rejected
    auth_client, csrf_token = get_authenticated_client(client, session)

    resp_bad_js_link = auth_client.post(
        "/admin/notices/new",
        data={
            "title": "Bad JS Link Notice",
            "body": "Body content",
            "category": NoticeCategory.GENERAL,
            "external_link": "javascript:alert(1)",
            "status": "published",
            "csrf_token": csrf_token,
        },
    )
    assert resp_bad_js_link.status_code == 400
    err_msg = "External link must start with http:// or https://"
    assert err_msg in resp_bad_js_link.text

    resp_bad_data_link = auth_client.post(
        "/admin/notices/new",
        data={
            "title": "Bad Data Link Notice",
            "body": "Body content",
            "category": NoticeCategory.GENERAL,
            "external_link": "data:text/html,<html>attack</html>",
            "status": "published",
            "csrf_token": csrf_token,
        },
    )
    assert resp_bad_data_link.status_code == 400
    assert err_msg in resp_bad_data_link.text


def test_drafts_never_appear_publicly(client: TestClient, session: Session):
    draft_notice = Notice(
        title="Top Secret Draft Notice",
        body="Confidential internal draft information",
        category=NoticeCategory.ACADEMIC,
        status=NoticeStatus.DRAFT,
        published_at=None,
    )
    session.add(draft_notice)
    session.commit()

    # 1. Must NOT appear on home page
    resp_home = client.get("/")
    assert "Top Secret Draft Notice" not in resp_home.text

    # 2. Must NOT appear in search
    resp_search = client.get("/?q=Top+Secret")
    assert "Top Secret Draft Notice" not in resp_search.text

    # 3. Must return 404 to visitor on detail page
    resp_detail_visitor = client.get(f"/notices/{draft_notice.id}")
    assert resp_detail_visitor.status_code == 404

    # 4. Authenticated admin CAN view the draft
    auth_client, _ = get_authenticated_client(client, session)
    resp_detail_admin = auth_client.get(f"/notices/{draft_notice.id}")
    assert resp_detail_admin.status_code == 200
    assert "Top Secret Draft Notice" in resp_detail_admin.text


def test_external_link_field_has_helpful_copy(client: TestClient, session: Session):
    """The notice form's external link field must explain how previews work.

    Admins should know that the link opens in a new tab and the host site
    handles the preview, and they should be guided toward PDF-friendly URLs.
    """
    auth_client, _ = get_authenticated_client(client, session)

    # 1. The new-notice form should include the help text.
    resp = auth_client.get("/admin/notices/new")
    assert resp.status_code == 200
    body = resp.text
    assert 'id="external_link"' in body
    assert "drive.google.com" in body.lower(), "Help text should mention Drive"
    assert "opens in a new tab" in body
    assert "preview" in body.lower()
    # Placeholder should give a useful example URL, not just example.com
    assert "drive.google.com" in body or "notice.pdf" in body


def test_external_link_validation_still_works(client: TestClient, session: Session):
    """The improved copy must not weaken URL validation."""
    auth_client, csrf_token = get_authenticated_client(client, session)
    # Get a fresh form to ensure CSRF token matches this session
    fresh = auth_client.get("/admin/notices/new")
    fresh_token = re.search(r'name="csrf_token" value="([^"]+)"', fresh.text).group(1)
    resp = auth_client.post(
        "/admin/notices/new",
        data={
            "title": "Bad Link Test",
            "body": "Testing bad link",
            "category": "General",
            "external_link": "javascript:alert(1)",
            "status": "published",
            "csrf_token": fresh_token,
        },
    )
    # 400 with error message because javascript: is not http/https
    assert resp.status_code == 400
    assert "http://" in resp.text or "https://" in resp.text


def test_admin_notice_crud_workflow(client: TestClient, session: Session):
    auth_client, csrf_token = get_authenticated_client(client, session)

    # 1. Create notice
    resp_create = auth_client.post(
        "/admin/notices/new",
        data={
            "title": "CRUD Test Notice",
            "body": "Initial body text",
            "category": NoticeCategory.EXAM,
            "external_link": "https://university.edu/exam-info",
            "status": "published",
            "is_pinned": "true",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_create.status_code == 303
    assert resp_create.headers["location"] == "/admin/notices"

    notice = session.exec(
        select(Notice).where(Notice.title == "CRUD Test Notice")
    ).first()
    assert notice is not None
    assert notice.is_pinned is True
    assert notice.external_link == "https://university.edu/exam-info"

    # 2. Update notice
    resp_update = auth_client.post(
        f"/admin/notices/{notice.id}/edit",
        data={
            "title": "CRUD Test Notice Updated",
            "body": "Updated body content",
            "category": NoticeCategory.SCHOLARSHIP,
            "status": "published",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_update.status_code == 303
    session.refresh(notice)
    assert notice.title == "CRUD Test Notice Updated"
    assert notice.category == NoticeCategory.SCHOLARSHIP

    # 3. Delete notice
    resp_delete = auth_client.post(
        f"/admin/notices/{notice.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert resp_delete.status_code == 303
    deleted_notice = session.get(Notice, notice.id)
    assert deleted_notice is None
