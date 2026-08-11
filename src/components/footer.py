import streamlit as st


def footer_home():
    
    st.markdown(f"""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
        <p style="font-weight:bold; color:white;"> Created with ❤️ by 
        <a href="https://github.com/Yash-Umdale" target="_blank" style="color:#7289DA; text-decoration:none;">Yash Umdale</a>
        </p>  
        </div>
                
                """, unsafe_allow_html=True)


def footer_dashboard():
    
    st.markdown(f"""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
        <p style="font-weight:bold; color:black;"> Created with ❤️ by 
        <a href="https://github.com/Yash-Umdale" target="_blank" style="color:#5865F2; text-decoration:none;">Yash Umdale</a>
        </p>  
        </div>
                
                """, unsafe_allow_html=True)
