import streamlit as st
import data_tools as dt

dt.implement_data_insert()

dashboard = st.Page('dashboard.py', title ='Dashboard')
profile = st.Page('profile.py', title = 'Profile')

page_navigation = st.navigation([dashboard, profile])

page_navigation.run()
