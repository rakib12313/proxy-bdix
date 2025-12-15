import streamlit as st
import socks
import socket
import ftplib
import pandas as pd
import time
import io
from contextlib import contextmanager

# --- Page Config ---
st.set_page_config(page_title="BDIX FTP Explorer", layout="wide", page_icon="📂")

# --- Session State Init ---
if 'current_path' not in st.session_state:
    st.session_state['current_path'] = "/"
if 'selected_server' not in st.session_state:
    st.session_state['selected_server'] = None
if 'file_cache' not in st.session_state:
    st.session_state['file_cache'] = []

# --- Helper: Context Manager for Proxy ---
@contextmanager
def use_proxy(proxy_ver, ip, port):
    """
    Safely routes traffic through proxy and resets socket afterwards.
    """
    original_socket = socket.socket
    try:
        # Strict int conversion
        port = int(port)
        p_type = socks.SOCKS5 if int(proxy_ver) == 5 else socks.SOCKS4
        
        socks.set_default_proxy(p_type, ip, port)
        socket.socket = socks.socksocket
        yield
    except Exception as e:
        raise e
    finally:
        socket.socket = original_socket
        socks.set_default_proxy(None)

# --- Helper: Parser ---
def parse_input_line(line):
    try:
        if "|" not in line: return None
        parts = line.split("|")
        proxy_part = parts[0].strip()
        target_part = parts[1].strip()

        # Determine Protocol
        protocol = 5
        if "socks4" in proxy_part.lower(): protocol = 4
        
        # Clean Proxy IP:Port
        clean_proxy = proxy_part.replace("socks5://", "").replace("socks4://", "").replace("socks://", "")
        if "://" in clean_proxy: clean_proxy = clean_proxy.split("://")[1]
        
        p_ip, p_port = clean_proxy.split(":")

        # Clean Target Host
        t_host = target_part.replace("Opens:", "").strip()
        for prefix in ["http://", "https://", "ftp://"]:
            t_host = t_host.replace(prefix, "")
        t_host = t_host.split("/")[0] # Get host only

        return {
            "p_ver": protocol,
            "p_ip": p_ip,
            "p_port": int(p_port),
            "t_host": t_host,
            "full_name": f"{t_host} (via {p_ip})"
        }
    except:
        return None

# --- Core Logic: List Files ---
def list_ftp_files(proxy_ver, p_ip, p_port, t_host, path="/", timeout=15):
    """
    Connects, goes to specific path, returns list of items.
    """
    items = []
    error_msg = None
    
    # Retry logic: Try selected protocol, then fallback
    protocols_to_try = [proxy_ver]
    protocols_to_try.append(4 if proxy_ver == 5 else 5)

    for p_ver in protocols_to_try:
        try:
            with use_proxy(p_ver, p_ip, p_port):
                ftp = ftplib.FTP()
                ftp.connect(t_host, timeout=timeout)
                ftp.login() # Anonymous
                
                # Navigate
                ftp.cwd(path)
                
                # Get structured list
                lines = []
                ftp.retrlines('LIST', lines.append)
                
                # Parse output nicely
                for line in lines:
                    parts = line.split()
                    if len(parts) > 8:
                        name = " ".join(parts[8:])
                        is_dir = line.startswith("d")
                        size = parts[4]
                        items.append({"name": name, "is_dir": is_dir, "size": size, "raw": line})
                
                ftp.quit()
                return items, None, p_ver # Return items, no error, and working protocol
        except Exception as e:
            error_msg = str(e)
            continue # Try next protocol

    return [], error_msg, None

# --- UI Layout ---
st.title("📂 BDIX/FTP Explorer")

