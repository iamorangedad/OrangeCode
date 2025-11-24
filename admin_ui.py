"""
Optional Admin UI for Context Management Service
View and manage conversation contexts via Streamlit
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuration
CONTEXT_SERVICE_URL = "http://context-service:8000"

st.set_page_config(page_title="Code Agent Context Admin", page_icon="🤖", layout="wide")

st.title("🤖 Code Agent Context Management")
st.markdown("---")

# Sidebar - Service Status
with st.sidebar:
    st.header("Service Status")
    try:
        response = requests.get(f"{CONTEXT_SERVICE_URL}/", timeout=3)
        if response.ok:
            data = response.json()
            st.success("✅ Service Online")
            st.metric("Total Contexts", data.get("total_contexts", 0))
        else:
            st.error("❌ Service Error")
    except Exception as e:
        st.error(f"❌ Connection Failed\n{str(e)}")

# Main Content
tab1, tab2, tab3 = st.tabs(["📊 Session Stats", "🔍 Query Context", "🗑️ Management"])

# Tab 1: Session Statistics
with tab1:
    st.header("Session Statistics")

    session_id = st.text_input("Session ID", placeholder="Enter session ID...")

    if session_id and st.button("Get Stats", key="stats_btn"):
        try:
            response = requests.get(
                f"{CONTEXT_SERVICE_URL}/context/stats/{session_id}", timeout=5
            )
            if response.ok:
                stats = response.json()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Messages", stats.get("total_messages", 0))
                with col2:
                    st.metric(
                        "User Queries", stats.get("by_type", {}).get("user_query", 0)
                    )
                with col3:
                    st.metric(
                        "Tool Calls", stats.get("by_type", {}).get("tool_call", 0)
                    )

                # Type breakdown
                st.subheader("Message Type Breakdown")
                type_data = stats.get("by_type", {})
                if type_data:
                    df = pd.DataFrame(
                        list(type_data.items()), columns=["Type", "Count"]
                    )
                    st.bar_chart(df.set_index("Type"))

                # Timestamps
                st.subheader("Session Timeline")
                st.info(f"**Started:** {stats.get('oldest_message', 'N/A')}")
                st.info(f"**Last Activity:** {stats.get('newest_message', 'N/A')}")
            else:
                st.error("Failed to retrieve stats")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Tab 2: Query Context
with tab2:
    st.header("Query Context")

    col1, col2 = st.columns([3, 1])
    with col1:
        query_session = st.text_input("Session ID", key="query_session")
        query_text = st.text_area("Query", placeholder="Enter semantic search query...")
    with col2:
        top_k = st.number_input("Top K Results", min_value=1, max_value=20, value=5)
        filter_type = st.selectbox(
            "Filter by Type", ["None", "user_query", "tool_call", "agent_response"]
        )

    if st.button("Search", key="search_btn"):
        if query_session and query_text:
            try:
                payload = {
                    "session_id": query_session,
                    "query": query_text,
                    "top_k": top_k,
                }
                if filter_type != "None":
                    payload["filter_by_type"] = filter_type

                response = requests.post(
                    f"{CONTEXT_SERVICE_URL}/context/query", json=payload, timeout=10
                )

                if response.ok:
                    results = response.json()["messages"]
                    st.success(f"Found {len(results)} results")

                    for i, msg in enumerate(results):
                        with st.expander(
                            f"Result {i+1} - {msg['metadata'].get('type', 'unknown')} (Distance: {msg.get('distance', 'N/A'):.3f})"
                        ):
                            st.markdown(
                                f"**Role:** {msg['metadata'].get('role', 'unknown')}"
                            )
                            st.markdown(
                                f"**Timestamp:** {msg['metadata'].get('timestamp', 'N/A')}"
                            )
                            st.text_area(
                                "Content",
                                msg["content"],
                                height=150,
                                key=f"content_{i}",
                            )
                else:
                    st.error("Query failed")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("Please provide both session ID and query")

# Tab 3: Management
with tab3:
    st.header("Context Management")

    # Clear session context
    st.subheader("Clear Session Context")
    clear_session = st.text_input("Session ID to Clear", key="clear_session")
    if st.button("Clear Session", type="secondary"):
        if clear_session:
            if st.checkbox("Confirm deletion", key="confirm_clear"):
                try:
                    response = requests.post(
                        f"{CONTEXT_SERVICE_URL}/context/clear",
                        json={"session_id": clear_session},
                        timeout=5,
                    )
                    if response.ok:
                        result = response.json()
                        st.success(f"Deleted {result.get('deleted_count', 0)} messages")
                    else:
                        st.error("Failed to clear context")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a session ID")

    st.markdown("---")

    # Danger zone - clear all
    st.subheader("⚠️ Danger Zone")
    if st.button("Clear ALL Context", type="primary"):
        if st.checkbox("I understand this will delete ALL data", key="confirm_all"):
            try:
                response = requests.delete(
                    f"{CONTEXT_SERVICE_URL}/context/all", timeout=10
                )
                if response.ok:
                    st.success("All context cleared successfully")
                else:
                    st.error("Failed to clear all context")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Code Agent Context Management v1.0*")
