from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import UserCreate, UserResponse, UserLogin, Token, KYCDocumentCreate, KYCDocumentResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, KYCDocument
from app.services.auth_service import get_password_hash, verify_password, create_access_token
from app.dependencies import get_tenant_session, get_current_user, get_db
from app.database import TenantScopedSession

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: TenantScopedSession = Depends(get_tenant_session)
):
    """
    Registers a new end-user for the authenticated tenant.
    Requires a valid X-API-Key header.
    """
    existing_user = await db.get_user_by_email(email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in your platform"
        )

    hashed_pwd = get_password_hash(user_in.password)

    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        phone=user_in.phone,
        date_of_birth=user_in.date_of_birth,
        country_code=user_in.country_code
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user

@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login_user(
    user_in: UserLogin,
    db: TenantScopedSession = Depends(get_tenant_session)
):
    """
    Authenticates an end-user and returns a JWT.
    The JWT payload includes both the user ID and the scoped tenant ID.
    Requires a valid X-API-Key header to resolve the tenant.
    """
    user = await db.get_user_by_email(email=user_in.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(user_in.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token_payload = {
        "sub": str(user.id),
        "tenant_id": str(db.tenant_id),
        "kyc_status": user.kyc_status
    }
    access_token = create_access_token(data=token_payload)

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the profile of the authenticated user.
    Requires both X-API-Key and the user's JWT.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to view this profile"
        )
    
    return current_user

# @router.post("/kyc", response_model=KYCDocumentResponse, status_code=status.HTTP_201_CREATED)
# async def submit_kyc_document(
#     kyc_in: KYCDocumentCreate,
#     current_user: User = Depends(get_current_user),
#     session: AsyncSession = Depends(get_db) 
# ):
#     """
#     Allows an authenticated end-user to submit a KYC document.
#     Updates their KYC status to UNDER_REVIEW.
#     Requires a valid user JWT.
#     """
#     db = TenantScopedSession(session, str(current_user.tenant_id))

#     new_doc = KYCDocument(
#         user_id=current_user.id,
#         document_type=kyc_in.document_type,
#         document_url=kyc_in.document_url,
#         document_ref=kyc_in.document_ref
#     )
#     db.add(new_doc)

#     current_user.kyc_status = "UNDER_REVIEW" #type: ignore
#     db.add(current_user)

#     await db.commit()
#     await db.refresh(new_doc)

#     return new_doc