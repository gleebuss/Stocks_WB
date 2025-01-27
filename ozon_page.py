import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from OzonTable import OzonTable


def load_files():
    required_files = ["sales_xlsx", "markup_xlsx", "goods_exclude_xlsx"]

    if all(st.session_state.get(key) is not None for key in required_files):
        if 'all_tables' not in st.session_state:
            sales_xlsx: UploadedFile = st.session_state["sales_xlsx"]
            markup_xlsx: UploadedFile = st.session_state["markup_xlsx"]
            goods_exclude_xlsx: UploadedFile = st.session_state["goods_exclude_xlsx"]

            st.session_state['all_tables'] = OzonTable(sales_xlsx, markup_xlsx, goods_exclude_xlsx)

    return st.session_state.get('all_tables', None)


def remove_percentage_order_limit(all_tables: OzonTable):
    if st.session_state["percentage"] is not None and st.session_state["order_limit"] is not None:
        percentage = int(st.session_state["percentage"])
        order_limit = int(st.session_state["order_limit"])
        all_tables.remove_by_percentage_order_limit(percentage, order_limit)


def remove_brand(all_tables: OzonTable):
    if st.session_state["selected_brand"] is not None and st.session_state["percentage_brand"] is not None:
        percentage_brand = int(st.session_state["percentage_brand"])
        brand = st.session_state["selected_brand"]
        all_tables.remove_by_brand(percentage_brand, brand)


def remove_category(all_tables: OzonTable):
    if st.session_state["selected_item"] is not None and st.session_state["percentage_category"] is not None:
        percentage_category = int(st.session_state["percentage_category"])
        category = st.session_state["selected_item"]
        all_tables.remove_by_category(percentage_category, category)


def remove_article(all_tables: OzonTable):
    if st.session_state["selected_article"] is not None:
        selected_article = st.session_state["selected_article"]
        all_tables.remove_by_article(selected_article)


def save_article(all_tables: OzonTable):
    if st.session_state["selected_article"] is not None:
        selected_article = st.session_state["selected_article"]
        all_tables.save_article(selected_article)


def display_filters(all_tables):
    st.subheader("Глобальные Фильтры")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.text_input("", label_visibility='collapsed', placeholder="Процент наценки после скидки", key="percentage")
    with col2:
        st.text_input("", label_visibility='collapsed', placeholder="Ограничение по заказам", key="order_limit")
    with col3:
        st.button("Применить", on_click=remove_percentage_order_limit, args=(all_tables,), key="percentage_button")


    st.subheader("Фильтры по брендам и категориям")
    col4, col5, col6 = st.columns([2, 2, 2])
    brand_options = all_tables.get_brands()
    item_options = all_tables.get_items()
    article_options = all_tables.get_article()
    with col4:
        st.selectbox('Выберите бренд', brand_options, label_visibility='collapsed', key="selected_brand")
        st.selectbox('Выберите предмет', item_options, label_visibility='collapsed', key="selected_item")
        st.selectbox('Выберите артикул', article_options, label_visibility='collapsed', key="selected_article")

    with col5:
        st.text_input("", label_visibility='collapsed',
                                   placeholder="Процент наценки после скидки", key="percentage_brand")
        st.text_input("", label_visibility='collapsed',
                                    placeholder="Процент наценки после скидки", key="percentage_category")
        st.button("Добавить в акцию", on_click=remove_article, args=(all_tables,), key="remove_article_button")
    with col6:
        st.button("Применить", on_click=remove_brand, args=(all_tables,), key="remove_brand_button")
        st.button("Применить", on_click=remove_category, args=(all_tables,), key="remove_category_button")
        st.button("Убрать из акции", on_click=save_article, args=(all_tables,), key="save_article_button")


def main():
    all_tables = None

    with st.sidebar:
        with st.popover("Загрузите файлы здесь"):
            st.file_uploader("Воронка продаж", type=["xlsx"], key="sales_xlsx")
            st.file_uploader("Наценка", type=["xlsx"], key="markup_xlsx")
            st.file_uploader("Товары для исключения", type=["xlsx"], key="goods_exclude_xlsx")

        all_tables = load_files()

        if all_tables:
            st.markdown(all_tables.get_logs())

    if all_tables:
        st.header("Файлы успешно загружены и обработаны!")
        display_filters(all_tables)
        st.subheader("Обработанный файл")
        st.download_button(
            label="Скачать файл",
            data=all_tables.download_excel(),
            file_name="output.xlsx",
        )
    else:
        st.warning("Пожалуйста, загрузите все необходимые файлы.")


main()