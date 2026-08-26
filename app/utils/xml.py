import codecs
import re
from typing import Any
import xml.etree.ElementTree as ET


CONTROL_RE = re.compile(r"&#(?:x)?([0-9A-Fa-f]+);")


def detect_and_decode_xml(data: bytes) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if data.startswith(codecs.BOM_UTF8):
        text = data.decode("utf-8-sig")
        return "UTF-8", text, warnings
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        text = data.decode("utf-16")
        return "UTF-16", text, warnings
    try:
        text = data.decode("utf-8")
        return "UTF-8", text, warnings
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-16")
            return "UTF-16", text, warnings
        except UnicodeDecodeError:
            raise ValueError("Unsupported or undecodable XML encoding")


def sanitize_xml_text(xml_text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    sanitized = xml_text

    def replace_invalid_ref(match: re.Match[str]) -> str:
        raw_value = match.group(1)
        is_hex = match.group(0).lower().startswith("&#x")
        value = int(raw_value, 16 if is_hex else 10)
        if value < 32 and value not in (9, 10, 13):
            warnings.append(f"Sanitized illegal XML numeric control reference {match.group(0)}")
            return " "
        return match.group(0)

    sanitized = CONTROL_RE.sub(replace_invalid_ref, sanitized)
    sanitized = "".join(ch if ch in "\n\t\r" or ord(ch) >= 32 else " " for ch in sanitized)
    if sanitized != xml_text:
        warnings.append("Removed XML control characters that are not valid in XML 1.0")
    return sanitized, warnings


def parse_xml_document(raw_bytes: bytes) -> tuple[str, ET.Element, str, list[str]]:
    detected_encoding, xml_text, initial_warnings = detect_and_decode_xml(raw_bytes)
    sanitized_text, sanitizer_warnings = sanitize_xml_text(xml_text)
    warnings = initial_warnings + sanitizer_warnings
    try:
        root = ET.fromstring(sanitized_text.encode("utf-8"))
    except ET.ParseError:
        root = ET.fromstring(sanitized_text)
    return detected_encoding, root, detected_encoding, warnings
