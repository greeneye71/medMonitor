from datetime import datetime, timedelta, timezone

from app import notifier, settings

T0 = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)


def configure(db):
    settings.set(db, "smtp", {"host": "smtp.example.com", "port": 587, "user": "u",
                              "password": "p", "sender": "mm@example.com"})
    settings.set(db, "recipients", ["a@example.com"])


def ok_sender(calls):
    async def sender(smtp, recipients, subject, text, html):
        calls.append((recipients, subject))
    return sender


async def failing_sender(smtp, recipients, subject, text, html):
    raise ConnectionError("smtp down")


def test_render_kinds():
    sensor = {"name": "Frigo 1", "min_c": 2, "max_c": 8, "last_battery": 15, "last_temp": 5,
              "last_seen_at": None}
    for kind in ["temp_open", "temp_close", "offline_open", "offline_close", "battery_open",
                 "test"]:
        subject, text, html = notifier.render(kind, sensor, T0, value=9.5, minutes=120)
        assert subject.startswith("[medMonitor]")
        assert text and "<div" in html
    assert "9,5" in notifier.render("temp_open", sensor, T0, value=9.5)[0]


def test_send_ok(db):
    configure(db)
    notifier.notify(db, T0, "test")
    calls = []
    assert notifier.process_outbox(db, T0, ok_sender(calls)) == 1
    assert calls == [(["a@example.com"], calls[0][1])]
    assert db.one("SELECT sent_at FROM outbox")["sent_at"] is not None
    assert notifier.pending_count(db) == 0


def test_failure_retries_and_logs_once(db):
    configure(db)
    notifier.notify(db, T0, "test")
    for i in range(5):
        notifier.process_outbox(db, T0 + timedelta(minutes=i), failing_sender)
    row = db.one("SELECT * FROM outbox")
    assert row["attempts"] == 5 and "smtp down" in row["last_error"]
    errors = db.query("SELECT * FROM events WHERE type='EMAIL_ERROR'")
    assert len(errors) == 1
    # after 5 failures: retry only every >= 10 min
    notifier.process_outbox(db, T0 + timedelta(minutes=6), failing_sender)
    assert db.one("SELECT attempts FROM outbox")["attempts"] == 5
    notifier.process_outbox(db, T0 + timedelta(minutes=14), failing_sender)
    assert db.one("SELECT attempts FROM outbox")["attempts"] == 6
    assert len(db.query("SELECT * FROM events WHERE type='EMAIL_ERROR'")) == 1
    calls = []
    notifier.process_outbox(db, T0 + timedelta(minutes=30), ok_sender(calls))
    assert len(calls) == 1 and notifier.pending_count(db) == 0


def test_unconfigured_smtp_keeps_queue(db):
    notifier.notify(db, T0, "test")
    calls = []
    assert notifier.process_outbox(db, T0, ok_sender(calls)) == 0
    assert calls == [] and notifier.pending_count(db) == 1
    assert db.one("SELECT attempts FROM outbox")["attempts"] == 0


def test_send_email_returns_refused_recipients(monkeypatch):
    import asyncio

    from aiosmtplib import SMTPResponse

    async def fake_send(msg, **kw):
        return {"b@example.com": SMTPResponse(550, "mailbox unavailable")}, "OK"
    monkeypatch.setattr(notifier.aiosmtplib, "send", fake_send)
    refused = asyncio.run(notifier.send_email({"host": "h"}, ["a@example.com", "b@example.com"],
                                              "s", "t", "<p>h</p>"))
    assert list(refused) == ["b@example.com"]


def test_partial_refusal_logs_email_error(db):
    configure(db)
    settings.set(db, "recipients", ["a@example.com", "b@example.com"])
    notifier.notify(db, T0, "test")

    async def partial_sender(smtp, recipients, subject, text, html):
        return {"b@example.com": (550, "mailbox unavailable")}
    assert notifier.process_outbox(db, T0, partial_sender) == 1
    assert notifier.pending_count(db) == 0          # delivered to the others: no resend
    errors = db.query("SELECT message FROM events WHERE type='EMAIL_ERROR'")
    assert len(errors) == 1 and "b@example.com" in errors[0]["message"]
    assert "a@example.com" not in errors[0]["message"]
