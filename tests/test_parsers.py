from depmirage.parsers import parse_requirements, normalize_name, pypi_normalize


def test_strips_version_specifiers():
    reqs = "\n".join([
        "requests==2.31.0",
        "flask>=2.0",
        "urllib3<=1.26.0",
        "numpy~=1.24",
        "pandas!=1.5.0",
        "scipy>1.0",
        "click<9",
    ])
    assert parse_requirements(reqs) == [
        "requests", "flask", "urllib3", "numpy", "pandas", "scipy", "click",
    ]


def test_strips_extras_and_markers():
    reqs = "\n".join([
        "requests[security]==2.31.0",
        "importlib-metadata; python_version < '3.8'",
        "uvicorn[standard]",
    ])
    assert parse_requirements(reqs) == [
        "requests", "importlib-metadata", "uvicorn",
    ]


def test_ignores_comments_blanks_options_and_urls():
    reqs = "\n".join([
        "# a comment",
        "",
        "requests  # inline comment",
        "-r other.txt",
        "-e .",
        "--hash=sha256:abc",
        "git+https://github.com/psf/requests.git",
        "https://example.com/pkg-1.0.tar.gz",
    ])
    assert parse_requirements(reqs) == ["requests"]


def test_dedup_preserves_first_occurrence():
    reqs = "requests\nReQuEsts==2.0\nrequests"
    assert parse_requirements(reqs) == ["requests"]


def test_normalize_name_edge_cases():
    assert normalize_name("  flask >= 2.0  ") == "flask"
    assert normalize_name("pkg[extra]") == "pkg"
    assert normalize_name("pkg==1.0 ; sys_platform == 'win32'") == "pkg"


def test_pypi_normalize():
    assert pypi_normalize("Foo.Bar_baz") == "foo-bar-baz"
    assert pypi_normalize("A--B") == "a-b"
