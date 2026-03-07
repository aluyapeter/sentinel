from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import KYCDocumentCreate, KYCDocumentResponse
from app.models import User, KYCDocument
from app.dependencies import get_current_user, get_db
from app.database import TenantScopedSession
from app.tasks.mock_webhook import simulate_kyc_processing

router = APIRouter(prefix="/users", tags=["KYC"])

@router.post("/{user_id}/kyc/submit", response_model=KYCDocumentResponse, status_code=status.HTTP_201_CREATED)
async def submit_kyc_document(
    user_id: str,
    kyc_in: KYCDocumentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db) 
):
    """
    Accepts a KYC document URL, updates the user's status, and triggers 
    the background processing task.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to submit documents for this user"
        )

    db = TenantScopedSession(session, str(current_user.tenant_id))

    new_doc = KYCDocument(
        user_id=current_user.id,
        document_type=kyc_in.document_type,
        document_url=kyc_in.document_url,
        document_ref=kyc_in.document_ref
    )
    db.add(new_doc)

    current_user.kyc_status = "UNDER_REVIEW"  # type: ignore
    db.add(current_user)

    await db.commit()
    await db.refresh(new_doc)

    background_tasks.add_task(
        simulate_kyc_processing,
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        document_id=str(new_doc.id)
    )

    return new_doc


@router.get("/{user_id}/kyc/status", status_code=status.HTTP_200_OK)
async def get_kyc_status(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Allows the frontend to poll for the user's current KYC status.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to view this status"
        )
    
    return {
        "user_id": user_id,
        "kyc_status": current_user.kyc_status
    }