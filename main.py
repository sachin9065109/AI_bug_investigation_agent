import streamlit as st


st.title("AI Bug Investigation Agent")

user_input = st.text_input("Enter your bug description:")

if st.button("Analyze"):
    st.write("Analyzing...")
    st.write("The result will appear here.")


# apiroutes.py ka example
from fastapi import APIRouter
from agent.agent import analyze_bug_with_ai

router = APIRouter()

@router.post("/investigate")
async def investigate_bug(description: str):
    # Yahan AI function call ho raha hai
    ai_result = analyze_bug_with_ai(description)
    return {"analysis": ai_result}
