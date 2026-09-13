from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models import Message
from app.schemas.schemas import FeedbackRequest

router = APIRouter(prefix="/api", tags=["feedback"])
logger = get_logger(__name__)


@router.post("/feedback", status_code=204)
async def submit_feedback(body: FeedbackRequest, db: AsyncSession = Depends(get_db)) -> None:
    message = await db.get(Message, body.message_id)
    if message is None:
        raise NotFoundError(f"Message {body.message_id} not found")

    # Feedback is logged (for offline review) rather than stored in its own table - there's no
    # requirement to query/aggregate it from the product yet, and adding a table for
    # write-only data nobody reads back would be premature.
    logger.info(
        "feedback_received",
        message_id=str(body.message_id),
        rating=body.rating,
        comment=body.comment,
    )
