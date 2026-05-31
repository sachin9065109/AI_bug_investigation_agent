import streamlit as st
# Baaki imports jo aapke project mein hain
# from agent import ... 

st.title("AI Bug Investigation Agent")

# User se input lene ke liye
user_input = st.text_input("Enter your bug description:")

if st.button("Analyze"):
    # Yahan woh logic call karein jo aapne 'agent' ya 'API' folder mein likha hai
    st.write("Analyzing...")
    # result = analyze_bug(user_input) 
    st.write("Result yahan aayega")
