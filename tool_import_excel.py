import pandas as pd
import requests
import json
import time

# CẤU HÌNH
EXCEL_FILE = "sinhvien_data.xlsx"
API_URL = "http://127.0.0.1:8000/api/v1/students"

def import_data():
    print(f"🔄 Đang đọc file Excel: {EXCEL_FILE}...")
    
    try:
        # Đọc file Excel bằng Pandas
        df = pd.read_excel(EXCEL_FILE)
        
        # Kiểm tra xem file có dữ liệu không
        if df.empty:
            print("⚠️ File Excel rỗng!")
            return

        print(f"✅ Đã tìm thấy {len(df)} sinh viên. Bắt đầu nạp vào hệ thống...")
        print("-" * 50)

        success_count = 0
        error_count = 0

        # Duyệt qua từng dòng trong Excel
        for index, row in df.iterrows():
            # Xử lý cột 'mon_da_hoc': Chuyển chuỗi "CS101, MA101" thành list ["CS101", "MA101"]
            mon_hoc_str = str(row['mon_da_hoc'])
            if pd.isna(row['mon_da_hoc']) or mon_hoc_str.lower() == 'nan':
                taken_subjects = []
            else:
                taken_subjects = [m.strip() for m in mon_hoc_str.split(',')]

            # Tạo payload đúng chuẩn API quy định
            student_payload = {
                "student_id": str(row['masv']),
                "full_name": str(row['hoten']),
                "major": str(row['nganh']),
                "total_credits": 150, # Mặc định hoặc lấy từ Excel nếu có cột này
                "completed_credits": int(row['tinchi_tichluy']),
                "gpa": float(row['gpa']),
                "taken_subjects": taken_subjects
            }

            try:
                # Gửi request POST đến API (Giống như nhập tay trên Docs)
                response = requests.post(API_URL, json=student_payload)

                if response.status_code == 200:
                    print(f"🟢 [OK] Đã nạp: {row['hoten']} ({row['masv']})")
                    success_count += 1
                elif response.status_code == 400:
                    print(f"🟡 [SKIP] Sinh viên {row['masv']} đã tồn tại.")
                else:
                    print(f"🔴 [ERROR] Lỗi khi nạp {row['masv']}: {response.text}")
                    error_count += 1
            
            except requests.exceptions.ConnectionError:
                print("❌ LỖI: Không kết nối được Server! Hãy chắc chắn bạn đã chạy 'uvicorn main:app'.")
                return

        print("-" * 50)
        print(f"🎉 HOÀN TẤT! Thành công: {success_count} | Lỗi: {error_count}")

    except FileNotFoundError:
        print(f"❌ LỖI: Không tìm thấy file '{EXCEL_FILE}'. Hãy tạo file Excel trước.")
    except Exception as e:
        print(f"❌ LỖI KHÔNG XÁC ĐỊNH: {e}")

if __name__ == "__main__":
    import_data()