# SCRIPT NẠP DỮ LIỆU KHUNG CHƯƠNG TRÌNH VÀO DATABASE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Base, SubjectDB, CurriculumDB, PrerequisiteDB, StudentDB 

# Kết nối Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./vhu_data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# 1. Xóa dữ liệu cũ (để tránh trùng lặp khi chạy lại)
print("Dang xoa du lieu cu...")
db.query(SubjectDB).delete()
db.query(CurriculumDB).delete()
db.query(PrerequisiteDB).delete()
db.commit()

# 2. Nạp Danh sách Môn học
print("Dang nap Mon hoc...")
subjects = [
    SubjectDB(subject_id="CS101", subject_name="Nhập môn Lập trình", credits=3),
    SubjectDB(subject_id="MA101", subject_name="Toán Cao cấp 1", credits=3),
    SubjectDB(subject_id="ENG101", subject_name="Tiếng Anh 1", credits=3),
    SubjectDB(subject_id="CS102", subject_name="Lập trình Nâng cao", credits=4),
    SubjectDB(subject_id="MA102", subject_name="Toán Cao cấp 2", credits=3),
    SubjectDB(subject_id="WEB101", subject_name="Lập trình Web", credits=3),
    SubjectDB(subject_id="DB101", subject_name="Cơ sở dữ liệu", credits=3),
]
db.add_all(subjects)

# 3. Nạp Khung chương trình (Ngành CNTT)
print("Dang nap Khung chuong trinh...")
curriculum = [
    # Kỳ 1
    CurriculumDB(major_id="CNTT", semester=1, subject_id="CS101"),
    CurriculumDB(major_id="CNTT", semester=1, subject_id="MA101"),
    CurriculumDB(major_id="CNTT", semester=1, subject_id="ENG101"),
    # Kỳ 2
    CurriculumDB(major_id="CNTT", semester=2, subject_id="CS102"),
    CurriculumDB(major_id="CNTT", semester=2, subject_id="MA102"),
    # Kỳ 3
    CurriculumDB(major_id="CNTT", semester=3, subject_id="WEB101"),
    CurriculumDB(major_id="CNTT", semester=3, subject_id="DB101"),
]
db.add_all(curriculum)

# 4. Nạp Điều kiện Tiên quyết
print("Dang nap Tien quyet...")
prereqs = [
    PrerequisiteDB(subject_id="CS102", prerequisite_id="CS101"), # Muốn học CS102 phải qua CS101
    PrerequisiteDB(subject_id="WEB101", prerequisite_id="CS101"),
]
db.add_all(prereqs)

db.commit()
print("✅ HOÀN TẤT! Database đã có dữ liệu chương trình đào tạo.")
db.close()