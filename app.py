import streamlit as st
from agent import ask_agent

st.set_page_config(page_title="Jarvis Agent", page_icon="🤖")
st.title("🤖 Jarvis Agent")

# Keep chat history across reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input box
user_input = st.chat_input("Ask about your emails, calendar, or Excel data...")

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = ask_agent(user_input)
            except Exception as e:
                response = f"Error: {e}"
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})