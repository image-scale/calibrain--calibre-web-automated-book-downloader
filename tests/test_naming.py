"""Tests for the naming module - template parsing and library path building."""

import tempfile
from pathlib import Path

import pytest

from bookdl.core.naming import (
    assign_part_numbers,
    build_library_path,
    derive_primary_title,
    format_series_position,
    natural_sort_key,
    parse_naming_template,
    sanitize_filename,
    same_filesystem,
)


class TestNaturalSortAndAssignment:
    """Tests for natural sorting and part number assignment."""

    def test_natural_sort_simple_numbers(self):
        """Numbers sort naturally (2 < 10)."""
        files = ["Part 2.mp3", "Part 10.mp3", "Part 1.mp3"]
        assert sorted(files, key=natural_sort_key) == ["Part 1.mp3", "Part 2.mp3", "Part 10.mp3"]

    def test_natural_sort_cd_track_pattern(self):
        """Complex patterns with multiple numbers sort correctly."""
        files = ["CD2_Track10.mp3", "CD1_Track2.mp3", "CD1_Track10.mp3", "CD2_Track1.mp3"]
        assert sorted(files, key=natural_sort_key) == [
            "CD1_Track2.mp3",
            "CD1_Track10.mp3",
            "CD2_Track1.mp3",
            "CD2_Track10.mp3",
        ]

    def test_assign_part_numbers_empty(self):
        """Empty list returns empty list."""
        assert assign_part_numbers([]) == []

    def test_assign_part_numbers_sorted(self):
        """Files are sorted and assigned sequential part numbers."""
        files = [Path("Part 3.mp3"), Path("Part 1.mp3"), Path("Part 2.mp3")]
        assert assign_part_numbers(files) == [
            (Path("Part 1.mp3"), "01"),
            (Path("Part 2.mp3"), "02"),
            (Path("Part 3.mp3"), "03"),
        ]

    def test_assign_part_numbers_custom_padding(self):
        """Custom zero-padding width is respected."""
        files = [Path("a.mp3"), Path("b.mp3")]
        assert assign_part_numbers(files, zero_pad_width=3) == [
            (Path("a.mp3"), "001"),
            (Path("b.mp3"), "002"),
        ]

    def test_no_false_positives_fahrenheit_451(self):
        """Numbers in titles don't cause incorrect sorting."""
        files = [Path("Fahrenheit 451 - Part 2.mp3"), Path("Fahrenheit 451 - Part 1.mp3")]
        result = assign_part_numbers(files)
        assert result[0] == (Path("Fahrenheit 451 - Part 1.mp3"), "01")


class TestParseNamingTemplate:
    """Tests for template parsing with variable substitution."""

    def test_simple_substitution(self):
        """Basic token replacement works."""
        result = parse_naming_template(
            "{Author}/{Title}", {"Author": "Brandon Sanderson", "Title": "The Way of Kings"}
        )
        assert result == "Brandon Sanderson/The Way of Kings"

    def test_conditional_suffix(self):
        """Conditional suffix is included only when value exists."""
        template = "{Author}/{Series/}{Title}"

        # With series
        result = parse_naming_template(
            template,
            {
                "Author": "Brandon Sanderson",
                "Series": "Stormlight Archive",
                "Title": "The Way of Kings",
            },
        )
        assert result == "Brandon Sanderson/Stormlight Archive/The Way of Kings"

        # Without series
        result = parse_naming_template(
            template, {"Author": "Brandon Sanderson", "Series": None, "Title": "The Way of Kings"}
        )
        assert result == "Brandon Sanderson/The Way of Kings"

    def test_conditional_prefix(self):
        """Conditional prefix is included only when value exists."""
        template = "{Title}{ - Subtitle}"

        # With subtitle
        result = parse_naming_template(
            template, {"Title": "The Way of Kings", "Subtitle": "Journey Before Destination"}
        )
        assert result == "The Way of Kings - Journey Before Destination"

        # Without subtitle
        result = parse_naming_template(
            template, {"Title": "The Way of Kings", "Subtitle": None}
        )
        assert result == "The Way of Kings"

    def test_empty_template(self):
        """Empty template returns empty string."""
        assert parse_naming_template("", {"Title": "Book"}) == ""

    def test_case_insensitive_placeholders(self):
        """Placeholder matching is case-insensitive."""
        result = parse_naming_template("{AUTHOR}/{title}", {"Author": "Jane", "Title": "Book"})
        assert result == "Jane/Book"

    def test_series_position_formatting(self):
        """SeriesPosition is formatted correctly in templates."""
        result = parse_naming_template(
            "{Series} {SeriesPosition}", {"Series": "Mistborn", "SeriesPosition": 2.0}
        )
        assert result == "Mistborn 2"

    def test_no_path_separators_option(self):
        """allow_path_separators=False replaces / with _."""
        result = parse_naming_template(
            "{Title}", {"Title": "Book/With/Slashes"}, allow_path_separators=False
        )
        assert result == "Book_With_Slashes"


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_replaces_invalid_characters(self):
        """Invalid characters are replaced with underscores."""
        result = sanitize_filename('Book: A <Good> Story?')
        assert result == "Book_ A _Good_ Story_"

    def test_collapses_underscores(self):
        """Multiple underscores are collapsed to one."""
        result = sanitize_filename("Book___With___Underscores")
        assert result == "Book_With_Underscores"

    def test_strips_dots_and_whitespace(self):
        """Leading/trailing dots and whitespace are stripped."""
        result = sanitize_filename("...  Book Title  ...")
        assert result == "Book Title"

    def test_truncates_to_max_length(self):
        """Result is truncated to max_length."""
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 245

    def test_custom_max_length(self):
        """Custom max_length is respected."""
        result = sanitize_filename("A" * 100, max_length=50)
        assert len(result) == 50

    def test_empty_input(self):
        """Empty input returns empty string."""
        assert sanitize_filename("") == ""
        assert sanitize_filename(None) == ""


