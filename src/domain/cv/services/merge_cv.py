class MergeCVService:
    """
    Merge uploaded/parsing/speech-extracted data into existing session CV data.

    Rules:
    - Existing manually answered values win
    - Missing fields are filled from parsed data
    - List fields are merged uniquely
    """

    def merge(self, existing: dict, parsed: dict) -> dict:
        for key, value in parsed.items():
            if key == "skills" and isinstance(value, dict):
                # Special handling for skills: ensure it's a dict
                if not isinstance(existing.get(key), dict):
                    # If existing skills is a list, convert to dict with primary_skills
                    existing_skills = existing.get(key, [])
                    if isinstance(existing_skills, list):
                        existing[key] = {"primary_skills": existing_skills}
                    else:
                        existing[key] = {}
                # Now merge as dict
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        current = existing[key].get(sub_key, [])
                        merged = list(current) if isinstance(current, list) else []
                        for item in sub_value:
                            if item not in merged:
                                merged.append(item)
                        existing[key][sub_key] = merged
                    else:
                        if not existing[key].get(sub_key):
                            existing[key][sub_key] = sub_value
            elif isinstance(value, dict):
                existing.setdefault(key, {})
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        current = existing[key].get(sub_key, [])
                        merged = list(current) if isinstance(current, list) else []
                        for item in sub_value:
                            if item not in merged:
                                merged.append(item)
                        existing[key][sub_key] = merged
                    else:
                        if not existing[key].get(sub_key):
                            existing[key][sub_key] = sub_value
            elif isinstance(value, list):
                # Handle top-level list fields (skills, etc.)
                current = existing.get(key, [])
                merged = list(current) if isinstance(current, list) else []
                for item in value:
                    if item not in merged:
                        merged.append(item)
                existing[key] = merged
            else:
                if not existing.get(key):
                    existing[key] = value
        return existing
