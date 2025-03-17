# Yayska - Parent's Guide to School Success

Know more. Help better.

## What is Yayska?

### Summary

Yayska:

- Empowers parents to navigate the Irish educational curriculum by providing AI-driven insights and personalized guidance for their children's learning journey.
- Simplifies complex educational concepts into practical, actionable steps while focusing exclusively on the Irish education system.
- Creates joyful learning experiences through interactive assessments and celebration of achievements, making education more engaging for both parents and children.

### Yayska Backend

It's a FastAPI-based backend service that manages educational curriculum data, student progress tracking, and assessment generation. The system organizes educational content hierarchically from education levels down to individual concepts, with comprehensive metadata support for educational topics. Built with PostgreSQL for data persistence, it provides APIs to handle curriculum structure, learning outcomes, and concept-based assessments.

Currently (in early MVP) focused on mathematics education in primary school with Irish language integration. It will be expanded to include other subjects and languages in the near future.

### Why Yayska name?

So "Yayska" is a play on words combining:

- "Yay" - expressing joy and celebration of learning achievements
- The Irish word "éasca" (easy) - the app makes learning more accessible and manageable
- Ska - brings some Polish flair to the name, as the founder could even be Polish ¯\_(ツ)\_/¯

## Development Setup

### 1. Environment Setup

First, create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
# Install uv package manager (recommended)
pip install uv

# Install project dependencies
uv pip install --editable ".[dev]"
```

### 3. Configure Environment Variables

Copy existing `.env.example` as `.env` file into the project root and update with your own values where needed.

### 4. Database Setup

#### Start Local Database

```bash
# Start PostgreSQL container
docker compose up -d

# Verify container is running
docker compose ps
```

#### Database Management

```bash
# Stop and remove containers
docker compose down

# Stop and remove containers + delete volumes (clean slate)
docker compose down -v

# View database logs
docker compose logs -f db
```

#### Initialize Master Data

```bash
# Apply all migrations
alembic upgrade head

# Import initial curriculum data (subjects, concepts, concept_metadata)
python -m app.scripts.import_master_data
python -m app.scripts.import_concepts
python -m app.scripts.import_concept_metadata
```

#### Common Issues

- If port 5432 is already in use, modify the port mapping in `docker-compose.yml`
- Ensure Docker is running before executing compose commands
- For permission issues, try running commands with sudo (Linux/macOS)

## Database Migrations

### Migration Approach

```bash
alembic revision -m "raw_sql_changes"
```

Example raw SQL migration:

```python
def upgrade() -> None:
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
        -- Use for operations not supported by SQLAlchemy
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_email;")
```

### Managing Migrations

First, use `ENVIRONMENT` variable in `.env` file to specify the environment you want to work in:

- `local` - for local development
- `prod` - for production DB

For `prod` environment, you need to have all `POSTGRES_` variables set in `.env` file, which point to the production DB.

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1    # Revert last migration
alembic downgrade base  # Revert all migrations
```

## Start the server

```bash
uvicorn app.main:app --reload
```

## App configuration

To add new .env variables, add them also to the `Settings` class in `app/config.py`.

Then, read the config in your code:

```python
from app.config import settings

# Access settings
print(settings.ANTHROPIC_API_KEY)
```

## Deployment

Pushing to the `main` branch will deploy the latest changes to the production environment (in Vercel).

Remember to update requirements.txt file with the latest dependencies, as Vercel uses it to install dependencies:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

## Database Schema Structure

### Core Educational Structure

```
education_levels
     └── school_years
          └── concepts
               └── concept_metadata
```

### Curriculum Organization

```
curriculum_areas
     └── subjects (with introduction_year_id linking to school_years)
          └── concepts
```

### Monthly Curriculum Planning

The system uses an academic month numbering system where:

- Month 1 = September (start of school year)
- Month 2 = October
- ...
- Month 10 = June (end of school year)
- Month 0 = Summer (special mode for July/August)

Monthly curriculum plans associate concepts with specific months of the academic year and categorize them by importance (essential, important, supplementary).

### User Management

```
users
     └── events (user activity tracking)
```

### Key Relationships

- Concepts are linked to both subjects and school_years
- Subjects are associated with curriculum_areas and have an introduction year
- Each concept can have detailed metadata (concept_metadata)
- User actions are tracked through the events table

### Notable Changes from Previous Schema

- Removed strands, strand_units, and learning_outcomes tables
- Added events table for user activity tracking
- Concepts now link directly to subjects and school years
- Added comprehensive user management structure

## Concept Metadata

The concept metadata helps parents understand educational topics by covering:

1. **Importance & Application**

   - Why this matters in real life
   - How it helps with future learning

2. **Difficulty Level**

   - How many children typically find it challenging (out of 10)
   - Common stumbling blocks
   - Reassuring guidance for parents

3. **Parent's Quick Guide**

   - Key points to understand
   - Common misunderstandings to watch for
   - Practical teaching tips

4. **Real-World Connection**

   - Everyday examples
   - Practice ideas at home

5. **Learning Journey**

   - What needs to be learned first
   - Signs that show understanding

6. **Time Investment**

   - How long it typically takes to learn
   - Recommended practice schedule
   - Guidance for different learning speeds

7. **Assessment Options**

   - Best ways to check understanding
   - Types of practice questions that work well

8. **Irish Language Support**
   - Key educational terms in Irish
   - Common educational phrases
   - Help with pronunciation

## TODO

- [ ] Generate assessments for concepts
- [ ] Create DB structure for events
