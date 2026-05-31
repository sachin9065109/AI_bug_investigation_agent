import streamlit as st


st.title("AI Bug Investigation Agent")

user_input = st.text_input("Enter your bug description:")

if st.button("Analyze"):
    st.write("Analyzing...")
    st.write("The result will appear here.")
