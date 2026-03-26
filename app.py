import streamlit as st
import pandas as pd
from auth import login_page
from downloader import run_downloader
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Call Recording Downloader", layout="wide")

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "conversation_ids" not in st.session_state:
    st.session_state.conversation_ids = []

if "failed_ids" not in st.session_state:
    st.session_state.failed_ids = []

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📞 Recorder Tool")

    menu = option_menu(
        "Navigation",
        ["Downloader", "Logout"],
        icons=["download", "box-arrow-right"],
        default_index=0,
    )

# ---------------- LOGOUT ----------------
if menu == "Logout":
    st.session_state.logged_in = False
    st.rerun()

# =========================================================
# DOWNLOADER PAGE
# =========================================================
if menu == "Downloader":

    st.title("Call Recording Downloader")

    channel_type = st.radio(
        "Select Channel Type",
        ["Single Channel", "Dual Channel"],
        horizontal=True
    )

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Single ID", "Multiple IDs", "Upload Excel"])

    # ---- Single ----
    with tab1:
        single_id = st.text_input("Conversation ID")

        if st.button("Add ID"):
            if single_id:
                st.session_state.conversation_ids = [single_id]
                st.session_state.failed_ids = []

    # ---- Multiple ----
    with tab2:
        multi = st.text_area("Comma separated IDs")

        if st.button("Load IDs"):
            ids = [i.strip() for i in multi.split(",") if i.strip()]
            st.session_state.conversation_ids = ids
            st.session_state.failed_ids = []

    # ---- Excel ----
    with tab3:
        file = st.file_uploader("Upload Excel", type=["xlsx"])
        if file:
            df = pd.read_excel(file)
            if "conversation_id" in df.columns:
                st.session_state.conversation_ids = df["conversation_id"].astype(str).tolist()
                st.session_state.failed_ids = []
                st.success(f"{len(st.session_state.conversation_ids)} IDs loaded")
            else:
                st.error("Column 'conversation_id' missing")

    st.divider()

    ids = st.session_state.conversation_ids

    if ids:
        st.info(f"{len(ids)} IDs ready for download")
        st.dataframe(pd.DataFrame({"Conversation IDs": ids}))

    # ---------------- START DOWNLOAD ----------------
    if st.button("Start Download"):

        if not ids:
            st.warning("No IDs provided")
            st.stop()

        st.session_state.failed_ids = []
        progress = st.progress(0)
        results = []
        downloaded_files = {}

        for i, cid in enumerate(ids):

            with st.spinner(f"Downloading {cid}..."):
                success, data = run_downloader(cid, channel_type)

            if success:
                results.append([cid, "Downloaded"])
                downloaded_files[cid] = data
            else:
                results.append([cid, "Failed"])
                st.session_state.failed_ids.append(cid)

            progress.progress((i+1)/len(ids))

        st.success("Download Completed")
        st.dataframe(pd.DataFrame(results, columns=["Conversation ID", "Status"]))

        # ---------------- DOWNLOAD BUTTONS ----------------
        if downloaded_files:
            st.subheader("Download Files")

            for cid, data in downloaded_files.items():

                # Dual channel
                if isinstance(data, dict):
                    for key, file_bytes in data.items():
                        st.download_button(
                            label=f"{cid} - {key}",
                            data=file_bytes,
                            file_name=f"{cid}_{key}.wav"
                        )

                # Single channel
                else:
                    st.download_button(
                        label=f"{cid}",
                        data=data,
                        file_name=f"{cid}.wav"
                    )

        if st.session_state.failed_ids:
            st.error(f"{len(st.session_state.failed_ids)} downloads failed.")

    # ---------------- RETRY FAILED ----------------
    if st.session_state.failed_ids:

        if st.button("Retry Failed Downloads"):

            retry_ids = st.session_state.failed_ids.copy()
            st.session_state.failed_ids = []

            progress = st.progress(0)
            results = []

            for i, cid in enumerate(retry_ids):

                with st.spinner(f"Retrying {cid}..."):
                    success, _ = run_downloader(cid, channel_type)

                if success:
                    results.append([cid, "Downloaded"])
                else:
                    results.append([cid, "Failed Again"])
                    st.session_state.failed_ids.append(cid)

                progress.progress((i+1)/len(retry_ids))

            st.success("Retry Attempt Completed")
            st.dataframe(pd.DataFrame(results, columns=["Conversation ID", "Status"]))