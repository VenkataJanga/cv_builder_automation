from fastapi import Request

async def error_handler(request: Request, exc: Exception):
    return {'error': str(exc)}
