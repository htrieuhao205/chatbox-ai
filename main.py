# =============================================================================
# TRỢ LÝ ẢO VHU - HỆ THỐNG BACKEND (FULL FEATURES: AUTH, DB, RAG PDF/DOCX, AUTOMATION)
# =============================================================================

import os
from datetime import datetime, timedelta
from typing import Optional, List

# --- Thư viện Web & API ---
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# --- Thư viện Database ---
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# --- Thư viện Bảo mật ---
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- Thư viện AI & Xử lý dữ liệu ---
import joblib 
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader 
from docx import Document # (MỚI) Đọc file Word

# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# =============================================================================

SECRET_KEY = "bi_mat_khong_duoc_tiet_lo" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 # Token sống 2 tiếng

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SQLALCHEMY_DATABASE_URL = "sqlite:///./vhu_secure.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =============================================================================
# 2. ĐỊNH NGHĨA DATABASE (MODELS)
# =============================================================================

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) # Mã SV
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="student") 
    major_id = Column(String) 
    total_credits = Column(Integer, default=150) # Tổng tín chỉ cần học
    completed_credits = Column(Integer, default=0)
    gpa = Column(Float, default=0.0)
    taken_subjects = Column(JSON, default={}) # Lưu điểm: {"CS101": 8.0}

class SubjectDB(Base):
    __tablename__ = "subjects"
    subject_id = Column(String, primary_key=True, index=True)
    subject_name = Column(String)
    credits = Column(Integer)

class CurriculumDB(Base):
    __tablename__ = "curriculum"
    id = Column(Integer, primary_key=True, autoincrement=True)
    major_id = Column(String)
    semester = Column(Integer)
    subject_id = Column(String)

class PrerequisiteDB(Base):
    __tablename__ = "prerequisites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String)
    prerequisite_id = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# =============================================================================
# 3. CẤU HÌNH AI & RAG (ĐỌC PDF + DOCX)
# =============================================================================

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY: genai.configure(api_key=GOOGLE_API_KEY)
try: gemini_model = genai.GenerativeModel('gemini-2.5-flash')
except: gemini_model = None

# Biến toàn cục lưu nội dung tài liệu
PDF_CONTENT = ""

def load_documents():
    global PDF_CONTENT
    root_folder = "documents"
    print(f"--- 📂 Đang quét tài liệu (PDF & DOCX) trong '{root_folder}'... ---")
    
    if not os.path.exists(root_folder):
        print(f"⚠️ Cảnh báo: Không tìm thấy thư mục '{root_folder}'")
        return

    # Quét đệ quy (Recursive scan) mọi thư mục con
    for current_root, dirs, files in os.walk(root_folder):
        category = os.path.basename(current_root)
        if category == "documents": category = "CHUNG"
        
        for filename in files:
            file_path = os.path.join(current_root, filename)
            text_file = ""
            try:
                # Đọc PDF
                if filename.endswith('.pdf'):
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: text_file += t + "\n"
                        
                # Đọc DOCX (Word)
                elif filename.endswith('.docx'):
                    doc = Document(file_path)
                    for para in doc.paragraphs:
                        text_file += para.text + "\n"
                
                if text_file:
                    PDF_CONTENT += f"\n========================================\n"
                    PDF_CONTENT += f"📂 DANH MỤC: {category.upper()} | 📄 TÀI LIỆU: {filename}\n"
                    PDF_CONTENT += f"========================================\n"
                    PDF_CONTENT += f"{text_file}\n"
                    print(f"   ✅ [Đã đọc] {category}/{filename}")
                    
            except Exception as e:
                print(f"   ❌ [Lỗi] {filename}: {e}")

    print(f"--- ✅ Hoàn tất! Tổng dữ liệu tri thức: {len(PDF_CONTENT)} ký tự ---")

load_documents()

# Tải Model ML
try: recommender_model = joblib.load('course_recommender.pkl')
except: recommender_model = None
try: risk_model = joblib.load('risk_predictor.pkl')
except: risk_model = None

# =============================================================================
# 4. CÁC HÀM XỬ LÝ BẢO MẬT
# =============================================================================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ", headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError: raise credentials_exception
        
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None: raise credentials_exception
    return user

# =============================================================================
# 5. KHỞI TẠO APP & API
# =============================================================================

app = FastAPI(title="VHU AI Assistant - Full Version")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class UserCreate(BaseModel):
    username: str 
    password: str
    full_name: str
    major_id: str = "CNTT"

class AdviceRequest(BaseModel):
    target_gpa: float = 3.2

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root(): return {"message": "Hệ thống đang chạy (v3.0)!"}

