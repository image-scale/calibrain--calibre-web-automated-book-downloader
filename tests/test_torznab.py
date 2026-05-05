"""Tests for the Torznab XML parser."""

import pytest

from bookdl.prowlarr.torznab import coerce_float, coerce_int, parse_torznab_xml


class TestCoerceInt:
    """Tests for coerce_int helper function."""

    def test_valid_integer_string(self):
        """coerce_int converts valid integer string."""
        assert coerce_int("42") == 42

    def test_negative_integer(self):
        """coerce_int handles negative integers."""
        assert coerce_int("-10") == -10

    def test_whitespace_is_stripped(self):
        """coerce_int strips whitespace."""
        assert coerce_int("  123  ") == 123

    def test_none_returns_none(self):
        """coerce_int returns None for None input."""
        assert coerce_int(None) is None

    def test_empty_string_returns_none(self):
        """coerce_int returns None for empty string."""
        assert coerce_int("") is None

    def test_whitespace_only_returns_none(self):
        """coerce_int returns None for whitespace-only string."""
        assert coerce_int("   ") is None

    def test_invalid_string_returns_none(self):
        """coerce_int returns None for non-numeric string."""
        assert coerce_int("abc") is None

    def test_float_string_returns_none(self):
        """coerce_int returns None for float string."""
        assert coerce_int("3.14") is None


class TestCoerceFloat:
    """Tests for coerce_float helper function."""

    def test_valid_float_string(self):
        """coerce_float converts valid float string."""
        assert coerce_float("3.14") == 3.14

    def test_integer_string(self):
        """coerce_float handles integer string."""
        assert coerce_float("42") == 42.0

    def test_negative_float(self):
        """coerce_float handles negative floats."""
        assert coerce_float("-2.5") == -2.5

    def test_whitespace_is_stripped(self):
        """coerce_float strips whitespace."""
        assert coerce_float("  1.5  ") == 1.5

    def test_none_returns_none(self):
        """coerce_float returns None for None input."""
        assert coerce_float(None) is None

    def test_empty_string_returns_none(self):
        """coerce_float returns None for empty string."""
        assert coerce_float("") is None

    def test_invalid_string_returns_none(self):
        """coerce_float returns None for non-numeric string."""
        assert coerce_float("abc") is None


