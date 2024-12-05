import json
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine,text
import uuid
from models import Contact

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your_secret_key" 
ALGORITHM = "HS256"

DATABASE_URL = "mysql+pymysql://root:mysql@localhost:3306/asterforms"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Creates a JWT token with a default expiration of 2 weeks.

    :param data: A dictionary containing user data to encode in the token.
    :param expires_delta: Optional timedelta to set token expiry.
    :return: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(weeks=2))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str):
    """
    Verifies the JWT token.

    :param token: JWT token to verify.
    :return: Dictionary with "status" as valid, expired, or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"status": "valid", "data": payload}
    except jwt.ExpiredSignatureError:
        return {"status": "expired"}
    except JWTError:
        return {"status": "invalid"}

def get_db():
    """
    Dependency to create and close database sessions for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_form_json(form_id: str, db: Session):
    """
    Check the status of a form in the database based on given criteria.

    :param form_id: The ID of the form to check.
    :param db: SQLAlchemy database session.
    :return: Dictionary with form data or failure stage.
    """

    try:
        query = text("""
            SELECT id, form_json, settings, scheduled, active, start, end
            FROM forms
            WHERE id = :form_id
        """)
        form = db.execute(query, {"form_id": form_id}).fetchone()

        if not form:
            return {"status": "id_not_found"}
        
        if not form["active"]:
            return {"status": "not_active"}

        if not form["scheduled"]:
            return {"status": "not_scheduled"}

        current_time = datetime.utcnow()
        if not (form["start"] and form["end"] and form["start"] <= current_time <= form["end"]):
            return {"status": "out_of_schedule"}

        return {
            "status": "success",
            "form_json": form["form_json"],
            "settings": form["settings"]
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}


def add_form(
    form_json: dict,
    settings: dict,
    active: bool,
    scheduled: bool,
    start: Optional[datetime],
    end: Optional[datetime],
    db: Session,
):
    """
    Adds a new form to the database with parameters passed directly.

    :param form_json: JSON data of the form.
    :param settings: Settings of the form.
    :param active: Whether the form is active.
    :param scheduled: Whether the form is scheduled.
    :param start: Start datetime of the schedule.
    :param end: End datetime of the schedule.
    :param db: SQLAlchemy database session.
    :return: Dictionary with success message and generated form ID.
    """
    try:

        form_id = str(uuid.uuid4())
        
        
        while db.execute(
            text("SELECT COUNT(*) FROM forms WHERE id = :form_id"),
            {"form_id": form_id}
        ).fetchone()[0] > 0:
            form_id = str(uuid.uuid4())

        form_json_str = json.dumps(form_json)  
        settings_str = json.dumps(settings)   

        query = text("""
            INSERT INTO forms (id, form_json, settings, active, scheduled, start, end)
            VALUES (:id, :form_json, :settings, :active, :scheduled, :start, :end)
        """)

        db.execute(query, {
            "id": form_id,
            "form_json": form_json_str,
            "settings": settings_str,
            "active": active,
            "scheduled": scheduled,
            "start": start,
            "end": end,
        })
        db.commit()

        return {"message": "Form created successfully.", "form_id": form_id}

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        return {"message": "Failed to create form.", "form_id": ""}

def add_template(
    form_json: dict,
    by_name: str,
    by_id: str,
    categories: List,
    title: str,
    description: str,
    db: Session
):
    """
    Inserts a new template into the 'templates' table.

    :param form_json: JSON data for the form.
    :param by_name: Name of the publisher.
    :param by_id: ID of the publisher.
    :param categories: List of categories.
    :param title: Title of the template.
    :param description: Description of the template.
    :param db: SQLAlchemy database session.
    :return: Dictionary with success message and generated template ID.
    """
    try:
        template_id = str(uuid.uuid4())
        
        while db.execute(
            text("SELECT COUNT(*) FROM templates WHERE id = :template_id"),
            {"template_id": template_id}
        ).fetchone()[0] > 0:
            template_id = str(uuid.uuid4())

        query = text("""
            INSERT INTO templates (
                id, publisher_name, publisher_id, title, description, categories, form_json
            ) VALUES (
                :id, :publisher_name, :publisher_id, :title, :description, :categories, :form_json
            )
        """)

        db.execute(query, {
            "id": template_id,
            "publisher_name": by_name,
            "publisher_id": by_id,
            "title": title,
            "description": description,
            "categories": json.dumps(categories),
            "form_json": json.dumps(form_json) 
        })

        db.commit()

        return {"message": "Template added successfully."}

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        return {"message": "Failed to add template."}
    

