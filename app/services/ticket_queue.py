
from datetime import datetime, timedelta
from typing import Literal
from pydantic import BaseModel
from app.model_db import Ticket


SLA_MIN = {"critical": 30, "high": 120, "medium": 480, "low": 1440}
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


class QueuedTicket(BaseModel):
    ticket_id: int
    severity: Literal["critical", "high", "medium", "low"]
    received_at: datetime
    deadline: datetime


def calculate_deadline(received_at: datetime, severity: str) -> datetime:
    return received_at + timedelta(minutes=SLA_MIN[severity])

def make_queue_ticket(ticket_id: int, severity: str, received_at:datetime) -> QueuedTicket:
    deadline = calculate_deadline(received_at, severity)
    return QueuedTicket(ticket_id=ticket_id, severity=severity, received_at=received_at, deadline=deadline)

def top_priority_ticket(ticket: QueuedTicket) -> tuple:
    return (ticket.deadline, -SEVERITY_RANK[ticket.severity], ticket.received_at, ticket.ticket_id)


class TicketQueue:
    def __init__(self):
        self.heap=[]
        self.ids=set()
        
    def __len__(self):
        return len(self.heap)
    
    def add_ticket(self, ticket: Ticket):
        if ticket.id in self.ids:
            return
        queued_ticket = make_queue_ticket(ticket.id, ticket.severity, ticket.received_at)
        self.heap.append(queued_ticket)
        self.ids.add(ticket.id)
        self.heap.sort(key=top_priority_ticket)
    
    def top_k(self, k: int):
        return self.heap[:k]
    