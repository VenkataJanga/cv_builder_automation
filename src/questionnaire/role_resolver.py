from src.core.config.loader import config_loader


def resolve_role(title: str) -> str:
    mapping = config_loader.load_role_mapping()
    title_lower = title.lower().strip()

    for role, titles in mapping.get("title_mapping", {}).items():
        for t in titles:
            if t.lower().strip() in title_lower:
                return role

    return "general"