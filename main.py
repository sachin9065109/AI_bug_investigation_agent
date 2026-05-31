import streamlit as st
import sys
import os

# Path set karein taaki 'agent' folder mil jaye
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agent.agent import analyze_bug_with_ai

st.title("AI Bug Investigation Agent")
user_input = st.text_input("Enter your bug description:")

if st.button("Analyze"):
    if user_input:
        st.write("Analyzing...")
        result = analyze_bug_with_ai(user_input)
        st.write(result)
    else:
        st.warning("Please enter something!")
