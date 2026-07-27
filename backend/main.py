from fastapi import FastAPI
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.auth_routes import router as auth_router

# Create avatar_url column in users table if it doesn't exist
# try:
    # with engine.connect() as conn:
#     #     conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)"))
#     #     conn.commit()
# except Exception as e:
#     print(f"Migration error: {e}")

app = FastAPI()
app.include_router(auth_router)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)


from backend.routes.profile_routes import router as profile_router
app.include_router(profile_router)

from backend.routes.auth_routes import (
    get_current_user,
    oauth2_scheme
)

from backend.routes.issue_routes import (
    router as issue_router
)
app.include_router(issue_router)

from backend.routes.comment_routes import (
    router as comment_router
)
app.include_router(comment_router)


from backend.routes.claim_routes import (
    router as claim_router
)
app.include_router(claim_router)

from backend.routes.verification_routes import (
    router as verification_router
)
app.include_router(verification_router)

from backend.routes.report_routes import (
    router as report_router
)
app.include_router(report_router)

from backend.routes.admin_routes import router as admin_router
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():

    with engine.connect() as connection:

        result = connection.execute(text("SELECT * FROM users"))

        users = []

        for row in result.mappings():
            users.append({
                "id": row["id"],
                "name": row["name"],
                "email": row["email"]
            })

        return users



@app.get("/add-complaint")
def add_complaint():

    with engine.connect() as connection:
            
        connection.execute(
            text("""
                    INSERT INTO complaints (title, description,user_id)
                    VALUES('Water issue','No water in area','1')
                """
            )
        )

        connection.commit()

        return {"message": "added complaint successfully"}
    

@app.get("/get_complaints")
def show_complaints():

    with engine.connect() as connection:

        result = connection.execute(text("SELECT * FROM complaints"))

        complaints = []

        for row in result.mappings():
            complaints.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "user_id": row["user_id"]
            })

        return complaints
        

@app.get("/get-complaints-with-users")
def complaints_with_users():

    with engine.connect() as connection:
    
        result = connection.execute(
            text("""
                    SELECT complaints.title, users.name AS user_name
                    FROM complaints
                    JOIN users
                    ON complaints.user_id = users.id
                """
                )
        )

        complaints = []

        for row in result.mappings():

            complaints.append({
                    "title": row["title"],
                    "user_name": row["user_name"]
                })

        return complaints
        
class VoteCreate(BaseModel):
    issue_id: int

@app.post("/vote")
def vote_issue(
        vote: VoteCreate,
        token: str = Depends(oauth2_scheme)
):
    
    user = get_current_user(token)

    with engine.connect() as connection:

        existing_vote = connection.execute(
            text("""
                SELECT * FROM votes
                WHERE issue_id = :issue_id
                AND user_id = :user_id
            """),
            {
                "issue_id": vote.issue_id,
                "user_id": user["user_id"]
            }
        )

        vote_found = existing_vote.mappings().first()

        if vote_found:
            return {"message": "Already voted"}
        
        connection.execute(
            text("""
                UPDATE issues
                SET upvotes = upvotes + 1
                WHERE id = :issue_id
            """),
            {
                "issue_id": vote.issue_id
            }
        )

        connection.execute(
                text("""
                    INSERT INTO votes
                    (issue_id, user_id)

                    VALUES
                    (:issue_id, :user_id)
                    """),
                {
                    "issue_id": vote.issue_id,
                    "user_id": user["user_id"]
                }
        )

        connection.commit()

        return{
            "message": "Vote added successfully"
        }
