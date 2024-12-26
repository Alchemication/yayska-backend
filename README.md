# Yayska Backend

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

Create a `.env` file in the project root:

```bash
# Database Configuration
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres  # Change in production
POSTGRES_DB=yayska
POSTGRES_PORT=5432
```

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

# Import master data (subjects, schools, etc.)
python -m app.scripts.import_master_data;

# Import learning outcomes
python -m app.scripts.import_learning_outcomes;
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

## Database Schema Structure

### Educational Progress Path
```
education_levels
     └── school_years
          └── learning_outcomes
               └── concepts
                    └── (quizzes & concept_metadata)
```

### Curriculum Structure Path
```
curriculum_areas
     └── subjects
          └── strands
               └── strand_units
                    └── learning_outcomes
```

## TODO

- [ ] Add irish translations for all content