import streamlit as st
import requests
import pyrebase

# Cấu hình Firebase Client (Bạn điền thông tin config từ Firebase Console của bạn vào đây)
firebaseConfig = {
  "apiKey": "YOUR_API_KEY",
  "authDomain": "YOUR_PROJECT.firebaseapp.com",
  "projectId": "YOUR_PROJECT_ID",
  "databaseURL": "YOUR_DB_URL",
  "storageBucket": "YOUR_BUCKET.appspot.com",
  "messagingSenderId": "YOUR_SENDER_ID",
  "appId": "YOUR_APP_ID"
}

# Khởi tạo pyrebase
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Sổ Tay Kế Toán Cá Nhân", layout="centered")
st.title("📊 Quản Lý Thu Chi Cá Nhân")

# ================= 1. ĐĂNG NHẬP / ĐĂNG XUẤT =================
if 'user' not in st.session_state:
    st.info("Vui lòng đăng nhập để tiếp tục.")
    email = st.text_input("Email")
    password = st.text_input("Mật khẩu", type="password")
    
    if st.button("Đăng nhập"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state['user'] = user
            st.success("Đăng nhập thành công!")
            st.rerun()
        except Exception as e:
            st.error("Sai tài khoản hoặc mật khẩu!")
else:
    user_id = st.session_state['user']['localId']
    st.success(f"Tài khoản đang đăng nhập: {st.session_state['user']['email']}")
    
    if st.button("Đăng xuất"):
        del st.session_state['user']
        st.rerun()

    st.markdown("---")

    # ================= 2. FEATURE CHÍNH: NHẬP LIỆU =================
    st.subheader("📝 Ghi nhận phát sinh")
    
    with st.form("transaction_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            trans_type = st.radio("Loại", ["Chi", "Thu"])
        with col2:
            amount = st.number_input("Số tiền (VNĐ)", min_value=0, step=10000)
        with col3:
            category = st.selectbox("Khoản mục", ["Tài liệu học tập", "Logistics/Vận chuyển", "Sinh hoạt phí", "Ăn uống", "Khác"])
            
        description = st.text_input("Diễn giải (VD: Mua giáo trình, thanh toán cước...)")
        
        submitted = st.form_submit_button("Lưu dữ liệu")
        
        if submitted:
            payload = {
                "user_id": user_id,
                "amount": amount,
                "description": description,
                "category": category,
                "type": trans_type
            }
            res = requests.post(f"{BACKEND_URL}/transactions", json=payload)
            if res.status_code == 200:
                st.success(res.json()["message"])
            else:
                st.error("Có lỗi xảy ra khi kết nối Backend!")

    st.markdown("---")

    # ================= 3. ĐỌC VÀ HIỂN THỊ DỮ LIỆU =================
    st.subheader("📋 Sổ chi tiết giao dịch")
    
    if st.button("Tải lại danh sách"):
        res = requests.get(f"{BACKEND_URL}/transactions/{user_id}")
        if res.status_code == 200:
            data = res.json()["transactions"]
            if data:
                # Hiển thị data dưới dạng bảng
                st.dataframe(data, use_container_width=True)
            else:
                st.info("Chưa có phát sinh nào.")
