"""Template-based naming for library organization.

Supports placeholder substitution with conditionals like:
- {Author}/{Title} - basic substitution
- {Series/}{Title} - conditional suffix (includes "/" only if Series has value)
- {Title}{ - Subtitle} - conditional prefix (includes " - " only if Subtitle has value)
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


# Known variable tokens, sorted longest-first to avoid partial matches
KNOWN_TOKENS = [
    "seriesposition",
    "primarytitle",
    "originalname",
    "partnumber",
    "subtitle",
    "author",
    "series",
    "title",
    "year",
    "user",
]

# Match any {...} block for template parsing
BRACE_PATTERN = re.compile(r"\{([^}]+)\}")

# Characters that are invalid in filenames on various filesystems
INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename(name: str | None, max_length: int = 245) -> str:
    """Sanitize a string for use as a filename or path component.

    Replaces invalid characters with underscores, collapses multiple
    underscores, strips leading/trailing whitespace and dots, and
    truncates to max_length.

    Args:
        name: The string to sanitize
        max_length: Maximum length of result (default 245)

    Returns:
        Sanitized filename string
    """
    if not name:
        return ""

    # Replace invalid characters
    sanitized = INVALID_CHARS.sub("_", name)
    # Strip leading/trailing whitespace and dots
    sanitized = re.sub(r"^[\s.]+|[\s.]+$", "", sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized[:max_length]


def format_series_position(position: str | float | None) -> str:
    """Format a series position for naming templates.

    Displays as integer if the value is a whole number.

    Args:
        position: Series position (e.g., 1, 1.5, "2")

    Returns:
        Formatted position string, or empty string if None
    """
    if position is None:
        return ""

    # Display as integer if whole number
    if isinstance(position, float) and position.is_integer():
        return str(int(position))

    return str(position)


def derive_primary_title(title: str | None, subtitle: str | None) -> str:
    """Return the title without an explicit subtitle suffix when possible.

    If the title contains the subtitle as a suffix (separated by : or -),
    returns just the primary title portion.

    Args:
        title: Full title string
        subtitle: Subtitle to strip if present

    Returns:
        Primary title without subtitle suffix
    """
    title_value = " ".join(str(title or "").split()).strip()
    if not title_value:
        return ""

    subtitle_value = " ".join(str(subtitle or "").split()).strip()
    if not subtitle_value:
        return title_value

    # Pattern matches "Primary Title: Subtitle" or "Primary Title - Subtitle"
    pattern = rf"^(?P<primary>.+?)(?:\s*:\s*|\s+-\s+){re.escape(subtitle_value)}$"
    match = re.match(pattern, title_value, flags=re.IGNORECASE)
    if not match:
        return title_value

    primary = match.group("primary").strip()
    return primary or title_value


# Pads numbers to 9 digits for natural sorting
PAD_NUMBERS_PATTERN = re.compile(r"\d+")


def natural_sort_key(path: str | Path) -> str:
    """Generate a sort key with padded numbers for natural sorting.

    Ensures "Part 2" comes before "Part 10".

    Args:
        path: File path to generate sort key for

    Returns:
        Sort key string with zero-padded numbers
    """
    filename = Path(path).name.lower()
    return PAD_NUMBERS_PATTERN.sub(lambda m: m.group().zfill(9), filename)


def assign_part_numbers(
    files: list[Path],
    zero_pad_width: int = 2,
) -> list[tuple[Path, str]]:
    """Sort files naturally and assign sequential part numbers.

    Args:
        files: List of file paths to sort and number
        zero_pad_width: Width for zero-padding part numbers (default 2)

    Returns:
        List of (file_path, part_number_string) tuples, sorted naturally
    """
    if not files:
        return []

    sorted_files = sorted(files, key=natural_sort_key)
    return [
        (file_path, str(part_num).zfill(zero_pad_width))
        for part_num, file_path in enumerate(sorted_files, start=1)
    ]


def parse_naming_template(
    template: str,
    metadata: "Mapping[str, str | int | float | None]",
    *,
    allow_path_separators: bool = True,
) -> str:
    """Render a naming template with metadata placeholders.

    Supports:
    - Basic substitution: {Author}, {Title}
    - Conditional suffix: {Series/} - includes "/" only if Series has value
    - Conditional prefix: { - Subtitle} - includes " - " only if Subtitle has value

    Args:
        template: Template string with {placeholder} tokens
        metadata: Dictionary of placeholder values
        allow_path_separators: If False, replaces "/" in values with "_"

    Returns:
        Rendered template string
    """
    if not template:
        return ""

    # Normalize metadata keys to lowercase for case-insensitive matching
    normalized = {k.lower(): v for k, v in metadata.items()}

    def find_placeholder(content: str) -> tuple[str | None, int]:
        """Find a known placeholder in content."""
        content_lower = content.lower()
        for placeholder_name in KNOWN_TOKENS:
            idx = content_lower.find(placeholder_name)
            if idx != -1:
                return placeholder_name, idx
        return None, -1

    def placeholder_value(placeholder_name: str) -> str:
        """Get the value for a placeholder."""
        value = normalized.get(placeholder_name)
        if placeholder_name == "seriesposition":
            value = format_series_position(value)
        if value is None:
            return ""
        return str(value).strip()

    def render_block(content: str) -> str | None:
        """Render a single {...} block."""
        placeholder_name, idx = find_placeholder(content)
        if placeholder_name is None:
            return None

        prefix = content[:idx]
        suffix = content[idx + len(placeholder_name) :]
        value = placeholder_value(placeholder_name)
        if not value:
            return ""

        if not allow_path_separators:
            value = value.replace("/", "_")
        value = sanitize_filename(value)
        return f"{prefix}{value}{suffix}"

    # Process brace blocks in order
    matches = list(BRACE_PATTERN.finditer(template))
    if not matches:
        result = template
    else:
        parts: list[str] = []
        cursor = 0
        for idx, match in enumerate(matches):
            parts.append(template[cursor : match.start()])
            content = match.group(1)
            rendered = render_block(content)

            if rendered is not None:
                parts.append(rendered)
            else:
                # Check for conditional literal (adjacent block)
                conditional_literal = False
                include_literal = False
                if idx + 1 < len(matches) and match.end() == matches[idx + 1].start():
                    next_content = matches[idx + 1].group(1)
                    next_placeholder_name, _next_idx = find_placeholder(next_content)
                    if next_placeholder_name is not None:
                        conditional_literal = True
                        include_literal = bool(placeholder_value(next_placeholder_name))
                if include_literal:
                    parts.append(content)
                elif not conditional_literal and re.search(r"\s", content):
                    # Preserve blocks that look like literal text
                    parts.append(match.group(0))

            cursor = match.end()

        parts.append(template[cursor:])
        result = "".join(parts)

    # Clean up any double slashes
    result = re.sub(r"/+", "/", result)

    # Remove leading/trailing slashes
    result = result.strip("/")

    # Clean up orphaned separators
    result = re.sub(r"^[\s\-_.]+", "", result)
    result = re.sub(r"[\s\-_.]+$", "", result)
    result = re.sub(r"(\s*-\s*){2,}", " - ", result)

    # Clean up empty parentheses/brackets
    result = re.sub(r"\(\s*\)", "", result)
    result = re.sub(r"\[\s*\]", "", result)

    # Final trim
    return re.sub(r"[\s\-_.]+$", "", result)


def build_library_path(
    base_path: str,
    template: str,
    metadata: "Mapping[str, str | int | float | None]",
    extension: str | None = None,
) -> Path:
    """Build a final library path from a template and metadata.

    Args:
        base_path: Base directory for the library
        template: Naming template with placeholders
        metadata: Dictionary of placeholder values
        extension: Optional file extension to append

    Returns:
        Full Path object for the library location

    Raises:
        ValueError: If the resulting path would escape the base directory
    """
    relative = parse_naming_template(template, metadata, allow_path_separators=True)

    if not relative:
        # Fallback to title if template produces empty result
        title = metadata.get("Title") or metadata.get("title") or "Unknown"
        relative = sanitize_filename(str(title))

    # Remove any path traversal attempts
    relative = relative.replace("..", "")

    base = Path(base_path).resolve()
    full_path = (base / relative).resolve()

    # Verify the path is within the base directory
    try:
        full_path.relative_to(base)
    except ValueError as exc:
        msg = "Path traversal detected: template would escape library directory"
        raise ValueError(msg) from exc

    if extension:
        ext = extension.lstrip(".")
        # Don't use with_suffix() - it replaces everything after the first dot
        full_path = Path(f"{full_path}.{ext}")

    return full_path


def same_filesystem(path1: str | Path, path2: str | Path) -> bool:
    """Check if two paths are on the same filesystem.

    Args:
        path1: First path to check
        path2: Second path to check

    Returns:
        True if both paths are on the same filesystem
    """
    path1 = Path(path1)
    path2 = Path(path2)

    def get_device(p: Path) -> int | None:
        try:
            while not p.exists():
                p = p.parent
                if p == p.parent:
                    break
            return p.stat().st_dev
        except (OSError, PermissionError):
            return None

    dev1 = get_device(path1)
    dev2 = get_device(path2)

    if dev1 is None or dev2 is None:
        return False

    return dev1 == dev2
