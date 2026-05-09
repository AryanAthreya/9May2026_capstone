import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from main import app, Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_expense():
    response = client.post(
        "/expenses/",
        json={"title": "Lunch", "amount": 15.5, "category": "Food", "date": "2023-10-01", "description": "Burger"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Lunch"
    assert data["amount"] == 15.5
    assert "id" in data

def test_read_expenses():
    client.post("/expenses/", json={"title": "Taxi", "amount": 20.0, "category": "Transport", "date": "2023-10-02"})
    response = client.get("/expenses/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Taxi"

def test_read_expense():
    create_response = client.post("/expenses/", json={"title": "Bus", "amount": 2.0, "category": "Transport", "date": "2023-10-03"})
    expense_id = create_response.json()["id"]
    
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Bus"

def test_update_expense():
    create_response = client.post("/expenses/", json={"title": "Bus", "amount": 2.0, "category": "Transport", "date": "2023-10-03"})
    expense_id = create_response.json()["id"]
    
    response = client.put(f"/expenses/{expense_id}", json={"amount": 2.5})
    assert response.status_code == 200
    assert response.json()["amount"] == 2.5

def test_delete_expense():
    create_response = client.post("/expenses/", json={"title": "Bus", "amount": 2.0, "category": "Transport", "date": "2023-10-03"})
    expense_id = create_response.json()["id"]
    
    response = client.delete(f"/expenses/{expense_id}")
    assert response.status_code == 204
    
    get_response = client.get(f"/expenses/{expense_id}")
    assert get_response.status_code == 404

def test_upload_csv():
    csv_content = "title,amount,category,date,description\nDinner,40.0,Food,2023-10-05,Pizza\nMovie,15.0,Entertainment,2023-10-06,Cinema"
    file = BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/expenses/upload/",
        files={"file": ("test.csv", file, "text/csv")}
    )
    assert response.status_code == 200
    assert "Successfully processed 2 expenses" in response.json()["message"]
    
    get_response = client.get("/expenses/")
    data = get_response.json()
    assert len(data) == 2
