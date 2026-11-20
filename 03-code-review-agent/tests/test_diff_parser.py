from pathlib import Path

from code_review.tools.diff_parser import chunk_diff, parse_diff

SAMPLE = (Path(__file__).parents[1] / "samples" / "example.diff").read_text(
    encoding="utf-8"
)


def test_parse_files_counts_and_test_flag():
    files = parse_diff(SAMPLE)

    assert [f.path for f in files] == ["app/users.py", "tests/test_users.py"]
    assert (files[0].added, files[0].removed) == (17, 0)
    assert [f.is_test for f in files] == [False, True]
    assert (
        files[0].header.startswith("diff --git")
        and "+++ b/app/users.py" in files[0].header
    )


def test_chunk_numbers_lines_with_new_file_line_numbers():
    chunk = chunk_diff(SAMPLE, 6000)[0]

    line = next(x for x in chunk.splitlines() if "find_user" in x)
    assert line.split()[0] == "11"  # find_user is line 11 of the new app/users.py


def test_small_diff_is_one_chunk_and_big_diff_splits_per_file():
    assert len(chunk_diff(SAMPLE, 6000)) == 1
    chunks = chunk_diff(SAMPLE, 100)
    assert len(chunks) == 2
    assert "app/users.py" in chunks[0] and "tests/test_users.py" in chunks[1]


def test_huge_file_is_split_by_hunks_and_keeps_its_header():
    hunks = "".join(
        f"@@ -{i * 10},1 +{i * 10},1 @@\n-old\n+new line {i} " + "x" * 200 + "\n"
        for i in range(1, 6)
    )
    diff = "diff --git a/big.py b/big.py\n--- a/big.py\n+++ b/big.py\n" + hunks

    chunks = chunk_diff(diff, 120)

    assert len(chunks) > 1
    assert all(c.startswith("diff --git a/big.py") for c in chunks)


def test_empty_diff_has_no_chunks():
    assert chunk_diff("", 6000) == []
