import os
import csv
from io import StringIO
from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel, Field
from pymongo import MongoClient

# ==========================================
# 1. Database Setup (SQLite & MongoDB)
# ==========================================
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# MongoDB for logging
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "expense_tracker")
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_db = mongo_client[MONGO_DB_NAME]
    logs_collection = mongo_db["logs"]
except Exception as e:
    logs_collection = None
    print(f"Failed to connect to MongoDB: {e}")

def log_request_data(method: str, url: str, status_code: int):
    if logs_collection is not None:
        try:
            log_entry = {
                "method": method,
                "url": url,
                "status_code": status_code,
                "timestamp": datetime.utcnow()
            }
            logs_collection.insert_one(log_entry)
        except Exception as e:
            print(f"Error logging to MongoDB: {e}")

# ==========================================
# 2. SQLAlchemy Models
# ==========================================
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, index=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=True)

# Create the SQLite tables
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. Pydantic Schemas
# ==========================================
class ExpenseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=50)
    date: date
    description: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None

class ExpenseResponse(ExpenseBase):
    id: int
    
    class Config:
        from_attributes = True

# ==========================================
# 4. FastAPI Setup & Routes
# ==========================================
app = FastAPI(title="Smart Expense Tracker API", description="API to manage expenses and log requests.")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log_request_data(request.method, str(request.url), response.status_code)
    return response

@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to the Smart Expense Tracker API! Visit /docs for the interactive API documentation."}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/expenses/", response_model=ExpenseResponse, status_code=201)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    """Add a new expense."""
    db_expense = Expense(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/expenses/", response_model=List[ExpenseResponse])
def read_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """View all expenses."""
    return db.query(Expense).offset(skip).limit(limit).all()

@app.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def read_expense(expense_id: int, db: Session = Depends(get_db)):
    """View a specific expense by ID."""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return db_expense

@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, expense_update: ExpenseUpdate, db: Session = Depends(get_db)):
    """Update an existing expense."""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    update_data = expense_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_expense, key, value)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete an expense."""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(db_expense)
    db.commit()
    return None

@app.post("/expenses/upload/")
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload expenses via a CSV file. Expected columns: title, amount, category, date, description."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    try:
        contents = file.file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(StringIO(decoded))
        
        inserted_count = 0
        for row in csv_reader:
            try:
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                expense_data = ExpenseCreate(
                    title=row['title'],
                    amount=float(row['amount']),
                    category=row['category'],
                    date=date_obj,
                    description=row.get('description', '')
                )
                db_expense = Expense(**expense_data.model_dump())
                db.add(db_expense)
                db.commit()
                inserted_count += 1
            except Exception as e:
                print(f"Error processing row {row}: {e}")
                continue
                
        return {"message": f"Successfully processed {inserted_count} expenses from CSV"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()
