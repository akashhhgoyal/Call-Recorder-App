import streamlit as st

def authenticate(username, password):
    users = st.secrets["users"]
    return username in users and users[username] == password

def login_page():
    st.title("🔐 Login - Call Recording System")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state["logged_in"] = True
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid username or password")