import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.deps import CurrentUser

router = APIRouter()


@router.get("/monthly-curriculum")
async def get_monthly_curriculum(
    current_user: CurrentUser,
    year_ids: str = Query(..., description="Comma-separated list of school year IDs"),
    reference_month: Optional[int] = Query(
        None,
        description="Academic month number where 1=September, 2=October, ..., 10=June. Use 0 for summer months (July/August). Defaults to current corresponding academic month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get monthly curriculum plans and concepts for specified school years.

    Returns previous, current, and next month's curriculum plans with
    detailed concept information for each month, enriched with user interaction data.

    Args:
        current_user: Current authenticated user
        year_ids: Comma-separated list of school year IDs
        reference_month: Academic month number where 1=September, 2=October, ..., 10=June. Use 0 for summer months (July/August). Defaults to current corresponding academic month.
        db: Database session dependency

    Returns:
        Dictionary containing curriculum plans grouped by school year and month
    """
    # Parse year_ids from comma-separated string to list of integers
    try:
        year_id_list = [int(year_id.strip()) for year_id in year_ids.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid year_ids format. Please provide comma-separated integers.",
        )

    # Determine reference month if not provided
    if reference_month is None:
        # Get current calendar month and convert to academic month
        calendar_month = datetime.datetime.now().month
        # Academic calendar: Sept(1) to June(10)
        # Calendar months: Sept(9) to June(6), missing July(7) and August(8)
        if calendar_month >= 9:  # Sept-Dec
            reference_month = calendar_month - 8  # Sept(9) -> 1, Oct(10) -> 2, etc.
        elif calendar_month <= 6:  # Jan-June
            reference_month = calendar_month + 4  # Jan(1) -> 5, Feb(2) -> 6, etc.
        else:
            # For summer months (July, August), we'll use a special mode
            # that shows June (month 10), September (month 1), and a summer review
            reference_month = 0  # Special summer mode
    elif not (0 <= reference_month <= 10):
        raise HTTPException(
            status_code=400,
            detail="reference_month must be between 0 (Summer) and 10 (June), where 1 is September",
        )

    # Calculate relevant months based on reference month
    if reference_month == 0:  # Summer mode
        # For summer, show June, a "summer review", and September
        months_to_fetch = [1, 10]  # September (1) and June (10)
        previous_month = 10  # June
        next_month = 1  # September
        current_month = 0  # Special summer mode
    else:
        # Normal academic year mode
        previous_month = 10 if reference_month == 1 else reference_month - 1
        next_month = 1 if reference_month == 10 else reference_month + 1
        current_month = reference_month
        months_to_fetch = [previous_month, current_month, next_month]

    # 1. Get monthly curriculum plans for the specified years and months
    curriculum_plans_query = text("""
        SELECT 
            mcp.year_id,
            sy.year_name,
            mcp.month_order,
            mcp.month_name,
            mcp.focus_statement,
            mcp.essential_concept_ids,
            mcp.important_concept_ids,
            mcp.supplementary_concept_ids,
            CASE 
                WHEN :current_month = 0 THEN 
                    CASE
                        WHEN mcp.month_order = 10 THEN 'previous'  -- June
                        WHEN mcp.month_order = 1 THEN 'next'       -- September
                    END
                ELSE
                    CASE
                        WHEN mcp.month_order = :current_month THEN 'current'
                        WHEN mcp.month_order = :previous_month THEN 'previous'
                        WHEN mcp.month_order = :next_month THEN 'next'
                    END
            END AS month_type
        FROM monthly_curriculum_plans mcp
        JOIN school_years sy ON mcp.year_id = sy.id
        WHERE mcp.year_id = ANY(:year_ids)
        AND mcp.month_order = ANY(:months_to_fetch)
        ORDER BY mcp.year_id, mcp.month_order
    """)

    result = await db.execute(
        curriculum_plans_query,
        {
            "year_ids": year_id_list,
            "current_month": current_month,
            "previous_month": previous_month,
            "next_month": next_month,
            "months_to_fetch": months_to_fetch,
        },
    )
    curriculum_plans = result.mappings().all()

    if not curriculum_plans:
        return {"curriculum_plans": []}

    # 2. Extract all concept IDs from the plans
    all_concept_ids = set()
    for plan in curriculum_plans:
        all_concept_ids.update(plan["essential_concept_ids"] or [])
        all_concept_ids.update(plan["important_concept_ids"] or [])
        all_concept_ids.update(plan["supplementary_concept_ids"] or [])

    # 3. Fetch concept details and user interactions in parallel
    concept_details = {}
    user_interactions_data = {}

    if all_concept_ids:
        concept_ids_list = list(all_concept_ids)

        # Fetch concept details
        concepts_query = text("""
            SELECT 
                c.id,
                c.concept_name,
                c.concept_description,
                c.subject_id,
                s.subject_name
            FROM concepts c
            JOIN subjects s ON c.subject_id = s.id
            WHERE c.id = ANY(:concept_ids)
        """)

        # Fetch user interactions
        interactions_query = text("""
            SELECT 
                (interaction_context->'concept_id')::text::integer as concept_id,
                interaction_type
            FROM user_interactions
            WHERE user_id = :user_id
            AND interaction_context->>'concept_id' IS NOT NULL
            AND (interaction_context->'concept_id')::text::integer = ANY(:concept_ids)
            AND interaction_type IN ('CONCEPT_STUDIED', 'AI_CHAT_ENGAGED')
        """)

        # Execute both queries
        concepts_result = await db.execute(
            concepts_query, {"concept_ids": concept_ids_list}
        )
        interactions_result = await db.execute(
            interactions_query,
            {"user_id": current_user["id"], "concept_ids": concept_ids_list},
        )

        # Process concept details
        concept_details = {
            row.id: dict(row) for row in concepts_result.mappings().all()
        }

        # Process user interactions
        interactions = interactions_result.mappings().all()
        for interaction in interactions:
            concept_id = interaction["concept_id"]
            interaction_type = interaction["interaction_type"]

            if concept_id not in user_interactions_data:
                user_interactions_data[concept_id] = {
                    "previously_studied": False,
                    "previously_discussed": False,
                }

            if interaction_type == "CONCEPT_STUDIED":
                user_interactions_data[concept_id]["previously_studied"] = True
            elif interaction_type == "AI_CHAT_ENGAGED":
                user_interactions_data[concept_id]["previously_discussed"] = True

    # 4. Enrich concept details with user interaction data
    enriched_concept_details = {}
    for concept_id, concept_data in concept_details.items():
        interaction_data = user_interactions_data.get(
            concept_id,
            {"previously_studied": False, "previously_discussed": False},
        )
        enriched_concept_details[concept_id] = {**concept_data, **interaction_data}

    # 5. Structure the response
    response = {"curriculum_plans": [], "is_summer_mode": reference_month == 0}
    current_year = None
    current_year_data = None

    for plan in curriculum_plans:
        year_id = plan["year_id"]

        # If we've moved to a new year, create a new year entry
        if current_year != year_id:
            current_year = year_id
            current_year_data = {
                "year_id": year_id,
                "year_name": plan["year_name"],
                "months": {},
            }
            response["curriculum_plans"].append(current_year_data)

        month_type = plan["month_type"]

        # Process concepts for this month
        essential_concepts = [
            enriched_concept_details[concept_id]
            for concept_id in (plan["essential_concept_ids"] or [])
            if concept_id in enriched_concept_details
        ]

        important_concepts = [
            enriched_concept_details[concept_id]
            for concept_id in (plan["important_concept_ids"] or [])
            if concept_id in enriched_concept_details
        ]

        supplementary_concepts = [
            enriched_concept_details[concept_id]
            for concept_id in (plan["supplementary_concept_ids"] or [])
            if concept_id in enriched_concept_details
        ]

        # Add month data to the response
        current_year_data["months"][month_type] = {
            "month_order": plan["month_order"],
            "month_name": plan["month_name"],
            "focus_statement": plan["focus_statement"],
            "essential_concepts": essential_concepts,
            "important_concepts": important_concepts,
            "supplementary_concepts": supplementary_concepts,
        }

    # Handle summer mode special case
    if reference_month == 0:
        # For each year's data, create a summer review section
        for year_data in response["curriculum_plans"]:
            # Only create summer review if we have at least one month
            if year_data["months"]:
                # Create a summer review with selected concepts from June
                june_concepts = []
                if "previous" in year_data["months"]:  # June data
                    june_data = year_data["months"]["previous"]
                    # Get some essential concepts from June (up to 3)
                    june_concepts.extend(june_data["essential_concepts"][:3])

                # Add the summer review section
                year_data["months"]["current"] = {
                    "month_order": 0,
                    "month_name": "Summer Review",
                    "focus_statement": "Summer Review: Practice key concepts from the past year and preview upcoming topics.",
                    "essential_concepts": june_concepts,
                    "important_concepts": [],
                    "supplementary_concepts": [],
                }

    return response


@router.get("/{concept_id}/metadata")
async def get_concept_metadata(
    concept_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get detailed metadata for a specific concept.

    Args:
        concept_id: The ID of the concept
        db: Database session dependency

    Returns:
        Dictionary containing all metadata fields for the concept

    Raises:
        HTTPException: If concept is not found
    """
    query = text("""
        SELECT 
            c.id as concept_id,
            c.concept_name,
            c.concept_description,
            cm.why_important,
            cm.difficulty_stats,
            cm.parent_guide,
            cm.real_world,
            cm.learning_path,
            cm.time_guide,
            cm.assessment_approaches,
            cm.irish_language_support
        FROM concepts c
        LEFT JOIN concept_metadata cm ON c.id = cm.concept_id
        WHERE c.id = :concept_id
    """)

    result = await db.execute(query, {"concept_id": concept_id})
    metadata = result.mappings().first()

    if not metadata:
        raise HTTPException(
            status_code=404, detail=f"Concept with id {concept_id} not found"
        )

    return dict(metadata)
