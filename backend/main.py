from fastapi import FastAPI
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30



pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated = "auto"
)


def create_access_token(data:dict):

    to_encode = data.copy() 

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm= ALGORITHM
    )

    return encoded_jwt

def get_current_user(
    token: str = Depends(oauth2_scheme)
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        email = payload.get("email")

        if user_id is None:
            raise Exception("Invalid token")

        return {
            "user_id": user_id,
            "email": email
        }

    except JWTError:

        return {
            "message": "Token is invalid or expired"
        }


class UserCreate(BaseModel):
    name: str
    email: str
    password : str

class LoginData(BaseModel):
    email: str
    password: str



@app.get("/profile")
def profile(token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)

    return{
        "current_user" : user
    }


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


@app.post("/login")
def login(data: OAuth2PasswordRequestForm = Depends()):
        
        with engine.connect() as connection:
            
            result = connection.execute(
                text("SELECT * FROM users WHERE email = :email "),
                {
                    "email": data.username
                }
            )

            user = result.mappings().first()

            if user is None:
                return {"message": "User not found"}
            
            if not pwd_context.verify(data.password, user["password"]):
                return {"message": "Invalid password"}
            



            token = create_access_token(
                {
                    "user_id" :  user["id"],
                    "email" : user["email"]
                }
            )

            return {
                "message" : "Login succeessful",
                "access_token" : token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"]
                }
            }


@app.post("/register")
def add_user(user: UserCreate):

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {
                "email": user.email
            }
        )

        existing_user = result.mappings().first()

        if existing_user:
            return {"message": "Email already registered"}

        hashed_password = pwd_context.hash(user.password)

        connection.execute(
            text("""
                INSERT INTO users (name, email, password)
                VALUES (:name, :email, :password)
            """),
            {
                "name": user.name,
                "email": user.email,
                "password": hashed_password
            }
        )

        connection.commit()


        result = connection.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {
                "email": user.email
            }
        )

        new_user = result.mappings().first()


        token = create_access_token(
            {
                "user_id": new_user["id"],
                "email": new_user["email"]
            }
        )

    return {
        "message": "User registered successfully",
        "access_token": token,
        "user": {
            "id": new_user["id"],
            "name": new_user["name"],
            "email": new_user["email"]
        }
    }    


class IssueCreate(BaseModel):
    title: str 
    description: str 
    category: str 
    location: str 


@app.post("/issues")
def create_issue(
    issue: IssueCreate,
    user = Depends(get_current_user)
):

    print(user)

    with engine.connect() as connection:
    
        connection.execute(
            text("""
                    INSERT INTO issues
                    (title, description, category, location, created_by)

                    VALUES
                    (:title, :description, :category, :location, :created_by)
                """),

                {
                    "title": issue.title,
                    "description": issue.description,
                    "category": issue.category,
                    "location": issue.location,
                    "created_by": user["user_id"]
                }
        )

        connection.commit()

        return {
            "message": "Issue create successfully"
        }


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
    

@app.get("/issues")
def get_issues(sort: str = "newest"):

    if sort == "trending":

        query = """
            SELECT * FROM issues
            ORDER BY upvotes DESC
        """

    elif sort == "oldest":

        query = """
            SELECT * FROM issues
            ORDER BY created_at ASC
        """

    else:

        query = """
            SELECT * FROM issues
            ORDER BY created_at DESC
        """

    with engine.connect() as connection:

        result = connection.execute(
            text(query)
        )

        issues = []

        for row in result.mappings():

            issues.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "location": row["location"],
                "status": row["status"],
                "upvotes": row["upvotes"],
                "created_by": row["created_by"],
                "created_at": str(row["created_at"])
            })

        return issues

@app.get("/issues/{issue_id}")
def get_single_issue(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT * FROM issues
                WHERE id = :id
            """),
            {
                "id": issue_id
            }
        )

        issue = result.mappings().first()

        if issue is None:
            return {"message": "Issue not found"}

        return {
            "id": issue["id"],
            "title": issue["title"],
            "description": issue["description"],
            "category": issue["category"],
            "location": issue["location"],
            "status": issue["status"],    
            "upvotes": issue["upvotes"],
            "created_by": issue["created_by"],
            "created_at": str(issue["created_at"])
        }
    
    
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

class CommentCreate(BaseModel):
    issue_id: int
    comment: str

@app.post("/comments")
def add_comment(
    data: CommentCreate,
    token: str = Depends(oauth2_scheme)
):

    user = get_current_user(token)

    with engine.connect() as connection:

        connection.execute(
            text("""
                INSERT INTO comments
                (issue_id, user_id, comment)

                VALUES
                (:issue_id, :user_id, :comment)
            """),
            {
                "issue_id": data.issue_id,
                "user_id": user["user_id"],
                "comment": data.comment
            }
        )

        connection.commit()

        return {
            "message": "Comment added"
        }
    
@app.get("/comments/{issue_id}")
def get_comments(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""

                SELECT
                    comments.id,
                    comments.comment,
                    comments.user_id,
                    comments.created_at,
                    users.name

                FROM comments

                JOIN users
                ON comments.user_id = users.id

                WHERE comments.issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        )

        comments = []

        for row in result.mappings():

            comments.append({
                "id": row["id"],
                "comment": row["comment"],
                "name": row["name"],
                "created_at": str(row["created_at"])
            })

        return comments