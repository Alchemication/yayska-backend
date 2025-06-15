# app/scripts/dev_token.py
from app.services.auth import create_access_token

# Assuming you have a test user with id=1
token = create_access_token(1)
print(f"Authorization: Bearer {token}")
