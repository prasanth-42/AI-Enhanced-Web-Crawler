import streamlit as st
from scrape import scrape_website, extract_body_content, clean_body_content, split_dom_content
from parse import parse_with_groq

# Streamlit UI with sidebar
st.set_page_config(page_title="Web Scraping App 🧠", page_icon="🌐")

st.sidebar.title("🚀 Model Selection")
selected_model = st.sidebar.selectbox(
    "Choose a Model for Parsing:",
    [
        "llama3-8b-8192",
        "llama3-groq-70b-8192-tool-use-preview",
        "llama-3.1-8b-instant",
        "llava-v1.5-7b-4096-preview",
        "mixtral-8x7b-32768",
    ]
)

# Application title
st.title("AI Enhanced Web Crawler 🌐")
st.write("Easily scrape and analyze web content using advanced AI models. 🌟")

# Input for website URL
url = st.text_input("Enter Website URL 🔗")

# Step 1: Scrape the Website
if st.button("Scrape Website"):
    if url:
        st.write("🕵️‍♂️ Scraping the website...")

        # Scrape the website
        dom_content = scrape_website(url)
        body_content = extract_body_content(dom_content)
        cleaned_content = clean_body_content(body_content)

        # Store the DOM content in Streamlit session state
        st.session_state.dom_content = cleaned_content

        # Display the DOM content in an expandable text box
        with st.expander("View DOM Content"):
            st.text_area("DOM Content", cleaned_content, height=300)

# Step 2: Parse the Content
if "dom_content" in st.session_state:
    parse_description = st.text_area("Describe what you want to parse 📝")

    if st.button("Parse Content"):
        if parse_description:
            st.write(f"🤖 Parsing the content with {selected_model}...")

            # Parse content using Groq
            dom_chunks = split_dom_content(st.session_state.dom_content)
            parsed_result = parse_with_groq(dom_chunks, parse_description, model=selected_model)
            st.write(parsed_result)

# CSS for footer at the bottom of the sidebar
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #272432;  /* Dark background for visibility */
        color: white;
        text-align: center;
        padding: 10px;
        font-size: 14px;
    }
    .sidebar .footer {
        position: fixed;
        bottom: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)
