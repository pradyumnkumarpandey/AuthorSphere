from fastapi import FastAPI , Depends, HTTPException , Form , status , Query
from sqlalchemy import  Column,String, ForeignKey, create_engine, FLOAT, Boolean, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import Session, sessionmaker, joinedload, relationship
from sqlalchemy import func
from pydantic import BaseModel, Field
from  typing import Optional
from fastapi.responses import JSONResponse
app = FastAPI()



'''MySQL'''
DATABASE_URL = "mysql+pymysql://root:Password123@localhost/fastapi-practice2"
engine = create_engine(DATABASE_URL, connect_args={})
metadata = MetaData()

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

class Author(Base):
    __tablename__ = "author"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(50))
    pen_name = Column(String(50),nullable=True)
    # Relationship to books
    books = relationship("Book", back_populates="author")
    def __repr__(self):
        return f"<Author(id={self.id})>"


class Book(Base):
    __tablename__ = "book"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    title = Column(String(255))
    price = Column(FLOAT)
    category = Column(String(20))
    is_active = Column(Boolean, default=True)
    author_id = Column(Integer, ForeignKey("author.id") , nullable=False)
    # Relationship to author
    author = relationship("Author", back_populates="books")

# Create the table
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



class CreateAuthor(BaseModel):
    name: str
    pen_name :Optional[str] = None

class ListAuthor(BaseModel):
    id:int
    name:str
    pen_name:Optional[str] = None





@app.post("/author/", response_model=dict)
def add_author(author:CreateAuthor, db:Session = Depends(get_db)):
    check_existing = db.query(Author).filter(func.lower(Author.name) == author.name.lower()).all()
    if check_existing:
        db.close()
        raise HTTPException(status_code=400, detail={"status":False,"message":"This Author already exists!."})
    instance = Author(name = author.name, pen_name = author.pen_name)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    db.close()

    return {"status":True,"message":"Author created successfully!","id":instance.id, "name":instance.name, "pen_name":instance.pen_name}

@app.get("/author/", response_model= list[ListAuthor])
def get_author(db:Session = Depends(get_db)):
    instances = db.query(Author).all()
    db.close()
    return instances



class CreateBook(BaseModel):
    title:str = Field(...) 
    price:str = Field(...)
    category:str = Field(...)
    author:str = Field(...)
    @classmethod
    def as_form(
        cls,
        title: str = Form(...),
        price: str = Form(...),
        category:str = Form(...),
        author:str = Form(...)
    ) -> "CreateBook":
        return cls(title=title, price=price,category=category,author=author)
    class Config:
        orm_mode = True
        # author:str =Field(...)
        # price:str=Field(...)

@app.post("/book/")
def add_book(book:CreateBook = Depends(CreateBook.as_form), db: Session = Depends(get_db)):
    author_list = db.query(Author).all()
    authors = [author.id for author in author_list]
    title = book.title
    price = book.price
    category = book.category
    author = book.author
    try:
        check_author_id = int(author)
        if check_author_id not in authors:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content = {"status":False,
                                       "message":"Invalid Author ID!."})
    except ValueError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content = {"status":False,
                                       "message":"Author ID must be integer."})
    try:
        float(price)
    except ValueError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content = {"status":False,
                                       "message":"Price must be numeric."})
    
    instance = Book(title = title, price = price, category = category, author_id = author)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content={"status":True,"message":"Book Added Successfully!."})



class ListBooks(BaseModel):
    id:int
    title:str
    category:str
    price:float
    author:ListAuthor

class PaginatedResponse(BaseModel):
    status:bool
    message:str
    count:int
    previous_page:Optional[int]=None
    next_page:Optional[int]=None
    result:list[dict]

@app.get("/book/",response_model=PaginatedResponse)
def get_book_list(page:int = Query(1,ge=1), page_size:int = Query(10, ge=1),db:Session = Depends(get_db)):
    total = db.query(Book).count()
    books = db.query(Book).options(joinedload(Book.author)).offset(page-1).limit(page_size).all()
    formatted_response = [
        {
            "id":book.id,
            "title":book.title,
            "category":book.category,
            "price":book.price,
            "author":{
                "id":book.author.id,
                "name":book.author.name,
                "pen_name":book.author.pen_name
            }
        }
        for book in books
    ]
    next = page +1 if (page_size * page) < total else None
    prev = page -1 if page>1 else None
    return {
        "status": True,
        "message": "Books fetched successfully!",
        "next_page": next,
        "previous_page": prev,
        "count": total,
        "result": formatted_response
    }



class ListAuthorDetails(BaseModel):
    # status:bool
    # message:str
    id:int
    name:str
    pen_name:Optional[str]= None
    book_details:list[dict]
class DetailedAutghorList(BaseModel):
    status:bool
    message:str
    data:list[dict]
@app.get("/author_details/",response_model=DetailedAutghorList)
def list_author_details(db:Session = Depends(get_db)):
    authors = db.query(Author).options(joinedload(Author.books)).all()
    data = [
        {
            "id":author.id,
            "name":author.name,
            "pen_name":author.pen_name,
            "book_details":[
                {
                    "id":book.id,
                    "title":book.title,
                    "category":book.category,
                    "price":book.price,
                }
                for book in author.books
            ]
        }
        for author in authors
    ]
    return {
        "status":True,
        "message":"data fetched successfully!",
        "data":data
    }