# --- AUTHENTICATION ---
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại")
    
    new_user = UserDB(
        username=user.username, 
        hashed_password=get_password_hash(user.password), 
        full_name=user.full_name, 
        major_id=user.major_id
    )
    db.add(new_user)
    db.commit()
    return {"message": "Đăng ký thành công!"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Sai tài khoản hoặc mật khẩu")
    return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}

# --- USER & PROGRESS ---
@app.get("/api/v1/me")
def get_my_profile(current_user: UserDB = Depends(get_current_user)):
    return {
        "student_id": current_user.username,
        "full_name": current_user.full_name,
        "gpa": current_user.gpa,
        "progress": (current_user.completed_credits / current_user.total_credits) * 100,
        "taken_subjects": current_user.taken_subjects
    }

# --- CỐ VẤN HỌC TẬP (DYNAMIC) ---
@app.post("/api/v1/advise/learning-path")
def advise(req: AdviceRequest, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    transcript = current_user.taken_subjects if current_user.taken_subjects else {}
    suggestions = {"retake": [], "standard": [], "advance": [], "message": ""}

    # 1. Học lại
    for code, score in transcript.items():
        if score < 5.0: suggestions["retake"].append({"code": code, "reason": "Trượt môn"})
        elif score < 6.5 and req.target_gpa >= 3.2: 
            suggestions["retake"].append({"code": code, "reason": f"Điểm thấp ({score})"})

    # 2. Môn mới (Dựa trên DB)
    current_sem = (current_user.completed_credits // 15) + 1
    next_sem = current_sem + 1
    
    def get_subjects_for_semester(sem):
        items = db.query(CurriculumDB).filter(
            CurriculumDB.major_id == current_user.major_id, CurriculumDB.semester == sem
        ).all()
        valid_subjects = []
        for item in items:
            # Check đã học chưa
            if item.subject_id in transcript and transcript[item.subject_id] >= 5.0: continue
            # Check tiên quyết
            prereqs = db.query(PrerequisiteDB).filter(PrerequisiteDB.subject_id == item.subject_id).all()
            passed_prereq = True
            for p in prereqs:
                if p.prerequisite_id not in transcript or transcript[p.prerequisite_id] < 5.0:
                    passed_prereq = False; break
            if passed_prereq:
                info = db.query(SubjectDB).filter(SubjectDB.subject_id == item.subject_id).first()
                valid_subjects.append({"code": item.subject_id, "name": info.subject_name if info else "Môn học"})
        return valid_subjects

    suggestions["standard"] = get_subjects_for_semester(next_sem)
    
    if current_user.gpa >= 8.0:
        suggestions["advance"] = get_subjects_for_semester(next_sem + 1)
        if suggestions["advance"]: suggestions["message"] = "Đủ điều kiện học vượt!"

    return {"student": current_user.full_name, "advice": suggestions}

# --- AI CHATBOT & TỰ ĐỘNG HÓA ---
@app.post("/api/v1/chat")
async def chat(req: ChatRequest, current_user: UserDB = Depends(get_current_user)):
    if not gemini_model: return {"reply": "Lỗi kết nối AI"}
    
    msg = req.message.lower()
    
    # TỰ ĐỘNG HÓA 1: Xin nghỉ học
    if "xin nghỉ" in msg or "nghỉ học" in msg:
        return {
            "reply": f"Chào {current_user.full_name}, để xin nghỉ học, bạn hãy tải mẫu đơn tại đây:\n"
                     "👉 [Link tải Biểu mẫu Xin nghỉ (.docx)]\n"
                     "Sau đó điền thông tin và gửi lại nội dung cho mình nhé (Ngày nghỉ, Lý do)."
        }
    
    # TỰ ĐỘNG HÓA 2: Nộp đơn (Giả lập)
    if "lý do" in msg and "ngày" in msg:
        return {"reply": "✅ Đã nhận thông tin! Hệ thống đã tự động gửi email báo cáo cho Giảng viên. Chúc bạn sớm giải quyết xong việc nhé."}

    # CHAT THÔNG MINH (RAG)
    context = f"TÀI LIỆU TRƯỜNG:\n{PDF_CONTENT[:15000]}..." if PDF_CONTENT else ""
    prompt = f"""
    Bạn là Trợ lý VHU. Người dùng: {current_user.full_name}.
    {context}
    Yêu cầu:
    1. Trả lời dựa vào tài liệu trên.
    2. Nếu hỏi về cảm xúc -> Động viên.
    3. Nếu hỏi về 'Tự động hóa' -> Hướng dẫn họ dùng tính năng xin nghỉ.
    Câu hỏi: {req.message}
    """
    try: return {"reply": gemini_model.generate_content(prompt).text}
    except: return {"reply": "Lỗi AI không phản hồi"}