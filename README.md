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

Focused on education in primary school with Irish language integration.

### Why Yayska name?

So "Yayska" is a play on words combining:

- "Yay" - expressing joy and celebration of learning achievements
- The Irish word "éasca" (easy) - the app makes learning more accessible and manageable
- Ska - brings some Polish flair to the name, as the founder could even be Polish ¯\_(ツ)\_/¯

## Development Setup

### 1. Install Dependencies

```bash
# Install uv package manager (recommended)
pip install uv

# Install project dependencies including dev extras
uv sync --extra dev
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with the following required variables:

```bash
# App Settings
ENVIRONMENT=local
SECRET_KEY=your-secret-key-here

# Database Settings
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=yayska
POSTGRES_PORT=5432

# OAuth Settings - Google
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8081/auth/google/callback

# AI Services (Required for chat functionality)
ANTHROPIC_API_KEY=your-anthropic-api-key
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Optional: AI Chat Rate Limiting
AI_REQUESTS_PER_DAY_LIMIT=50
AI_REQUEST_WHITELIST=["your-email@example.com"]

# Optional: Database Query Logging
DB_ECHO_QUERIES=false
```

**Note**: You'll need to obtain API keys from Google Cloud Console, Anthropic, and Google AI Studio for full functionality.

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
uv run alembic upgrade head

# Import initial curriculum data (subjects, concepts, concept_metadata)
uv run python -m app.scripts.import_master_data
uv run python -m app.scripts.import_concepts
uv run python -m app.scripts.import_concept_metadata
```

#### Common Issues

- If port 5432 is already in use, modify the port mapping in `docker-compose.yml`
- Ensure Docker is running before executing compose commands
- For permission issues, try running commands with sudo (Linux/macOS)

## Database Migrations

### Migration Approach

```bash
uv run alembic revision -m "raw_sql_changes"
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
uv run alembic upgrade head

# Rollback migrations
uv run alembic downgrade -1    # Revert last migration
uv run alembic downgrade base  # Revert all migrations
```

## Testing

This project uses `pytest` for unit testing. The tests are located in the `tests/` directory, mirroring the structure of the `app/` directory.

### Running Tests

To run all tests, execute the following command from the project root:

```bash
uv run pytest
```

To run tests for a specific file or directory, provide the path:

```bash
# Run all tests in the utils directory
uv run pytest tests/utils/

# Run a specific test file
uv run pytest tests/utils/test_llm.py
```

### Test Configuration

Some tests, particularly those interacting with external services like LLMs, require API keys. These should be defined in a `.env` file in the project root. The tests are designed to skip themselves gracefully if the required environment variables are not found.

Currently, the tests for `app/utils/llm.py` require:

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

## Start the server

```bash
uv run uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000` by default.

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

## API Documentation

### Swagger UI

Once the server is running, you can access the interactive API documentation at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

The API documentation is automatically generated from the FastAPI application and includes all available endpoints, request/response schemas, and the ability to test endpoints directly from the browser.

### Authentication

The API uses **OAuth 2.0 with Google** for authentication. Most endpoints require a valid JWT token in the Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

#### Getting Started with Authentication

1. **Frontend Integration**: The frontend handles OAuth flow with Google
2. **Token Exchange**: Use `/api/v1/auth/oauth/callback` endpoint to exchange authorization code for tokens
3. **Token Refresh**: Use `/api/v1/auth/refresh` endpoint to refresh expired tokens
4. **Current User**: Use `/api/v1/auth/me` endpoint to get current user information

#### Public Endpoints (No Authentication Required)

- `GET /api/v1/health` - Health check
- `POST /api/v1/auth/oauth/callback` - OAuth callback
- `POST /api/v1/auth/google/callback` - Google OAuth callback (legacy)
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /docs` - API documentation
- `GET /redoc` - Alternative API documentation

## API Overview

### Core Features

The Yayska backend provides the following main features:

#### 🔐 Authentication System

- **OAuth 2.0** with Google (extensible to other providers)
- **JWT-based** authentication with access and refresh tokens
- **Token blacklisting** for secure logout
- **Multi-session** management

#### 🤖 AI-Powered Chat

- **Interactive conversations** with AI tutors about educational concepts
- **Context-aware responses** based on curriculum data
- **Streaming responses** for real-time chat experience
- **Message feedback** system for continuous improvement
- **Rate limiting** (50 requests per day per user, configurable)

#### 📚 Educational Content Management

- **Curriculum structure** (education levels, school years, subjects, concepts)
- **Concept metadata** with detailed guidance for parents
- **Monthly curriculum planning** with academic calendar support
- **Learning path recommendations**

#### 📊 User Interaction Tracking

- **Event logging** for user activities
- **Progress tracking** and analytics
- **User interaction history**

### API Endpoints Overview

| Endpoint Category     | Description              | Key Endpoints                                                     |
| --------------------- | ------------------------ | ----------------------------------------------------------------- |
| **Health**            | System health monitoring | `GET /health`                                                     |
| **Auth**              | User authentication      | `POST /auth/oauth/callback`, `GET /auth/me`                       |
| **Chats**             | AI-powered conversations | `POST /chats/find-or-create`, `POST /chats/{id}/messages`         |
| **Concepts**          | Educational concepts     | `GET /concepts/monthly-curriculum`, `GET /concepts/{id}/metadata` |
| **Curriculum**        | Curriculum management    | `GET /curriculum/subjects/{year_id}/learning-paths`               |
| **Education**         | Education levels         | `GET /education/education-levels`                                 |
| **Events**            | User activity tracking   | `POST /events`                                                    |
| **User Interactions** | User interaction logging | `POST /user-interactions`                                         |

### Rate Limiting

The API implements rate limiting for AI chat requests:

- **Default limit**: 50 AI requests per day per user
- **Whitelist support**: Specific email addresses can be exempted from rate limiting
- **Configurable**: Set via `AI_REQUESTS_PER_DAY_LIMIT` environment variable
- **Daily reset**: Counters reset at midnight

### AI Chat Features

The chat system provides:

- **Context-aware conversations** about educational concepts
- **Multiple AI models** supported (Claude, Gemini)
- **Streaming responses** for real-time interaction
- **Session management** with conversation history
- **Feedback system** for message quality
- **Educational prompts** tailored to Irish curriculum

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

## License

MIT License

Copyright (c) 2025 Yayska

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact

For questions or support, please [create an issue](https://github.com/alchemication/yayska-backend/issues).

---

Built with ❤️ for parents in Ireland
