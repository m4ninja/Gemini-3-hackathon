import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Factory Sentinel AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- AUTHENTICATION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# --- PDF GENERATOR (FIXED FOR TEXT WRAPPING) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Factory Sentinel - Full Incident Report', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(report_data):
    # This is for single reports (from button)
    # We wrap this in a list to use the same logic as the full report
    return generate_full_report([report_data] if isinstance(report_data, dict) else report_data)

def generate_full_report(history_data=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Meta Data
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.cell(0, 10, f"Location: Factory Floor - Sector 4 (Cam-01)", 0, 1)
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 10, "Time", 1, 0, 'C', 1)
    pdf.cell(140, 10, "Violation Detected", 1, 1, 'C', 1)
    
    # Table Content
    pdf.set_font("Arial", size=10)
    
    # Load data if not provided directly
    if history_data is None:
        if os.path.exists("incident_log.json"):
            with open("incident_log.json", "r") as f:
                history_data = json.load(f)
        else:
            history_data = []

    for item in history_data:
        timestamp = str(item.get('timestamp', item.get('Time', 'N/A')))
        issue = str(item.get('issue', item.get('Violation', 'Unknown Issue')))
        
        # --- LOGIC FOR TEXT WRAPPING ---
        # 1. Save current cursor position (Top-Left of the row)
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # 2. Check for page break
        if y_start > 270: # If near bottom of A4 page
            pdf.add_page()
            y_start = pdf.get_y()
            x_start = pdf.get_x()
        
        # 3. Print the "Violation" cell FIRST using MultiCell to measure its height
        # We move the cursor to the right to print the second column first
        pdf.set_xy(x_start + 50, y_start)
        pdf.multi_cell(140, 10, issue, 1, 'L')
        
        # 4. Get the new Y position (Bottom of the row)
        y_end = pdf.get_y()
        row_height = y_end - y_start
        
        # 5. Move cursor BACK to the start to print the "Time" cell
        pdf.set_xy(x_start, y_start)
        pdf.cell(50, row_height, timestamp, 1, 0, 'C') # Use row_height so borders match
        
        # 6. Move cursor to the next line for the next loop
        pdf.set_xy(x_start, y_end)

    if not history_data:
        pdf.cell(190, 10, "No incidents recorded.", 1, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# --- 1. LOGIN PAGE ---
def login_page():
    components.html("""<script>var v=document.getElementById('vanta-canvas');if(v){v.remove()};window.parent.document.querySelector(".stApp").style.background="#000000";</script>""", height=0, width=0)
    st.markdown("""<style>.stApp{background:#000!important}.login-box{margin-top:100px;padding:40px;background:#111;border:1px solid #333;text-align:center;border-radius:10px}h1{color:white!important}</style>""", unsafe_allow_html=True)
    _, c2, _ = st.columns([1,1,1])
    with c2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.title("🔐 ACCESS CONTROL")
        u = st.text_input("ID")
        p = st.text_input("Password", type="password")
        if st.button("LOGIN", type="primary", use_container_width=True):
            if u=="admin" and p=="1234":
                st.session_state['authenticated'] = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 2. MAIN DASHBOARD ---
def main_dashboard():
    components.html("""<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/vanta/0.5.24/vanta.net.min.js"></script><script>window.onload=function(){var d=document.createElement('div');d.id='vanta-canvas';window.parent.document.body.appendChild(d);VANTA.NET({el:window.parent.document.getElementById('vanta-canvas'),mouseControls:true,touchControls:true,minHeight:200.00,minWidth:200.00,scale:1.00,scaleMobile:1.00,color:0x00ff99,backgroundColor:0x050505,points:11.00,maxDistance:22.00,spacing:18.00})}</script>""", height=0, width=0)
    
    st.markdown("""<style>.stApp{background:transparent!important}header{background:transparent!important}#vanta-canvas{position:fixed;top:0;left:0;width:100%;height:100%;z-index:-1;opacity:0.5}div[data-testid="metric-container"]{background:#0e1117!important;border:1px solid #00cc96;color:white}h1,h2,h3{color:white!important;text-shadow:2px 2px 0 #000;background:rgba(0,0,0,0.8);padding:5px 15px;border-left:5px solid #00cc96}.danger-box{background:#4a0000;border:2px solid red;color:#ffcccc;padding:20px;text-align:center;font-weight:bold}.safe-box{background:#002b00;border:2px solid #00cc96;color:#ccffcc;padding:20px;text-align:center;font-weight:bold}</style>""", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1: st.title("🛡️ FACTORY SENTINEL AI")
    with c2: 
        c2a, c2b = st.columns(2)
        with c2a: live = st.toggle("🔴 LIVE", True)
        with c2b: 
            if st.button("LOGOUT"): 
                st.session_state['authenticated']=False
                st.rerun()
    
    st.markdown("---")
    
    col_vid, col_met = st.columns([2, 1])
    with col_vid: vid_ph = st.empty()
    with col_met: 
        date_ph = st.empty()
        stat_ph = st.empty()
        conf_ph = st.empty()
        
    st.markdown("---")
    st.subheader("📈 CONFIDENCE TREND")
    graph_ph = st.empty()
    
    st.markdown("---")
    c_log, c_rep = st.columns(2)
    with c_log: 
        st.subheader("📜 RECENT ALERTS")
        log_ph = st.empty()
    with c_rep:
        st.subheader("📑 FULL HISTORY REPORT")
        
        hist_count = 0
        if os.path.exists("incident_log.json"):
            try:
                with open("incident_log.json", "r") as f:
                    hist_count = len(json.load(f))
            except: pass
        
        st.info(f"Database contains {hist_count} recorded incidents.")
        
        if st.button(f"Download Full PDF Report ({hist_count} Events) 📄", type="primary"):
            # Generates PDF from the JSON log file
            pdf_data = generate_full_report()
            st.download_button("📥 Click to Save PDF", data=pdf_data, file_name="Full_Incident_Log.pdf", mime="application/pdf")

    if 'history' not in st.session_state: st.session_state['history'] = []
    
    if live:
        while live:
            status_file = "status.json"
            curr = {}
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r") as f: curr = json.load(f)
                    if curr: 
                        st.session_state['history'].append({"Time": datetime.now().strftime("%H:%M:%S"), "Conf": curr.get("confidence", 0)})
                        if len(st.session_state['history']) > 30: st.session_state['history'].pop(0)
                except: pass
            
            if os.path.exists("current_frame.jpg"):
                try: vid_ph.image("current_frame.jpg", caption="Live Feed", width="stretch")
                except: vid_ph.image("current_frame.jpg", caption="Live Feed", use_container_width=True)
            
            date_ph.write(f"**{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
            
            if curr.get("status") == "DANGER":
                stat_ph.markdown(f'<div class="danger-box">⚠️ VIOLATION: {curr.get("issue")}</div>', unsafe_allow_html=True)
                log_ph.error(f"{curr.get('issue')}")
            else:
                stat_ph.markdown(f'<div class="safe-box">✅ SAFE</div>', unsafe_allow_html=True)
                log_ph.success("No active violations.")
                
            conf_ph.metric("Confidence", f"{curr.get('confidence', 0)}%")
            
            if st.session_state['history']:
                df = pd.DataFrame(st.session_state['history'])
                fig = px.area(df, x="Time", y="Conf", markers=True, color_discrete_sequence=["#00cc96"])
                fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#00cc96"), height=250, yaxis_range=[0,100])
                try: graph_ph.plotly_chart(fig, use_container_width=True)
                except: graph_ph.plotly_chart(fig)
            
            time.sleep(1)

# --- 3. CONTROLLER ---
if __name__ == "__main__":
    if st.session_state['authenticated']:
        main_dashboard()
    else:
        login_page()
