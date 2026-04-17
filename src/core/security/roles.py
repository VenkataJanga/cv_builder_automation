from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    USER = "user"
    DELIVERY_MANAGER = "delivery_manager"
    CV_EDITOR = "cv_editor"