# 1. INPUT SECTION
with st.expander("📝 Server List Input", expanded=not st.session_state['selected_server']):
    raw_input = st.text_area(
        "Paste List (Proxy | Target)", 
        height=100,
        placeholder="socks5://123.136.24.161:1080 | Opens: http://172.16.50.4/"
    )
    
    if st.button("🔍 Scan Connections"):
        lines = raw_input.strip().split('\n')
        parsed_list = [parse_input_line(l) for l in lines if parse_input_line(l)]
        
        if not parsed_list:
            st.error("No valid lines found.")
        else:
            found_servers = []
            progress = st.progress(0)
            
            for i, item in enumerate(parsed_list):
                # Try listing root / to see if it works
                items, err, working_proto = list_ftp_files(item['p_ver'], item['p_ip'], item['p_port'], item['t_host'])
                
                if not err:
                    item['p_ver'] = working_proto # Update to working protocol
                    found_servers.append(item)
                
                progress.progress((i + 1) / len(parsed_list))
            
            if found_servers:
                st.success(f"Found {len(found_servers)} working FTPs!")
                st.session_state['server_list'] = found_servers
            else:
                st.warning("All connections failed. Check your network or proxies.")

# 2. SELECT SERVER
if 'server_list' in st.session_state and st.session_state['server_list']:
    server_options = {s['full_name']: s for s in st.session_state['server_list']}
    selected_name = st.selectbox("Select an FTP Server to Browse:", list(server_options.keys()))
    
    if st.button("📂 Open File Manager"):
        st.session_state['selected_server'] = server_options[selected_name]
        st.session_state['current_path'] = "/" # Reset to root
        st.session_state['file_cache'] = [] # Clear cache
        st.rerun()

# 3. FILE BROWSER INTERFACE
if st.session_state['selected_server']:
    srv = st.session_state['selected_server']
    
    st.divider()
    st.subheader(f"Browsing: {srv['t_host']}")
    st.caption(f"Path: `{st.session_state['current_path']}` via `{srv['p_ip']}`")
    
    # Navigation Buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    if st.session_state['current_path'] != "/":
        if col1.button("⬅️ Back"):
            # Move up one level
            parts = st.session_state['current_path'].strip("/").split("/")
            if len(parts) > 1:
                st.session_state['current_path'] = "/" + "/".join(parts[:-1])
            else:
                st.session_state['current_path'] = "/"
            st.rerun()
            
    if col2.button("🔄 Refresh"):
        st.rerun()

    # Fetch Files (Real-time)
    with st.spinner("Fetching file list..."):
        items, err, _ = list_ftp_files(
            srv['p_ver'], srv['p_ip'], srv['p_port'], srv['t_host'], 
            st.session_state['current_path']
        )
        
    if err:
        st.error(f"Error listing directory: {err}")
    else:
        # --- RENDER FILES ---
        # Sort: Directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name']))
        
        for item in items:
            c1, c2, c3 = st.columns([1, 6, 2])
            
            if item['is_dir']:
                c1.write("📁")
                c2.write(f"**{item['name']}**")
                if c3.button("Open", key=f"dir_{item['name']}"):
                    new_path = st.session_state['current_path'].rstrip("/") + "/" + item['name']
                    st.session_state['current_path'] = new_path
                    st.rerun()
            else:
                c1.write("📄")
                c2.write(f"{item['name']} ({item['size']} B)")
                
                # Helper to download
                def download_file(fname):
                    try:
                        with use_proxy(srv['p_ver'], srv['p_ip'], srv['p_port']):
                            ftp = ftplib.FTP()
                            ftp.connect(srv['t_host'], timeout=20)
                            ftp.login()
                            ftp.cwd(st.session_state['current_path'])
                            
                            buffer = io.BytesIO()
                            ftp.retrbinary(f"RETR {fname}", buffer.write)
                            ftp.quit()
                            return buffer.getvalue()
                    except Exception as e:
                        return None

                # Download Button logic is tricky in loop. 
                # We use a unique key and st.download_button directly if possible, 
                # but getting data beforehand slows rendering.
                # Optimized approach: Only download small files or on request.
                
                # For this demo, we can't pre-download everything. 
                # We show a "Prepare Download" checkbox or button.
                if c3.checkbox("Get", key=f"dl_{item['name']}"):
                    data = download_file(item['name'])
                    if data:
                        st.download_button(
                            label="⬇️ Save",
                            data=data,
                            file_name=item['name'],
                            mime="application/octet-stream",
                            key=f"save_{item['name']}"
                        )
                    else:
                        st.error("Failed")
