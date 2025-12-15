import streamlit as st
import socks
import socket
import ftplib
import sys
from contextlib import contextmanager

# Page Configuration
st.set_page_config(page_title="SOCKS FTP Tester", page_icon="🌐")

st.title("🌐 SOCKS4/5 FTP Connector")
st.markdown("""
This tool allows you to test connectivity to an FTP server through a specific SOCKS proxy.
*Useful for verifying BDIX or internal network access via authorized proxies.*
""")

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("1. Proxy Configuration")
    proxy_type_str = st.selectbox("Proxy Type", ["SOCKS5", "SOCKS4"])
    proxy_ip = st.text_input("Proxy IP", value="127.0.0.1")
    proxy_port = st.number_input("Proxy Port", min_value=1, max_value=65535, value=1080)
    
    st.divider()
    
    st.header("2. Target FTP Server")
    ftp_host = st.text_input("FTP Host/IP", value="ftp.example.com")
    ftp_port = st.number_input("FTP Port", min_value=1, max_value=65535, value=21)
    
    use_auth = st.checkbox("Requires Authentication?", value=False)
    ftp_user = "anonymous"
    ftp_pass = "anonymous@test.com"
    
    if use_auth:
        ftp_user = st.text_input("Username")
        ftp_pass = st.text_input("Password", type="password")

# --- Helper: Context Manager for Proxy ---
@contextmanager
def use_proxy(proxy_type, ip, port):
    """
    Temporarily patches the global socket to use the proxy, 
    then restores it immediately after the block finishes.
    """
    # Save the original socket
    original_socket = socket.socket
    
    try:
        # Determine strict type
        p_type = socks.SOCKS5 if proxy_type == "SOCKS5" else socks.SOCKS4
        
        # Set default proxy
        socks.set_default_proxy(p_type, ip, port)
        socket.socket = socks.socksocket
        yield
    finally:
        # Restore the original socket no matter what happens
        socket.socket = original_socket
        # Remove the default proxy setting to be safe
        socks.set_default_proxy(None)

# --- Main Logic ---
if st.button("🚀 Connect & List Files", type="primary"):
    if not proxy_ip or not ftp_host:
        st.error("Please provide both Proxy IP and FTP Host.")
    else:
        log_container = st.container()
        
        with log_container:
            st.info(f"Configuring {proxy_type_str} Proxy: {proxy_ip}:{proxy_port}")
            
            # Use the context manager to safely patch/unpatch
            with use_proxy(proxy_type_str, proxy_ip, proxy_port):
                ftp = ftplib.FTP()
                try:
                    st.write(f"⏳ Attempting connection to **{ftp_host}**...")
                    
                    # Connect
                    ftp.connect(ftp_host, port=ftp_port, timeout=15)
                    st.success(f"✅ Connected to {ftp_host}")
                    st.text(f"Server Message: {ftp.getwelcome()}")
                    
                    # Login
                    st.write(f"🔑 Logging in as `{ftp_user}`...")
                    ftp.login(ftp_user, ftp_pass)
                    st.success("✅ Login successful!")
                    
                    # List Files
                    st.write("📂 Retrieving directory listing...")
                    files = []
                    # Capture the output into the list
                    ftp.retrlines('LIST', files.append)
                    
                    if files:
                        st.code("\n".join(files[:20]), language="text") # Show first 20 lines
                        if len(files) > 20:
                            st.caption(f"...and {len(files)-20} more items.")
                    else:
                        st.warning("Directory is empty.")
                        
                except socket.timeout:
                    st.error("❌ Connection Timed Out. The proxy might be dead or the target is unreachable.")
                except socks.ProxyConnectionError:
                    st.error("❌ Failed to connect to the Proxy Server. Check the Proxy IP/Port.")
                except ftplib.error_perm as e:
                    st.error(f"❌ FTP Permission Error: {e}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    try:
                        ftp.quit()
                    except:
                        pass