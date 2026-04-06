def check_duplicates(cv_data: dict) -> list[str]:
    issues = []

    skills = cv_data.get("skills", {}).get("primary_skills", [])
    if len(skills) != len(set(skills)):
        issues.append("Duplicate entries found in primary skills.")

    leadership = cv_data.get("leadership", {})
    for key, values in leadership.items():
        if isinstance(values, list) and len(values) != len(set(values)):
            issues.append(f"Duplicate entries found in leadership section: {key}")

    return issues