class TestFormatSeriesPosition:
    """Tests for series position formatting."""

    def test_whole_number_as_integer(self):
        """Whole number floats are displayed as integers."""
        assert format_series_position(2.0) == "2"
        assert format_series_position(10.0) == "10"

    def test_decimal_preserved(self):
        """Decimal values are preserved."""
        assert format_series_position(1.5) == "1.5"

    def test_integer_input(self):
        """Integer input is converted to string."""
        assert format_series_position(3) == "3"

    def test_string_input(self):
        """String input is passed through."""
        assert format_series_position("4") == "4"

    def test_none_returns_empty(self):
        """None returns empty string."""
        assert format_series_position(None) == ""


class TestDerivePrimaryTitle:
    """Tests for primary title derivation."""

    def test_extracts_primary_from_colon_separator(self):
        """Extracts title before colon separator."""
        result = derive_primary_title("The Way of Kings: Book One", "Book One")
        assert result == "The Way of Kings"

    def test_extracts_primary_from_dash_separator(self):
        """Extracts title before dash separator."""
        result = derive_primary_title("The Way of Kings - Book One", "Book One")
        assert result == "The Way of Kings"

    def test_no_subtitle_returns_full_title(self):
        """When no subtitle, returns full title."""
        result = derive_primary_title("The Way of Kings", None)
        assert result == "The Way of Kings"

    def test_subtitle_not_found_returns_full_title(self):
        """When subtitle not in title, returns full title."""
        result = derive_primary_title("The Way of Kings", "Different Subtitle")
        assert result == "The Way of Kings"

    def test_empty_title_returns_empty(self):
        """Empty title returns empty string."""
        assert derive_primary_title("", "Subtitle") == ""
        assert derive_primary_title(None, "Subtitle") == ""


class TestBuildLibraryPath:
    """Tests for library path building."""

    def test_basic_path_building(self):
        """Basic template produces correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_library_path(
                tmpdir, "{Author}/{Title}", {"Author": "Jane", "Title": "Book"}
            )
            expected = Path(tmpdir) / "Jane" / "Book"
            assert result == expected

    def test_with_extension(self):
        """Extension is added correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_library_path(
                tmpdir, "{Title}", {"Title": "My Book"}, extension="epub"
            )
            assert str(result).endswith(".epub")

    def test_extension_with_dot(self):
        """Extension with leading dot is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_library_path(
                tmpdir, "{Title}", {"Title": "Book"}, extension=".pdf"
            )
            assert str(result).endswith(".pdf")
            assert not str(result).endswith("..pdf")

    def test_fallback_to_title_on_empty_template(self):
        """Empty template result falls back to title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_library_path(tmpdir, "", {"Title": "Fallback Book"})
            assert "Fallback_Book" in str(result) or "Fallback Book" in str(result)

    def test_path_traversal_prevented(self):
        """Path traversal attempts are sanitized by removing '..'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # The ".." is stripped from the path, making it safe
            result = build_library_path(
                tmpdir, "{Author}", {"Author": "../../../etc"}
            )
            # The result should be inside the base directory
            assert str(result).startswith(str(Path(tmpdir).resolve()))
            # ".." should be removed
            assert ".." not in str(result)

    def test_double_dot_removed(self):
        """Double dots are removed from paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_library_path(
                tmpdir, "{Title}", {"Title": "Book..Name"}
            )
            # .. should be stripped, resulting in "BookName" or similar
            assert ".." not in str(result)


class TestSameFilesystem:
    """Tests for filesystem comparison."""

    def test_same_directory(self):
        """Paths in same directory are on same filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "file1.txt"
            path2 = Path(tmpdir) / "file2.txt"
            assert same_filesystem(path1, path2) is True

    def test_nonexistent_paths_use_parent(self):
        """Nonexistent paths check parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "nonexistent1.txt"
            path2 = Path(tmpdir) / "nonexistent2.txt"
            assert same_filesystem(path1, path2) is True

    def test_string_paths_accepted(self):
        """String paths are converted to Path objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = f"{tmpdir}/file1.txt"
            path2 = f"{tmpdir}/file2.txt"
            assert same_filesystem(path1, path2) is True
