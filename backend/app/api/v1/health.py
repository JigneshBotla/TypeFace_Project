from fastapi import APIRouter
from app.schemas.simple import Health

router = APIRouter()

@router.get('/health', response_model=Health)
def health():
    return {'status': 'ok'}
