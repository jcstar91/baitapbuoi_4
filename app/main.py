from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from app.schemas import ExtractIn, ConfirmIn
from .database import Base, make_session_factory
from fastapi import FastAPI
from fastapi import HTTPException
from .config import Settings, get_settings
from fastapi import Request, Depends, Response, Query

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from .services.ticket_queue import calculate_deadline, SLA_MIN

from .model_db import Ticket
from .dependencies import get_db
from .services.extractor import read_message_openai, AIError


VN_TZ = timezone(timedelta(hours=7))

def now_vn() -> datetime:
    return datetime.now(VN_TZ)

def find_ticket_by_id(db: Session, ticket_id: int) -> Ticket:
    return db.get(Ticket, ticket_id)

QUEUED = "queued"

def count_queued(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Ticket).where(Ticket.status == QUEUED))

def queue_item(rank: int, row: Ticket) -> dict:
    return {
        "rank": rank,
        "ticket_id": row.id,
        "intent": row.intent,
        "severity": row.severity,
        "product": row.product,
        "summary": row.summary,
        "received_at": row.received_at,
        "deadline_at": row.deadline_at,
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(app.state.engine)
    yield
    app.state.engine.dispose()

def create_app(settings: Settings, clock=now_vn) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    
    engine, session_factory = make_session_factory(settings.database_url)
    
    app.state.engine = engine
    app.state.session_factory = session_factory
    
    app.state.settings = settings

    @app.post("/tickets/extract")
    async def extract_ticket(payload: ExtractIn, db: Session = Depends(get_db)):
        
        received_at = clock()
        row = Ticket(
            received_at=received_at,
            raw_message=payload.message
        )
        db.add(row)
        db.commit()
        
        try:
            data = read_message_openai(row.id, payload.message, app.state.settings)
        except AIError as exc:
            # Keep the saved ticket but flag it so a human handles it.
            row.needs_human_review = True
            row.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=502,
                detail={"ticket_id": row.id, "message": str(exc)},
            ) from exc

        row.status = "extracted"
        row.intent = data.intent
        row.severity = data.severity
        row.product = data.product
        row.summary = data.summary
        row.needs_human_review = data.needs_human_review
        db.commit()

        return {
            "ticket_id": row.id,
            "received_at": row.received_at,
            "extracted": {
                "intent": row.intent,
                "severity": row.severity,
                "product": row.product,
                "summary": row.summary,
                "needs_human_review": row.needs_human_review,
            },
        }
    
    
    @app.post("/tickets/confirm")
    def confirm_ticket(payload: ConfirmIn, db: Session = Depends(get_db)):
        ticket = find_ticket_by_id(db, payload.ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Update the ticket with the confirmed data first: the SLA deadline depends on the confirmed severity.
        ticket.intent = payload.extracted.get("intent", ticket.intent)
        ticket.severity = payload.extracted.get("severity", ticket.severity)
        ticket.product = payload.extracted.get("product", ticket.product)
        ticket.summary = payload.extracted.get("summary", ticket.summary)
        ticket.needs_human_review = payload.extracted.get("needs_human_review", ticket.needs_human_review)

        if ticket.severity not in SLA_MIN:
            raise HTTPException(status_code=422, detail=f"Invalid severity: {ticket.severity}")

        ticket.deadline_at = calculate_deadline(ticket.received_at, ticket.severity)
        ticket.status = QUEUED
        db.commit()

        return {
            "ticket_id": ticket.id,
            "severity": ticket.severity,
            "sla_minutes": SLA_MIN[ticket.severity],
            "deadline_at": ticket.deadline_at,
            "queue_size": count_queued(db),
        }

    @app.get("/ticket/queue")
    def get_queue(limit: int = Query(..., ge=1, le=100), db: Session = Depends(get_db)):
        # The queue lives in the database so it survives restarts and works with multiple workers.
        stmt = (
            select(Ticket)
            .where(Ticket.status == QUEUED)
            .order_by(Ticket.deadline_at, Ticket.received_at, Ticket.id)
            .limit(limit)
        )
        rows = db.scalars(stmt).all()
        items = [queue_item(rank, row) for rank, row in enumerate(rows, start=1)]
        return {"total": count_queued(db), "items": items}
    
    
    return app

app = create_app(get_settings())

