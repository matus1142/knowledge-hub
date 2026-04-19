from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Comment, Topic
from schemas import CommentCreate, CommentUpdate, CommentOut

router = APIRouter(tags=["comments"])


@router.get("/topics/{topic_id}/comments", response_model=list[CommentOut])
def list_comments(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    return db.query(Comment).filter(Comment.topic_id == topic_id).order_by(Comment.created_at.asc()).all()


@router.post("/topics/{topic_id}/comments", response_model=CommentOut)
def create_comment(topic_id: int, body: CommentCreate, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    comment = Comment(topic_id=topic_id, content=body.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.put("/topics/{topic_id}/comments/{comment_id}", response_model=CommentOut)
def update_comment(topic_id: int, comment_id: int, body: CommentUpdate, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.topic_id == topic_id).first()
    if not comment:
        raise HTTPException(404, "Comment not found")
    comment.content = body.content
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/topics/{topic_id}/comments/{comment_id}")
def delete_comment(topic_id: int, comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.topic_id == topic_id).first()
    if not comment:
        raise HTTPException(404, "Comment not found")
    db.delete(comment)
    db.commit()
    return {"ok": True}
