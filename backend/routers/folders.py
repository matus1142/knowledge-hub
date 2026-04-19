from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Folder
from schemas import FolderCreate, FolderUpdate, FolderOut

router = APIRouter(prefix="/folders", tags=["folders"])


def build_tree(folders: list[Folder], parent_id=None) -> list[FolderOut]:
    result = []
    for f in folders:
        if f.parent_id == parent_id:
            out = FolderOut(
                id=f.id,
                name=f.name,
                parent_id=f.parent_id,
                created_at=f.created_at,
                children=build_tree(folders, f.id),
            )
            result.append(out)
    return result


@router.get("", response_model=list[FolderOut])
def list_folders(db: Session = Depends(get_db)):
    folders = db.query(Folder).all()
    return build_tree(folders, parent_id=None)


@router.post("", response_model=FolderOut)
def create_folder(body: FolderCreate, db: Session = Depends(get_db)):
    if body.parent_id:
        parent = db.query(Folder).filter(Folder.id == body.parent_id).first()
        if not parent:
            raise HTTPException(404, "Parent folder not found")
    folder = Folder(name=body.name, parent_id=body.parent_id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return FolderOut(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        created_at=folder.created_at,
        children=[],
    )


@router.put("/{folder_id}", response_model=FolderOut)
def update_folder(folder_id: int, body: FolderUpdate, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(404, "Folder not found")
    folder.name = body.name
    db.commit()
    db.refresh(folder)
    return FolderOut(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        created_at=folder.created_at,
        children=[],
    )


@router.delete("/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(404, "Folder not found")
    db.delete(folder)
    db.commit()
    return {"ok": True}
