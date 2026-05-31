import streamlit as st
# Apne AI logic ka function import karein (agar alag file mein hai)
from agent.agent import analyze_bug_with_ai 

st.title("AI Bug Investigation Agent")

user_input = st.text_input("Enter your bug description:")

if st.button("Analyze"):
    if user_input:
        st.write("Analyzing... please wait.")
        
        # Yahan aapka AI function call ho raha hai
        try:
            result = analyze_bug_with_ai(user_input)
            st.success("Analysis Complete!")
            st.write(result)
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a bug description first.")
