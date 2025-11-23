import pandas as pd
from surprise import SVD, Dataset, Reader
import joblib # Thư viện để lưu/tải mô hình

print("Bắt đầu huấn luyện mô hình gợi ý...")

# 1. Đọc dữ liệu từ file CSV
df = pd.read_csv('ratings.csv')

# 2. Chuẩn bị dữ liệu cho thư viện surprise
# Thang điểm của chúng ta là từ 0-10
reader = Reader(rating_scale=(0, 10))
data = Dataset.load_from_df(df[['student_id', 'subject_id', 'grade']], reader)

# 3. Sử dụng toàn bộ dữ liệu để huấn luyện (vì đây là demo)
trainset = data.build_full_trainset()

# 4. Chọn thuật toán SVD (một thuật toán gợi ý phổ biến)
model = SVD()

# 5. Dạy (train) mô hình
model.fit(trainset)

# 6. Lưu mô hình đã huấn luyện ra 1 file
# File "course_recommender.pkl" này chính là "bộ não" AI đã học
joblib.dump(model, 'course_recommender.pkl')

print("Đã huấn luyện và lưu mô hình thành công!")