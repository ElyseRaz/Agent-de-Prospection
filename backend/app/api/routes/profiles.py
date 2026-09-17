import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_embedding_backend
from app.embeddings.base import EmbeddingBackend
from app.models.matching import MatchFeedbackAction
from app.models.profile import Profile
from app.models.user import User, UserRole
from app.schemas.job import JobRead
from app.schemas.matching import MatchFeedbackCreate, MatchListResponse, MatchRead
from app.schemas.profile import (
    ProfileCreate,
    ProfileDetailRead,
    ProfileRead,
    ProfileSkillInput,
    ProfileSkillRead,
    ProfileUpdate,
)
from app.services.matching import compute_top_matches, record_match_feedback
from app.services.profile import get_profile_skills, set_profile_skills

router = APIRouter(prefix="/profiles", tags=["profiles"])


async def _get_owned_profile(
    db: AsyncSession, profile_id: uuid.UUID, current_user: User
) -> Profile:
    profile = await db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable")
    if profile.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Ce profil ne vous appartient pas"
        )
    return profile


async def _to_detail_read(db: AsyncSession, profile: Profile) -> ProfileDetailRead:
    rows = await get_profile_skills(db, profile.id)
    skills = [
        ProfileSkillRead(
            skill_slug=slug, skill_label=label, level=level, years=years, is_required=is_required
        )
        for slug, label, level, years, is_required in rows
    ]
    return ProfileDetailRead(**ProfileRead.model_validate(profile).model_dump(), skills=skills)


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Profile:
    profile = Profile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("", response_model=list[ProfileRead])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Profile]:
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id).order_by(Profile.created_at)
    )
    return list(result.scalars())


@router.get("/{profile_id}", response_model=ProfileDetailRead)
async def get_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileDetailRead:
    profile = await _get_owned_profile(db, profile_id, current_user)
    return await _to_detail_read(db, profile)


@router.patch("/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: uuid.UUID,
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Profile:
    profile = await _get_owned_profile(db, profile_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    profile = await _get_owned_profile(db, profile_id, current_user)
    await db.delete(profile)
    await db.commit()


@router.put("/{profile_id}/skills", response_model=ProfileDetailRead)
async def put_profile_skills(
    profile_id: uuid.UUID,
    payload: list[ProfileSkillInput],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
) -> ProfileDetailRead:
    profile = await _get_owned_profile(db, profile_id, current_user)
    await set_profile_skills(db, profile, payload, embedding_backend=embedding_backend)
    await db.refresh(profile)
    return await _to_detail_read(db, profile)


@router.get("/{profile_id}/matches", response_model=MatchListResponse)
async def get_profile_matches(
    profile_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchListResponse:
    profile = await _get_owned_profile(db, profile_id, current_user)
    results = await compute_top_matches(db, profile, limit=limit)
    return MatchListResponse(
        results=[
            MatchRead(
                job=JobRead.model_validate(result.job),
                score=result.score,
                breakdown=[
                    {"criterion": item.criterion, "points": item.points, "label": item.label}
                    for item in result.breakdown
                ],
            )
            for result in results
        ]
    )


@router.post("/{profile_id}/matches/{job_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def post_match_feedback(
    profile_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: MatchFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    profile = await _get_owned_profile(db, profile_id, current_user)
    await record_match_feedback(db, profile, job_id, MatchFeedbackAction(payload.action))
