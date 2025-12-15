import streamlit as st
import socks
import socket
import ftplib
import pandas as pd
import time
import io
from contextlib import contextmanager

# --- Page Config ---
st.set_page_config(page_title="BDIX/FTP Proxy Scanner", layout="wide", page_icon="📡")

# --- CSS for Mobile Optimization ---
st.markdown("""
<style>
    .stTextArea textarea { font-size: 12px; font-family: monospace; }
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# --- Helper: Context Manager for Proxy ---
@contextmanager
def use_proxy(proxy_ver, ip, port):
    """
    Safely routes traffic through proxy and resets socket afterwards.
    """
    original_socket = socket.socket
    try:
        p_type = socks.SOCKS5 if proxy_ver == 5 else socks.SOCKS4
        socks.set_default_proxy(p_type, ip, int(port))
        socket.socket = socks.socksocket
        yield
    finally:
        socket.socket = original_socket
        socks.set_default_proxy(None)

# --- Helper: Parser ---
def parse_input_line(line):
    """
    Parses format: socks5://1.2.3.4:1080 | Opens: http://10.10.10.10/
    """
    try:
        if "|" not in line: return None
        
        parts = line.split("|")
        proxy_part = parts[0].strip() # socks5://123.136.24.161:1080
        target_part = parts[1].strip() # Opens: http://172.16.50.4/

        # Parse Proxy
        protocol = 5 # Default
        if "socks4" in proxy_part.lower(): protocol = 4
        
        # Remove scheme to get IP:Port
        clean_proxy = proxy_part.replace("socks5://", "").replace("socks4://", "")
        if "://" in clean_proxy: clean_proxy = clean_proxy.split("://")[1]
        
        p_ip, p_port = clean_proxy.split(":")
        p_port = int(p_port)

        # Parse Target
        t_host = target_part.replace("Opens:", "").strip()
        # Clean http/https/ftp and trailing slashes
        for prefix in ["http://", "https://", "ftp://"]:
            t_host = t_host.replace(prefix, "")
        t_host = t_host.split("/")[0] # Remove path, keep host

        return {
            "p_ver": protocol,
            "p_ip": p_ip,
            "p_port": p_port,
            "t_host": t_host,
            "original": line
        }
    except Exception:
        return None

# --- Core Logic: Connectivity Test ---
def test_connection(proxy_ver, p_ip, p_port, t_host, timeout=10):
    start_time = time.time()
    
    # 1. Health Check (Socket Connect)
    # We first try to connect to the proxy port itself to see if it's alive
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3) # Short timeout for handshake
        result = s.connect_ex((p_ip, p_port))
        s.close()
        if result != 0:
            return "Dead Proxy (Unreachable)", 0, []
    except:
        return "Dead Proxy (Error)", 0, []

    # 2. FTP Connection via Proxy
    file_list = []
    status = "Failed"
    
    # Helper to try FTP
    def try_ftp(ver):
        with use_proxy(ver, p_ip, p_port):
            ftp = ftplib.FTP()
            ftp.connect(t_host, timeout=timeout)
            ftp.login() # Anonymous
            files = []
            ftp.retrlines('LIST', files.append)
            ftp.quit()
            return files

    # Try Primary Protocol
    try:
        file_list = try_ftp(proxy_ver)
        status = "Success"
    except Exception as e:
        # 3. Auto-Protocol Fallback
        # If SOCKS5 failed, try SOCKS4 (or vice versa)
        alt_ver = 4 if proxy_ver == 5 else 5
        try:
            file_list = try_ftp(alt_ver)
            status = f"Success (Fallback SOCKS{alt_ver})"
        except:
            status = f"Failed ({str(e)})"

    duration = round(time.time() - start_time, 2)
    return status, duration, file_list

# --- UI Layout ---
st.title("📡 Universal FTP Proxy Scanner")
st.caption("Supports: `socks5://IP:Port | Opens: http://Target/` format")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    timeout = st.slider("Connection Timeout (seconds)", 5, 30, 10)
    max_files = st.slider("Max Files to Preview", 5, 50, 10)
    st.info("Ensure you have permission to access these networks.")

# Tabs
tab1, tab2 = st.tabs(["🚀 Bulk Scanner", "🛠️ Single Tester"])

# --- TAB 1: Bulk Scanner ---
with tab1:
    raw_input = st.text_area(
        "Paste Proxy List Here:", 
        height=150,
        placeholder="socks5://123.136.24.161:1080 | Opens: http://172.16.50.4/\nsocks5://103.189.218.83:6969 | Opens: http://10.16.100.244/"
    )
    
    col1, col2 = st.columns([1, 2])
    start_btn = col1.button("Start Scan", type="primary")
    
    if start_btn and raw_input:
        lines = raw_input.strip().split('\n')
        valid_targets = [parse_input_line(l) for l in lines if parse_input_line(l)]
        
        if not valid_targets:
            st.error("No valid lines found. Check your format.")
        else:
            st.write(f"🔍 Scanning {len(valid_targets)} targets...")
            
            results_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Container for live results
            live_table = st.empty()
            
            for i, item in enumerate(valid_targets):
                # Update UI
                progress = (i + 1) / len(valid_targets)
                progress_bar.progress(progress)
                status_text.text(f"Testing: {item['t_host']} via {item['p_ip']}...")
                
                # Run Test
                stat, lat, files = test_connection(
                    item['p_ver'], item['p_ip'], item['p_port'], item['t_host'], timeout
                )
                
                # Store Result
                res_entry = {
                    "Proxy IP": item['p_ip'],
                    "Port": item['p_port'],
                    "Target": item['t_host'],
                    "Status": stat,
                    "Latency (s)": lat,
                    "Files Found": len(files),
                    "File Sample": " | ".join(files[:3]) if files else ""
                }
                results_data.append(res_entry)
                
                # Update Table Live
                df_live = pd.DataFrame(results_data)
                live_table.dataframe(df_live, use_container_width=True)
            
            status_text.text("✅ Scan Complete")
            
            # --- Export Section ---
            if results_data:
                df = pd.DataFrame(results_data)
                
                # Filter for Success only
                success_df = df[df["Status"].str.contains("Success")]
                
                if not success_df.empty:
                    st.success(f"🎉 Found {len(success_df)} working servers!")
                    
                    # Convert to CSV
                    csv = success_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Working List (CSV)",
                        csv,
                        "working_proxies.csv",
                        "text/csv"
                    )
                    
                    # Show Detailed View of Working
                    st.subheader("📂 File Browser (Working Servers)")
                    for index, row in success_df.iterrows():
                        with st.expander(f"✅ {row['Target']} (via {row['Proxy IP']})"):
                            st.write(f"**Latency:** {row['Latency (s)']}s")
                            # We re-fetch files or parse from sample? 
                            # Since we stored sample, let's just show sample, 
                            # but ideally we store the full list in memory (simplified here)
                            st.code(row['File Sample'] + " ...", language="text")
                else:
                    st.warning("No working servers found in this batch.")

# --- TAB 2: Single Tester ---
with tab2:
    col_a, col_b = st.columns(2)
    s_ip = col_a.text_input("Proxy IP", "127.0.0.1")
    s_port = col_b.number_input("Proxy Port", 1, 65535, 1080)
    s_ver = st.selectbox("Protocol", ["SOCKS5", "SOCKS4"])
    s_target = st.text_input("FTP Target", "ftp.example.com")
    
    if st.button("Test Single Connection"):
        ver_int = 5 if s_ver == "SOCKS5" else 4
        with st.spinner("Connecting..."):
            stat, lat, files = test_connection(ver_int, s_ip, s_port, s_target, timeout)
        
        if "Success" in stat:
            st.success(f"Connected! ({lat}s)")
            st.write(f"**Status:** {stat}")
            st.write("**Directory Listing:**")
            st.code("\n".join(files[:max_files]), language="text")
            if len(files) > max_files:
                st.caption(f"... {len(files) - max_files} more files.")
        else:
            st.error(f"Connection Failed: {stat}")
