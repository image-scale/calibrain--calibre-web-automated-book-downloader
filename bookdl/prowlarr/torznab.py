"""Torznab/Newznab XML parser for Prowlarr.

Parses torrent/usenet search results from Prowlarr indexers using
the Torznab/Newznab XML format with XXE protection.
"""

from __future__ import annotations

from typing import Any

from defusedxml import ElementTree as DefusedElementTree
from defusedxml.common import DefusedXmlException


def _local_name(tag: str) -> str:
    """Return tag name without namespace prefix.

    Args:
        tag: Full tag name potentially with namespace

    Returns:
        Tag name without namespace
    """
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def coerce_int(value: str | None) -> int | None:
    """Coerce a string value to integer.

    Args:
        value: String value to convert

    Returns:
        Integer value, or None if conversion fails
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def coerce_float(value: str | None) -> float | None:
    """Coerce a string value to float.

    Args:
        value: String value to convert

    Returns:
        Float value, or None if conversion fails
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _strip_author_from_title(title: str, author: str | None) -> str:
    """Strip duplicate trailing author text from a Torznab title.

    Some indexers append " by {author}" to the title while also
    emitting author as a separate field.

    Args:
        title: Original title
        author: Author name to remove

    Returns:
        Title with author suffix removed if present
    """
    if not title or not author:
        return title

    needle = f" by {author}"
    if needle in title:
        return title.replace(needle, "", 1).strip()

    return title


def parse_torznab_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse a Torznab/Newznab XML response into result dictionaries.

    Uses defusedxml for protection against XXE and other XML attacks.
    The parsed structure is similar to Prowlarr's JSON search results.

    Args:
        xml_text: Raw XML response text

    Returns:
        List of result dictionaries with parsed fields
    """
    if not xml_text or not xml_text.strip():
        return []

    try:
        root = DefusedElementTree.fromstring(xml_text)
    except (DefusedElementTree.ParseError, DefusedXmlException):
        return []

    items = root.findall(".//item")
    results: list[dict[str, Any]] = []

    for item in items:
        # Basic fields
        title = (item.findtext("title") or "").strip()
        guid = (item.findtext("guid") or "").strip() or None
        download_url = (item.findtext("link") or "").strip() or None
        info_url = (item.findtext("comments") or "").strip() or None
        pub_date = (item.findtext("pubDate") or "").strip() or None

        size = coerce_int(item.findtext("size"))

        # Enclosure for download URL and protocol detection
        enclosure = item.find("enclosure")
        enclosure_type = enclosure.get("type") if enclosure is not None else None
        enclosure_url = enclosure.get("url") if enclosure is not None else None

        protocol: str | None = None
        if enclosure_type == "application/x-bittorrent":
            protocol = "torrent"
        elif enclosure_type == "application/x-nzb":
            protocol = "usenet"

        if not download_url and enclosure_url:
            download_url = enclosure_url.strip() or None

        # Prowlarr indexer info
        prowlarr_indexer_el = item.find("prowlarrindexer")
        indexer_id = (
            coerce_int(prowlarr_indexer_el.get("id"))
            if prowlarr_indexer_el is not None
            else None
        )
        indexer_name = (
            (prowlarr_indexer_el.text or "").strip()
            if prowlarr_indexer_el is not None
            else ""
        )

        # Categories
        categories: list[int] = []
        for cat_el in item.findall("category"):
            cat_id = coerce_int(cat_el.text)
            if cat_id is not None:
                categories.append(cat_id)

        # Torznab/Newznab attr elements (potentially namespaced)
        attrs: dict[str, str] = {}
        tags: list[str] = []
        for el in item.iter():
            if _local_name(el.tag) != "attr":
                continue
            name = (el.get("name") or "").strip()
            value = (el.get("value") or "").strip()
            if not name:
                continue
            if name == "tag" and value:
                tags.append(value)
                continue
            if value:
                attrs[name] = value

        # Extract commonly used attributes
        seeders = coerce_int(attrs.get("seeders"))
        peers = coerce_int(attrs.get("peers"))
        leechers: int | None = None
        if peers is not None and seeders is not None and peers >= seeders:
            leechers = peers - seeders

        author = attrs.get("author") or None
        book_title = attrs.get("booktitle") or None
        info_hash = attrs.get("infohash") or None

        download_volume_factor = coerce_float(attrs.get("downloadvolumefactor"))
        upload_volume_factor = coerce_float(attrs.get("uploadvolumefactor"))
        minimum_ratio = coerce_float(attrs.get("minimumratio"))
        minimum_seed_time = coerce_int(attrs.get("minimumseedtime"))

        # Clean up title if author is duplicated
        cleaned_title = _strip_author_from_title(title, author)

        results.append(
            {
                "title": cleaned_title or title,
                "guid": guid or info_url or download_url or f"{indexer_id}:{title}",
                "size": size,
                "protocol": protocol or "unknown",
                "downloadUrl": download_url,
                "infoUrl": info_url,
                "publishDate": pub_date,
                "indexer": indexer_name or None,
                "indexerId": indexer_id,
                "categories": categories,
                "seeders": seeders,
                "leechers": leechers,
                "files": coerce_int(attrs.get("files")),
                "grabs": coerce_int(attrs.get("grabs")),
                "infoHash": info_hash,
                "indexerFlags": tags,
                "author": author,
                "bookTitle": book_title,
                "downloadVolumeFactor": download_volume_factor,
                "uploadVolumeFactor": upload_volume_factor,
                "minimumRatio": minimum_ratio,
                "minimumSeedTime": minimum_seed_time,
                "torznabAttrs": attrs,
            }
        )

    return results
