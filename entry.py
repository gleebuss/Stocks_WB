import streamlit as st

pages = {
    "Tools": [
        st.Page("wb_page.py", title="WB", default=True),
        st.Page("ozon_page.py", title="OZON"),
    ]
}

pg = st.navigation(pages)

pg.run()

# if 'current_page' not in st.session_state:
#     st.session_state.current_page = "WB"
#
# if 'prev_page' not in st.session_state:
#     st.session_state.prev_page = st.session_state.current_page
# else:
#     if st.session_state.prev_page != st.session_state.current_page:
#         st.session_state.prev_page = st.session_state.current_page
#         st.experimental_rerun()