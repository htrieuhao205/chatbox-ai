import pandas as pd
from sklearn.ensemble import RandomForestClassifier # Chọn mô hình "Rừng Ngẫu nhiên"
from sklearn.model_selection import train_test_split
import joblib

print("Bắt đầu huấn luyện mô hình dự báo rủi ro...")

# 1. Đọc dữ liệu
df = pd.read_csv('risk_data.csv')

# 2. Tách dữ liệu: X là "đặc trưng", y là "kết quả"
X = df.drop('will_fail', axis=1) # Lấy 4 cột đầu
y = df['will_fail']             # Lấy cột cuối (mục tiêu)

# 3. (Optional) Chia train/test để xem độ chính xác
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Chọn mô hình
# RandomForest là mô hình rất tốt cho dữ liệu bảng
model = RandomForestClassifier(n_estimators=100, random_state=42)

# 5. Dạy (train) mô hình với TOÀN BỘ dữ liệu (vì data ít)
model.fit(X, y)

# 6. Lưu mô hình (bộ não dự báo) ra file
joblib.dump(model, 'risk_predictor.pkl')

print("Đã huấn luyện và lưu mô hình DỰ BÁO RỦI RO thành công!")