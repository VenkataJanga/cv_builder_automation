def check_chronology(cv_data: dict) -> list[str]:
    issues = []
    work_experience = cv_data.get("work_experience", [])
    for item in work_experience:
        if not isinstance(item, dict):
            continue
        start = item.get("start_date")
        end = item.get("end_date")
        if start and end and str(start) > str(end):
            issues.append(f"Invalid chronology: {start} is after {end}.")
    return issues
