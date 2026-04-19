from __future__ import annotations

from pathlib import Path


def _find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    i = open_index
    in_string = False
    quote_char = ""
    escape = False

    while i < len(text):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i

        i += 1

    raise ValueError("Unbalanced braces in localization catalog")


def _skip_ws_and_commas(text: str, idx: int) -> int:
    while idx < len(text) and text[idx] in " \t\r\n,":
        idx += 1
    return idx


def _parse_key(text: str, idx: int) -> tuple[str, int]:
    idx = _skip_ws_and_commas(text, idx)
    start = idx
    if idx >= len(text) or not (text[idx].isalpha() or text[idx] in "_$"):
        raise ValueError(f"Invalid key start at index {idx}")

    idx += 1
    while idx < len(text) and (text[idx].isalnum() or text[idx] in "_$"):
        idx += 1

    return text[start:idx], idx


def _skip_value(text: str, idx: int) -> int:
    idx = _skip_ws_and_commas(text, idx)
    if idx >= len(text):
        return idx

    if text[idx] in ('"', "'"):
        quote = text[idx]
        idx += 1
        escape = False
        while idx < len(text):
            ch = text[idx]
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                idx += 1
                break
            idx += 1
        return idx

    if text[idx] == "{":
        end = _find_matching_brace(text, idx)
        return end + 1

    while idx < len(text) and text[idx] not in ",}":
        idx += 1
    return idx


def _parse_string_literal(text: str, idx: int) -> tuple[str, int]:
    quote = text[idx]
    idx += 1
    chars: list[str] = []
    escape = False

    while idx < len(text):
        ch = text[idx]
        if escape:
            chars.append(ch)
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == quote:
            idx += 1
            return "".join(chars), idx
        else:
            chars.append(ch)
        idx += 1

    raise ValueError("Unterminated string literal in localization catalog")


def _collect_leaf_paths(object_text: str, prefix: str = "") -> set[str]:
    paths: set[str] = set()

    idx = _skip_ws_and_commas(object_text, 0)
    if idx >= len(object_text) or object_text[idx] != "{":
        raise ValueError("Expected object start")

    idx += 1
    while idx < len(object_text):
        idx = _skip_ws_and_commas(object_text, idx)
        if idx >= len(object_text):
            break
        if object_text[idx] == "}":
            break

        key, idx = _parse_key(object_text, idx)
        idx = _skip_ws_and_commas(object_text, idx)
        if idx >= len(object_text) or object_text[idx] != ":":
            raise ValueError(f"Expected ':' after key '{key}'")

        idx += 1
        idx = _skip_ws_and_commas(object_text, idx)
        full_key = f"{prefix}.{key}" if prefix else key

        if idx < len(object_text) and object_text[idx] == "{":
            end = _find_matching_brace(object_text, idx)
            nested = object_text[idx : end + 1]
            paths.update(_collect_leaf_paths(nested, full_key))
            idx = end + 1
        else:
            paths.add(full_key)
            idx = _skip_value(object_text, idx)

        idx = _skip_ws_and_commas(object_text, idx)
        if idx < len(object_text) and object_text[idx] == ",":
            idx += 1

    return paths


def _collect_leaf_values(object_text: str, prefix: str = "") -> dict[str, str]:
    values: dict[str, str] = {}

    idx = _skip_ws_and_commas(object_text, 0)
    if idx >= len(object_text) or object_text[idx] != "{":
        raise ValueError("Expected object start")

    idx += 1
    while idx < len(object_text):
        idx = _skip_ws_and_commas(object_text, idx)
        if idx >= len(object_text) or object_text[idx] == "}":
            break

        key, idx = _parse_key(object_text, idx)
        idx = _skip_ws_and_commas(object_text, idx)
        if idx >= len(object_text) or object_text[idx] != ":":
            raise ValueError(f"Expected ':' after key '{key}'")

        idx += 1
        idx = _skip_ws_and_commas(object_text, idx)
        full_key = f"{prefix}.{key}" if prefix else key

        if idx < len(object_text) and object_text[idx] == "{":
            end = _find_matching_brace(object_text, idx)
            nested = object_text[idx : end + 1]
            values.update(_collect_leaf_values(nested, full_key))
            idx = end + 1
        else:
            if idx >= len(object_text) or object_text[idx] not in ('"', "'"):
                raise ValueError(f"Expected string value for key '{full_key}'")
            parsed_value, idx = _parse_string_literal(object_text, idx)
            values[full_key] = parsed_value

        idx = _skip_ws_and_commas(object_text, idx)
        if idx < len(object_text) and object_text[idx] == ",":
            idx += 1

    return values


def _extract_locale_object(catalog_text: str, locale: str) -> str:
    marker = f"{locale}:"
    marker_index = catalog_text.find(marker)
    if marker_index < 0:
        raise ValueError(f"Locale '{locale}' not found")

    open_index = catalog_text.find("{", marker_index)
    if open_index < 0:
        raise ValueError(f"Locale '{locale}' object start not found")

    close_index = _find_matching_brace(catalog_text, open_index)
    return catalog_text[open_index : close_index + 1]


def test_ui_localization_en_de_have_same_leaf_keys() -> None:
    localization_file = Path("web-ui/static/js/localization.js")
    source = localization_file.read_text(encoding="utf-8")

    en_object = _extract_locale_object(source, "en")
    de_object = _extract_locale_object(source, "de")

    en_keys = _collect_leaf_paths(en_object)
    de_keys = _collect_leaf_paths(de_object)

    missing_in_de = sorted(en_keys - de_keys)
    extra_in_de = sorted(de_keys - en_keys)

    assert not missing_in_de and not extra_in_de, (
        "UI localization key mismatch between en and de.\n"
        f"Missing in de: {missing_in_de}\n"
        f"Extra in de: {extra_in_de}"
    )


def test_ui_localization_critical_values_are_non_empty() -> None:
    localization_file = Path("web-ui/static/js/localization.js")
    source = localization_file.read_text(encoding="utf-8")

    critical_prefixes = ("ui.", "auth.", "validation.")

    for locale in ("en", "de"):
        locale_object = _extract_locale_object(source, locale)
        values = _collect_leaf_values(locale_object)
        critical_values = {
            key: value
            for key, value in values.items()
            if any(key.startswith(prefix) for prefix in critical_prefixes)
        }

        assert critical_values, f"No critical localization keys found for locale '{locale}'"

        blank_critical_keys = [
            key for key, value in critical_values.items() if not value.strip()
        ]
        assert not blank_critical_keys, (
            f"Blank critical localization values found for locale '{locale}': "
            f"{blank_critical_keys}"
        )
