def check_quality(cv_data: dict) -> dict:
    warnings = []
    suggestions = []

    summary = cv_data.get("summary", "")
    if isinstance(summary, dict):
        summary = str(summary.get("professional_summary", ""))
    elif isinstance(summary, list):
        summary = " ".join(
            str(item.get("professional_summary", "")) if isinstance(item, dict) else str(item)
            for item in summary
        )
    else:
        summary = str(summary)

    summary = summary.strip()
    if summary and len(summary.split()) < 8:
        warnings.append("Professional summary is very short.")
        suggestions.append("Expand summary to include role, strengths, and impact.")

    leadership = cv_data.get("leadership", {})
    for key, values in leadership.items():
        if isinstance(values, list):
            for value in values:
                text = str(value).lower()
                if all(token not in text for token in ["%", "improved", "reduced", "saved", "increased"]):
                    warnings.append(f"{key.replace('_', ' ').title()} may be missing measurable impact.")
                    suggestions.append(f"Add metrics or outcomes to {key.replace('_', ' ')}.")

    return {
        "warnings": warnings,
        "suggestions": suggestions,
    }
