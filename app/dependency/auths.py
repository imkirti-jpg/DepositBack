from uuid import UUID
from app.core.config import settings
import jwt
from jwt import PyJWKClient
import traceback
from fastapi import Depends,HTTPException,status

from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_jwks, get_jwks_client
from app.db.database import get_db
from app.services.provision_service import UserProvisioningService

security = HTTPBearer()
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    try:
        jwks_client = get_jwks_client()

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        header = jwt.get_unverified_header(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[header["alg"]],
            audience="authenticated",
        )

        user_id = UUID(payload["sub"])

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or authentication failed",
        )
    
    
    profile = await UserProvisioningService.provision_user(
        db,
        user_id,
    )

    return profile