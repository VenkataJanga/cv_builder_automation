from fastapi.security import OAuth2PasswordBearer
from src.core.constants import AUTH_TOKEN_URL


# Declares the token URL that clients use to obtain a JWT.
# FastAPI uses this only for OpenAPI docs — actual validation happens in dependencies.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=AUTH_TOKEN_URL, auto_error=False)
