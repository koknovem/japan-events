from japan_events.scan import is_dirty, normalize_body


def test_is_dirty_ignores_first_seen_and_errors():
    current = {"etag": "abc", "sha256": "1", "status": 200, "error": None}
    assert is_dirty(None, current) is False
    assert is_dirty({"etag": "abc"}, {**current, "error": "timeout"}) is False
    assert is_dirty({"etag": "abc"}, {**current, "status": 503, "etag": "zzz"}) is False


def test_is_dirty_prefers_etag_then_hash():
    assert is_dirty({"etag": "a"}, {"etag": "b", "status": 200, "error": None}) is True
    assert is_dirty({"etag": "a"}, {"etag": "a", "sha256": "changed", "status": 200, "error": None}) is False
    assert is_dirty({"sha256": "old"}, {"sha256": "new", "status": 200, "error": None, "etag": None}) is True
    assert is_dirty({"sha256": "same"}, {"sha256": "same", "status": 200, "error": None}) is False


def test_normalize_body_strips_scripts_and_stable_json():
    html = b"<html><script>token=1</script><h1>Festival</h1><style>x</style></html>"
    out = normalize_body("text/html", html)
    assert b"script" not in out.lower()
    assert b"Festival" in out

    a = normalize_body("application/json", b'{"b":1,"a":2}')
    b = normalize_body("application/json", b'{"a": 2, "b": 1}')
    assert a == b
