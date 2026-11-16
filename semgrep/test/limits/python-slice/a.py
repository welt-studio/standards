from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


@router.get("/a/{name}")
async def preview(name: str):
    base = name[: -len(".bin")]
    Path(f"{base}.png").is_file()


@router.get("/b/{name}")
async def first(name: str):
    Path(name[0]).is_file()
