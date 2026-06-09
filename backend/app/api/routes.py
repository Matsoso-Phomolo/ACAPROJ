from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.ids.engine import ids_engine
from app.schemas.requests import LoginRequest, RegisterRequest
from app.services.auth_service import authenticate_user, current_user, register_user, users
from app.services.file_service import (
    cluster_status,
    corrupt_node_chunk,
    list_user_files,
    reconstruct_file,
    store_file,
    toggle_node_health,
    file_pipeline,
    demo_flow,
)

router = APIRouter(prefix="/api")


@router.post("/register")
def register(data: RegisterRequest):
    register_user(data.username, data.password)
    return {"message": "registered"}


@router.post("/login")
def login(data: LoginRequest, request: Request):
    token = authenticate_user(data.username, data.password, request)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), username: str = Depends(current_user)):
    raw = await file.read()
    return store_file(username, file.filename or "uploaded-file", raw)


@router.get("/files")
def list_files(username: str = Depends(current_user)):
    return list_user_files(username)


@router.get("/files/{file_id}/download")
def download_file(file_id: str, username: str = Depends(current_user)):
    content, filename = reconstruct_file(file_id, username)
    return StreamingResponse(
        iter([content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/nodes/{node_id}/corrupt-one-chunk")
def corrupt_one_chunk(node_id: str, username: str = Depends(current_user)):
    return corrupt_node_chunk(node_id)


@router.post("/nodes/{node_id}/toggle")
def toggle_node(node_id: str, username: str = Depends(current_user)):
    return toggle_node_health(node_id)


@router.get("/status")
def status():
    data = cluster_status()
    data["user_count"] = len(users)
    return data


@router.get("/files/{file_id}/pipeline")
def get_file_pipeline(file_id: str, username: str = Depends(current_user)):
    return file_pipeline(file_id, username)


@router.get("/demo-flow")
def get_demo_flow():
    return demo_flow()


@router.get("/alerts")
def get_alerts():
    return list(reversed(ids_engine.alerts[-100:]))


@router.get("/events")
def get_events():
    return list(reversed(ids_engine.events[-200:]))
