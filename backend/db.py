from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:?harekrishna?@localhost:5432/political_app_db"

engine = create_engine(DATABASE_URL)

print("Database connected successfully")