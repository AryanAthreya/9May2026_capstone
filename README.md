# Smart Expense Tracker API

A lightweight backend application to manage expenses.

## Features
- Add, View, Update, Delete expenses
- Upload expenses in bulk via CSV
- SQLite database for storing expenses
- MongoDB for logging API requests
- Dockerized setup
- Automated unit tests

## How to Run

### Using Docker Compose (Recommended)
1. Ensure you have Docker and Docker Compose installed.
2. Run the following command in the root directory:
   ```bash
   docker-compose up --build
   ```
3. The API will be available at `http://localhost:8000`.
4. Interactive API Documentation (Swagger) is at `http://localhost:8000/docs`.

### Running Locally (Without Docker)
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```
2. Make sure you have a local MongoDB instance running on port 27017 (or it will just skip logging if it fails).
3. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running Unit Tests
To run the automated tests, execute:
```bash
pytest tests/
```

## Testing APIs with Postman

Here are the methods and payloads to test using Postman (assuming running on `localhost:8000`).

### 1. Add Expense
- **Method**: `POST`
- **URL**: `http://localhost:8000/expenses/`
- **Headers**: `Content-Type: application/json`
- **Body** (raw -> JSON):
  ```json
  {
    "title": "Groceries",
    "amount": 45.50,
    "category": "Food",
    "date": "2023-10-15",
    "description": "Weekly grocery shopping"
  }
  ```

### 2. View All Expenses
- **Method**: `GET`
- **URL**: `http://localhost:8000/expenses/`

### 3. View Specific Expense
- **Method**: `GET`
- **URL**: `http://localhost:8000/expenses/{expense_id}` *(replace {expense_id} with the actual ID, e.g., 1)*

### 4. Update Expense
- **Method**: `PUT`
- **URL**: `http://localhost:8000/expenses/{expense_id}`
- **Headers**: `Content-Type: application/json`
- **Body** (raw -> JSON):
  ```json
  {
    "amount": 50.00
  }
  ```

### 5. Delete Expense
- **Method**: `DELETE`
- **URL**: `http://localhost:8000/expenses/{expense_id}`

### 6. Upload CSV Data
- **Method**: `POST`
- **URL**: `http://localhost:8000/expenses/upload/`
- **Body** (form-data):
  - **Key**: `file` (Change type from Text to **File**)
  - **Value**: Select your `.csv` file.
  
  *(Note: The CSV must have headers: `title`, `amount`, `category`, `date`, `description`)*
