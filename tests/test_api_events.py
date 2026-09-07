from datetime import date

from japan_events.api.app import _build_events_response
from japan_events.models import CombinedOutput, Event, SiteResult


def test_build_events_response_keeps_only_selected_date():
    combined = CombinedOutput(
        date="2026-09-07",
        generated_at="2026-09-07T00:00:00Z",
        site_count=1,
        ok_count=1,
        event_count=2,
        sites=[
            SiteResult(
                prefecture="Tokyo",
                id="tokyo",
                ok=True,
                date="2026-09-07",
                event_count=2,
                events=[
                    Event(
                        prefecture="Tokyo",
                        title="On selected day",
                        start_date="2026-09-07",
                        source="test",
                    ),
                    Event(
                        prefecture="Tokyo",
                        title="Other day",
                        start_date="2026-09-01",
                        end_date="2026-09-02",
                        source="test",
                    ),
                ],
            )
        ],
    )

    res = _build_events_response(
        combined,
        prefecture=None,
        scraped=False,
        lang=None,
        target=date(2026, 9, 7),
    )

    assert [event.title for event in res.events] == ["On selected day"]
    assert res.event_count == 1
    assert res.sites[0].event_count == 1
