from depmirage.secrets import scan_text, mask, shannon_entropy


def test_mask_shows_first_and_last_four():
    m = mask("sk-abcdefghijklmnopqrstuvwxyz")
    assert m.startswith("sk-a")
    assert m.endswith("wxyz")
    assert "*" in m
    # never leaks the middle
    assert "efghijklmno" not in m


def test_mask_short_secret_fully_hidden():
    assert mask("abcd1234") == "*" * 8
    assert set(mask("short")) == {"*"}


def test_detects_openai_key():
    text = 'OPENAI_API_KEY = "sk-demo1234567890ABCDEFghijKLMNopqrSTUV"'
    findings = scan_text(text, "x.py")
    kinds = {f.kind for f in findings}
    assert "OpenAI API key" in kinds
    # value must be masked in every finding
    for f in findings:
        assert "sk-demo1234567890" not in f.masked


def test_detects_aws_key():
    text = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"'
    findings = scan_text(text, "x.py")
    assert any(f.kind == "AWS access key" for f in findings)


def test_detects_secret_assignment_with_entropy():
    text = 'API_TOKEN = "f3Kd9sLmZ0qXvB2nP7rT1wY8cA6eH4jU"'
    findings = scan_text(text, "x.py")
    assert findings
    assert all("f3Kd9sLm" not in f.masked or f.masked.startswith("f3Kd")
               for f in findings)


def test_reports_line_numbers():
    text = "\n".join([
        "x = 1",
        "y = 2",
        'SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"',
    ])
    findings = scan_text(text, "x.py")
    assert any(f.line == 3 for f in findings)


def test_ignores_ordinary_prose_strings():
    text = 'greeting = "hello there, this is a normal sentence in code"'
    findings = scan_text(text, "x.py")
    assert findings == []


def test_shannon_entropy_ranges():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") > 1.5
