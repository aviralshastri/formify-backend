from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models import User, SignUpRequest, LoginRequest, Token, TokenStatus, GetForm, CreateForm, CreateFormReponse, AddTemplate, AddTemplateResponse,GetTemplatesResponse, Contact,ContactResponse
from functions import hash_password, verify_password, create_access_token, verify_access_token, get_db,get_form_json,add_form,add_template, get_templates_data, get_templates_data_by_id,add_contact_form
from typing import Optional,List
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

@app.post("/signup", response_model=dict)
def sign_up(request: SignUpRequest, db: Session = Depends(get_db)):
    hashed_password = hash_password(request.password)
    new_user = User(
        name=request.name,
        email=request.email,
        phone=request.phone,
        password=hashed_password,
    )
    db.add(new_user)
    try:
        db.commit()
        return {"message": "User created successfully."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists.")

@app.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    access_token = create_access_token(data={"sub": user.email})
    return Token(token=access_token, token_type="bearer")

@app.post("/verify-token", response_model=TokenStatus)
def verify_token(token: str):
    print(token)
    result = verify_access_token(token)
    return {"status": result["status"]}

@app.get("/get-form", response_model=GetForm)
def get_form(form_id: str, db: Session = Depends(get_db)):
    result = get_form_json(form_id, db)
    return result

@app.post("/create-form", response_model=CreateFormReponse)
def create_form(
    form_data: CreateForm, 
    db: Session = Depends(get_db)
):
    result = add_form(
        form_data.form_json, 
        form_data.settings, 
        form_data.active, 
        form_data.scheduled, 
        form_data.start, 
        form_data.end, 
        db
    )
    if not result["form_id"]:
        raise HTTPException(status_code=400, detail="Failed to create form.")
    
    return result

@app.post("/create-template", response_model=AddTemplateResponse)
def create_template(
    template_data: AddTemplate,
    db: Session = Depends(get_db)
):
    form_json = template_data.form_json
    categories = template_data.categories
    title = template_data.title
    description = template_data.description
    by_name = template_data.by_name
    by_id = template_data.by_id

    result = add_template(
        form_json=form_json,
        by_name=by_name,
        by_id=by_id,
        categories=categories,
        title=title,
        description=description,
        db=db
    )

    return {"message": result["message"]}

@app.get("/get-templates", response_model=GetTemplatesResponse)
def get_templates(query: str, categories: Optional[List[str]] = None, db: Session = Depends(get_db)):
    templates = get_templates_data(query=query, categories=categories, db=db)
    return {"templates": templates}

@app.get("/get-templates-by-id", response_model=GetTemplatesResponse)
def get_templates_by_id(id:str, db: Session = Depends(get_db)):
    templates = get_templates_data_by_id(publisher_id=id, db=db)
    return {"templates": templates}

@app.post("/contact", response_model=ContactResponse)
def handle_contact_form(request: Contact, db: Session = Depends(get_db)):
    try:
        result=add_contact_form(contact=request, db=db)
        return {"message": result}
    except HTTPException as e:
        raise e 
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

