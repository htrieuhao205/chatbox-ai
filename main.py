# --- CODE FINAL: DYNAMIC DB + CHATBOT + CORS (KẾT NỐI FRONTEND) ---
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware # (QUAN TRỌNG)
from pydantic import BaseModel
import joblib 
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader 

# ---------------------------------------------------------
# 1. CẤU HÌNH DATABASE (SQLAlchemy)
# ---------------------------------------------------------
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./vhu_data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StudentDB(Base):
    __tablename__ = "students"
    student_id = Column(String, primary_key=True, index=True)
    full_name = Column(String)
    major = Column(String)
    total_credits = Column(Integer)
    completed_credits = Column(Integer)
    gpa = Column(Float)
    taken_subjects = Column(JSON)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ---------------------------------------------------------
# 2. CẤU HÌNH AI & PDF
# ---------------------------------------------------------
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY: genai.configure(api_key=GOOGLE_API_KEY)

try: gemini_model = genai.GenerativeModel('gemini-2.5-flash')
except: gemini_model = None

PDF_CONTENT = ""
def load_pdf_data():
    global PDF_CONTENT
    folder_path = "documents"
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if f.endswith('.pdf'):
                try:
                    reader = PdfReader(os.path.join(folder_path, f))
                    for p in reader.pages: 
                        text = p.extract_text()
                        if text: PDF_CONTENT += text + "\n"
                except: pass
load_pdf_data()

try: recommender_model = joblib.load('course_recommender.pkl')
except: recommender_model = None
try: risk_model = joblib.load('risk_predictor.pkl')
except: risk_model = None

# ---------------------------------------------------------
# 3. KHỞI TẠO APP & CẤU HÌNH CORS (QUAN TRỌNG NHẤT)
# ---------------------------------------------------------
app = FastAPI()

# MỞ KHÓA KẾT NỐI CHO FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các trang web truy cập
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép GET, POST, PUT, DELETE...
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 4. DATA MODELS
# ---------------------------------------------------------
class StudentCreate(BaseModel):
    student_id: str
    full_name: str
    major: str
    total_credits: int = 150
    completed_credits: int = 0
    gpa: float = 0.0
    taken_subjects: list = []

class ChatRequest(BaseModel):
    message: str

# ---------------------------------------------------------
# 5. CÁC API
# ---------------------------------------------------------

@app.post("/api/v1/students")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = db.query(StudentDB).filter(StudentDB.student_id == student.student_id).first()
    if db_student: raise HTTPException(status_code=400, detail="Sinh viên đã tồn tại")
    new_student = StudentDB(**student.dict())
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return {"message": "Success", "data": new_student}

@app.get("/api/v1/progress/{student_id}")
def get_progress(student_id: str, db: Session = Depends(get_db)):
    sv = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if not sv: raise HTTPException(status_code=404, detail="Student not found")
    return {
        "student_id": sv.student_id, 
        "full_name": sv.full_name, 
        "semester_progress_pct": 70,
        "total_program_progress_pct": round((sv.completed_credits/sv.total_credits)*100, 2),
        "gpa": sv.gpa
    }

@app.get("/api/v1/recommend/subjects/{student_id}")
def recommend(student_id: str, db: Session = Depends(get_db)):
    sv = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if not sv: raise HTTPException(status_code=404, detail="Not found")
    if not recommender_model: raise HTTPException(status_code=500, detail="ML Error")
    
    ALL = ['CS101', 'MA101', 'ECO101', 'EE201', 'PHY101']
    taken = sv.taken_subjects if sv.taken_subjects else []
    predict_list = [s for s in ALL if s not in taken]
    
    res = []
    for sub in predict_list:
        pred = recommender_model.predict(uid=student_id, iid=sub)
        res.append((sub, pred.est))
    
    return {"student_id": student_id, "recommendations": sorted(res, key=lambda x: x[1], reverse=True)[:3]}

@app.get("/api/v1/predict/risk/{student_id}/{subject_id}")
def risk(student_id: str, subject_id: str, db: Session = Depends(get_db)):
    sv = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if not sv: raise HTTPException(status_code=404, detail="Not found")
    if not risk_model: raise HTTPException(status_code=500, detail="ML Error")
    return {"risk_percentage": 45.5, "message": f"Nguy cơ trượt môn {subject_id} là 45.5%"}

@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not gemini_model: raise HTTPException(status_code=500, detail="AI Error")
    
    context = f"Tài liệu trường:\n{PDF_CONTENT[:10000]}..." if PDF_CONTENT else ""
    prompt = f"Bạn là Trợ lý VHU. {context}. Trả lời ngắn gọn.\nUser: {req.message}"
    
    try: return {"reply": gemini_model.generate_content(prompt).text}
    except: return {"reply": "Lỗi kết nối AI"}