class TestParseTorznabXml:
    """Tests for parse_torznab_xml function."""

    def test_parses_basic_item(self):
        """parse_torznab_xml extracts basic item fields."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Book</title>
                    <guid>12345</guid>
                    <link>https://example.com/download</link>
                    <comments>https://example.com/info</comments>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert len(results) == 1
        assert results[0]["title"] == "Test Book"
        assert results[0]["guid"] == "12345"
        assert results[0]["downloadUrl"] == "https://example.com/download"
        assert results[0]["infoUrl"] == "https://example.com/info"

    def test_extracts_size(self):
        """parse_torznab_xml extracts size as integer."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <size>1048576</size>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["size"] == 1048576

    def test_determines_torrent_protocol(self):
        """parse_torznab_xml determines torrent protocol from enclosure."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <enclosure url="https://example.com/file.torrent" type="application/x-bittorrent"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["protocol"] == "torrent"

    def test_determines_usenet_protocol(self):
        """parse_torznab_xml determines usenet protocol from enclosure."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <enclosure url="https://example.com/file.nzb" type="application/x-nzb"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["protocol"] == "usenet"

    def test_extracts_seeders_leechers(self):
        """parse_torznab_xml extracts seeders and calculates leechers."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
            <channel>
                <item>
                    <title>Test</title>
                    <torznab:attr name="seeders" value="10"/>
                    <torznab:attr name="peers" value="15"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["seeders"] == 10
        assert results[0]["leechers"] == 5

    def test_extracts_author_booktitle(self):
        """parse_torznab_xml extracts author and booktitle."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
            <channel>
                <item>
                    <title>The Way of Kings by Brandon Sanderson</title>
                    <torznab:attr name="author" value="Brandon Sanderson"/>
                    <torznab:attr name="booktitle" value="The Way of Kings"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["author"] == "Brandon Sanderson"
        assert results[0]["bookTitle"] == "The Way of Kings"
        # Title should have author stripped
        assert results[0]["title"] == "The Way of Kings"

    def test_extracts_indexer_info(self):
        """parse_torznab_xml extracts indexer name and ID."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <prowlarrindexer id="42">MyIndexer</prowlarrindexer>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["indexer"] == "MyIndexer"
        assert results[0]["indexerId"] == 42

    def test_extracts_categories(self):
        """parse_torznab_xml extracts category IDs."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <category>7000</category>
                    <category>7020</category>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["categories"] == [7000, 7020]

    def test_extracts_volume_factors(self):
        """parse_torznab_xml extracts download/upload volume factors."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
            <channel>
                <item>
                    <title>Test</title>
                    <torznab:attr name="downloadvolumefactor" value="0.5"/>
                    <torznab:attr name="uploadvolumefactor" value="2.0"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["downloadVolumeFactor"] == 0.5
        assert results[0]["uploadVolumeFactor"] == 2.0

    def test_extracts_tags_as_indexer_flags(self):
        """parse_torznab_xml extracts tags into indexerFlags list."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
            <channel>
                <item>
                    <title>Test</title>
                    <torznab:attr name="tag" value="freeleech"/>
                    <torznab:attr name="tag" value="vip"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert "freeleech" in results[0]["indexerFlags"]
        assert "vip" in results[0]["indexerFlags"]

    def test_returns_empty_for_empty_string(self):
        """parse_torznab_xml returns empty list for empty string."""
        result = parse_torznab_xml("")
        assert result == []

    def test_returns_empty_for_whitespace(self):
        """parse_torznab_xml returns empty list for whitespace-only string."""
        result = parse_torznab_xml("   \n\t   ")
        assert result == []

    def test_returns_empty_for_invalid_xml(self):
        """parse_torznab_xml returns empty list for invalid XML."""
        result = parse_torznab_xml("<not valid xml")
        assert result == []

    def test_returns_empty_for_xml_without_items(self):
        """parse_torznab_xml returns empty list when no items present."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Empty Channel</title>
            </channel>
        </rss>"""

        result = parse_torznab_xml(xml)
        assert result == []

    def test_handles_missing_optional_fields(self):
        """parse_torznab_xml handles items with missing optional fields."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Minimal Item</title>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert len(results) == 1
        assert results[0]["title"] == "Minimal Item"
        assert results[0]["size"] is None
        assert results[0]["seeders"] is None
        assert results[0]["author"] is None

    def test_uses_enclosure_url_as_fallback(self):
        """parse_torznab_xml uses enclosure URL when link is missing."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test</title>
                    <enclosure url="https://example.com/fallback" type="application/x-bittorrent"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["downloadUrl"] == "https://example.com/fallback"

    def test_generates_guid_from_fallbacks(self):
        """parse_torznab_xml generates guid from available fields when missing."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Book</title>
                    <comments>https://example.com/info</comments>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        # Should fall back to info_url when guid is missing
        assert results[0]["guid"] == "https://example.com/info"

    def test_parses_multiple_items(self):
        """parse_torznab_xml parses multiple items."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item><title>Book 1</title></item>
                <item><title>Book 2</title></item>
                <item><title>Book 3</title></item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert len(results) == 3
        assert results[0]["title"] == "Book 1"
        assert results[1]["title"] == "Book 2"
        assert results[2]["title"] == "Book 3"

    def test_stores_all_attrs_in_torznab_attrs(self):
        """parse_torznab_xml stores all torznab attributes."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
            <channel>
                <item>
                    <title>Test</title>
                    <torznab:attr name="custom" value="value1"/>
                    <torznab:attr name="another" value="value2"/>
                </item>
            </channel>
        </rss>"""

        results = parse_torznab_xml(xml)

        assert results[0]["torznabAttrs"]["custom"] == "value1"
        assert results[0]["torznabAttrs"]["another"] == "value2"


class TestXXEProtection:
    """Tests to verify XXE protection is working."""

    def test_rejects_xxe_attack(self):
        """parse_torznab_xml rejects XML with XXE attack attempts."""
        # This XML attempts to read /etc/passwd via XXE
        malicious_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
          <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <rss version="2.0">
            <channel>
                <item>
                    <title>&xxe;</title>
                </item>
            </channel>
        </rss>"""

        # Should return empty list and not raise or leak file content
        result = parse_torznab_xml(malicious_xml)
        assert result == []

    def test_rejects_billion_laughs_attack(self):
        """parse_torznab_xml rejects billion laughs XML bomb."""
        malicious_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE lolz [
          <!ENTITY lol "lol">
          <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
          <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <rss version="2.0">
            <channel>
                <item>
                    <title>&lol3;</title>
                </item>
            </channel>
        </rss>"""

        # Should return empty list and not consume excessive resources
        result = parse_torznab_xml(malicious_xml)
        assert result == []
