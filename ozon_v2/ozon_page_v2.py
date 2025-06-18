import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from ozon_v2.OzonAPI import OzonAPI

def main():

    with st.sidebar:
        with st.popover("Загрузите файлы здесь"):
            st.file_uploader("Стикеры", type=["pdf"], key="stickers_pdf")
            st.file_uploader("Плата", type=["xlsx"], key="plata_xlsx")

    if st.session_state["stickers_pdf"] and st.session_state["plata_xlsx"]:
        st.header("Файлы успешно загружены и обработаны!")
        ozonAPI = OzonAPI(client_id=st.secrets["client_id"], key=st.secrets["key"])
        download_pdf, download_xlsx = ozonAPI.download_df_pdf(st.session_state["plata_xlsx"], st.session_state["stickers_pdf"])
        st.subheader("Обработанный файл")
        st.download_button(
            label="Скачать файл: Стикеры",
            data=download_pdf,
            file_name="Стикер.pdf",
        )

        st.download_button(
            label="Скачать файл: Лист подбора",
            data=download_xlsx,
            file_name="Лист подбора.xlsx",
        )
    else:
        st.warning("Пожалуйста, загрузите все необходимые файлы.")

main()