"""模块列表。"""

from fastapi import APIRouter

from app.modules_data import MODULES

router = APIRouter(prefix="/api", tags=["modules"])


@router.get("/modules")
async def list_modules():
    return {"modules": MODULES}
