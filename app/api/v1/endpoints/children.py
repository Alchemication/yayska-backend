import json

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import DatabaseError, NotFoundError, ValidationError
from app.schemas.children import (
    ChildCreate,
    ChildrenListResponse,
    ChildResponse,
    ChildUpdate,
)
from app.utils.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=ChildrenListResponse)
async def get_children(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Get all children for the current user"""
    query = text("""
        SELECT 
            c.id,
            c.user_id,
            c.name,
            c.school_year_id,
            c.memory,
            c.created_at,
            c.updated_at,
            sy.year_name as school_year_name
        FROM children c
        LEFT JOIN school_years sy ON c.school_year_id = sy.id
        WHERE c.user_id = :user_id
        ORDER BY c.created_at ASC
    """)

    try:
        result = await db.execute(query, {"user_id": current_user["id"]})
        children_data = result.mappings().all()
        children = [
            ChildResponse(
                id=child["id"],
                user_id=child["user_id"],
                name=child["name"],
                school_year_id=child["school_year_id"],
                memory=child["memory"],
                created_at=child["created_at"].isoformat(),
                updated_at=child["updated_at"].isoformat()
                if child["updated_at"]
                else None,
                school_year_name=child["school_year_name"],
            )
            for child in children_data
        ]

        return ChildrenListResponse(children=children)
    except Exception as e:
        logger.exception(
            "Error in get_children",
            error=str(e),
            error_type=type(e).__name__,
            user_id=current_user["id"],
        )
        # Re-raise as DatabaseError with the original exception details
        raise DatabaseError(
            f"Failed to retrieve children: {type(e).__name__}: {str(e)}",
            operation="get_children",
        )


@router.post("/", response_model=ChildResponse)
async def create_child(
    child_data: ChildCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new child"""
    query = text("""
        INSERT INTO children (user_id, name, school_year_id, memory)
        VALUES (:user_id, :name, :school_year_id, :memory)
        RETURNING id, user_id, name, school_year_id, memory, created_at, updated_at
    """)

    try:
        result = await db.execute(
            query,
            {
                "user_id": current_user["id"],
                "name": child_data.name,
                "school_year_id": child_data.school_year_id,
                "memory": json.dumps(child_data.memory),
            },
        )
        await db.commit()

        child_row = result.mappings().first()
        if not child_row:
            raise DatabaseError(
                "Failed to create child - no data returned", operation="create_child"
            )

        # Get school year name if available
        school_year_name = None
        if child_row["school_year_id"]:
            year_query = text("SELECT year_name FROM school_years WHERE id = :id")
            year_result = await db.execute(
                year_query, {"id": child_row["school_year_id"]}
            )
            year_row = year_result.mappings().first()
            if year_row:
                school_year_name = year_row["year_name"]

        return ChildResponse(
            id=child_row["id"],
            user_id=child_row["user_id"],
            name=child_row["name"],
            school_year_id=child_row["school_year_id"],
            memory=child_row["memory"],
            created_at=child_row["created_at"].isoformat(),
            updated_at=None,
            school_year_name=school_year_name,
        )

    except DatabaseError:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            "Database error in create_child",
            error=str(e),
            error_type=type(e).__name__,
            user_id=current_user["id"],
            child_name=child_data.name,
        )
        raise DatabaseError(
            f"Failed to create child: {str(e)}", operation="create_child"
        )


@router.put("/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: int,
    child_data: ChildUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update a child"""
    # First, verify the child exists and belongs to the current user
    check_query = text("""
        SELECT id FROM children 
        WHERE id = :child_id AND user_id = :user_id
    """)

    try:
        result = await db.execute(
            check_query, {"child_id": child_id, "user_id": current_user["id"]}
        )

        if not result.mappings().first():
            raise NotFoundError(
                "Child not found or access denied", resource_type="child"
            )

        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"child_id": child_id}

        if child_data.name is not None:
            update_fields.append("name = :name")
            params["name"] = child_data.name

        if child_data.school_year_id is not None:
            update_fields.append("school_year_id = :school_year_id")
            params["school_year_id"] = child_data.school_year_id

        if child_data.memory is not None:
            update_fields.append("memory = :memory")
            params["memory"] = json.dumps(child_data.memory)

        if not update_fields:
            raise ValidationError("No fields to update")

        # Always update the updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        update_query = text(f"""
            UPDATE children 
            SET {', '.join(update_fields)}
            WHERE id = :child_id
            RETURNING id, user_id, name, school_year_id, memory, created_at, updated_at
        """)

        result = await db.execute(update_query, params)
        await db.commit()

        child_row = result.mappings().first()
        if not child_row:
            raise DatabaseError(
                "Failed to update child - no data returned", operation="update_child"
            )

        # Get school year name if available
        school_year_name = None
        if child_row["school_year_id"]:
            year_query = text("SELECT year_name FROM school_years WHERE id = :id")
            year_result = await db.execute(
                year_query, {"id": child_row["school_year_id"]}
            )
            year_row = year_result.mappings().first()
            if year_row:
                school_year_name = year_row["year_name"]

        return ChildResponse(
            id=child_row["id"],
            user_id=child_row["user_id"],
            name=child_row["name"],
            school_year_id=child_row["school_year_id"],
            memory=child_row["memory"],
            created_at=child_row["created_at"].isoformat(),
            updated_at=child_row["updated_at"].isoformat(),
            school_year_name=school_year_name,
        )

    except (NotFoundError, ValidationError, DatabaseError):
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise DatabaseError(
            f"Failed to update child: {str(e)}", operation="update_child"
        )


@router.delete("/{child_id}")
async def delete_child(
    child_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a child"""
    # First, verify the child exists and belongs to the current user
    check_query = text("""
        SELECT id FROM children 
        WHERE id = :child_id AND user_id = :user_id
    """)

    try:
        result = await db.execute(
            check_query, {"child_id": child_id, "user_id": current_user["id"]}
        )

        if not result.mappings().first():
            raise NotFoundError(
                "Child not found or access denied", resource_type="child"
            )

        # Delete the child (cascading will handle related chat sessions)
        delete_query = text("DELETE FROM children WHERE id = :child_id")
        await db.execute(delete_query, {"child_id": child_id})
        await db.commit()

        return {"status": "success", "message": "Child deleted successfully"}

    except NotFoundError:
        raise
    except Exception as e:
        await db.rollback()
        raise DatabaseError(
            f"Failed to delete child: {str(e)}", operation="delete_child"
        )