def get_templates_data(query: str, categories: Optional[List[str]], db: Session):
    """
    Fetch templates from the database based on the search query and optional categories.

    :param query: Search query for title or description.
    :param categories: List of categories to filter templates (optional).
    :param db: Database session.
    :return: List of templates matching the criteria.
    """
    try:
        sql_query = """
            SELECT id, publisher_name, publisher_id, title, description, form_json, categories
            FROM templates
            WHERE (title LIKE :query OR description LIKE :query)
        """
        query_params = {"query": f"%{query}%"}
        if categories:
            sql_query += " AND JSON_CONTAINS(categories, :categories)"
            query_params["categories"] = json.dumps(categories)
            
        result = db.execute(text(sql_query), query_params).fetchall()
        
        templates = [
            {
                "id": row.id,
                "publisher_name": row.publisher_name,
                "publisher_id": row.publisher_id,
                "title": row.title,
                "description": row.description,
                "form_json": json.loads(row.form_json), 
                "categories": json.loads(row.categories), 
            }
            for row in result
        ]

        return templates

    except Exception as e:
        print(f"Error fetching templates: {e}")
        return []
    
def get_templates_data_by_id(publisher_id: str, db: Session):
    """
    Fetch all templates for a specific publisher.

    :param publisher_id: ID of the publisher.
    :param db: Database session.
    :return: List of templates for the given publisher.
    """
    try:
        sql_query = """
            SELECT id, publisher_name, publisher_id, title, description, form_json, categories
            FROM templates
            WHERE publisher_id = :publisher_id
        """
        
        result = db.execute(text(sql_query), {"publisher_id": publisher_id}).fetchall()
        
        templates = [
            {
                "id": row.id,
                "publisher_name": row.publisher_name,
                "publisher_id": row.publisher_id,
                "title": row.title,
                "description": row.description,
                "form_json": json.loads(row.form_json),
                "categories": json.loads(row.categories), 
            }
            for row in result
        ]

        return templates

    except Exception as e:
        print(f"Error fetching templates for publisher {publisher_id}: {e}")
        return []
    

def add_contact_form(contact: Contact, db: Session):
    """
    Adds a new contact form submission to the database.

    This function performs the following steps:
    1. Checks if there are already 3 unprocessed requests for the same email or phone number.
    2. If the limit is reached, the function returns an error message indicating too many pending requests.
    3. Generates a unique contact ID to avoid collisions in the database.
    4. Inserts the new contact form data (name, email, phone number, message, and 'seen' status) into the 'contactforms' table.
    5. Commits the transaction to the database.

    Args:
        contact (Contact): The contact form data to be submitted.
        db (Session): The database session used to interact with the database.

    Returns:
        str: A success message if the form is successfully added, or an error message if something goes wrong.
    """
    try:
        # Check if there are already 3 unprocessed requests for the same email or phone number
        existing_requests = db.execute(
            text("""
                SELECT COUNT(*) FROM contactforms 
                WHERE (email = :email OR phone_number = :phone_number) AND seen = :seen
            """),
            {"email": contact.email, "phone_number": contact.phone, "seen": False}
        ).fetchone()[0]

        if existing_requests >= 3:
            return "Too many pending requests for this email or phone number."

        # Generate a unique contact ID
        contact_id = str(uuid.uuid4())
        while db.execute(
            text("SELECT COUNT(*) FROM contactforms WHERE id = :contact_id"),
            {"contact_id": contact_id}
        ).fetchone()[0] > 0:
            contact_id = str(uuid.uuid4())
        query = """
            INSERT INTO contactforms (id, name, email, phone_number, message, seen)
            VALUES (:id, :name, :email, :phone_number, :message, :seen)
        """
        
        db.execute(text(query), {
            "id": contact_id,
            "name": contact.name,
            "email": contact.email,
            "phone_number": contact.phone,
            "message": contact.message,
            "seen": False  
        })
        db.commit()
        
        return "success"
    
    except Exception as e:
        db.rollback()
        return f"Error creating contact request: {str(e)}"
