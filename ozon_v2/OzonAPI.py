import requests
import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import re
from pypdf import PdfReader, PdfWriter
import io

class OzonAPI:

    def __init__(self, client_id, key):
        self.base_url = "https://api-seller.ozon.ru/"
        self.client_id = client_id
        self.key = key

    def download_df_pdf(self, plata_xlsx, stickers_pdf):
        df = self.create_ozon_dataframe(self.getListFromAPI())
        _, sort_df = self.count_and_sort_by_articles(df)

        plata_df = pd.read_excel(plata_xlsx)

        merged_df = self.merge_common_articles_with_price(sort_df, plata_df)
        merged_df.drop('№', axis=1, inplace=True)

        output_buffer_xlsx = io.BytesIO()

        with pd.ExcelWriter(output_buffer_xlsx, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, sheet_name='sheetName', index=False, na_rep='NaN')
            
            worksheet = writer.sheets['sheetName']
            workbook = writer.book
            
            for column in merged_df:
                column_length = max(merged_df[column].astype(str).map(len).max(), len(column)) if column != "Товар" else max(merged_df[column].astype(str).map(len).max(), len(column)) * 0.6
                col_idx = merged_df.columns.get_loc(column)
                worksheet.set_column(col_idx, col_idx, column_length)
            
            bold_format = workbook.add_format({'bold': True})
            if "Этикетка" in merged_df.columns:
                etikett_col_idx = merged_df.columns.get_loc("Этикетка")
                worksheet.set_row(0, None, bold_format)
                worksheet.set_column(etikett_col_idx, etikett_col_idx, None, bold_format)
            
            centered_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            if "Количество" in merged_df.columns:
                quantity_col_idx = merged_df.columns.get_loc("Количество")
                worksheet.set_column(quantity_col_idx, quantity_col_idx, None, centered_format)

        output_pdf_buffer = io.BytesIO()

        reader = PdfReader(stickers_pdf)

        pattern=r'\d{1,3}\s\d{8,10}-\d{3,4}-\d{1,2}'
        all_stickers = []

        for page in reader.pages:
            text = page.extract_text(extraction_mode="layout")
            matches = re.findall(pattern, text)
            key = matches[0].split('\n')[1]
            temp = {
            key : page
            }

            all_stickers.append(temp)

        order = merged_df["Поставка"].drop_duplicates().to_list()
        list_pdf = []

        for i in order:
            found_values = [j[i] for j in all_stickers if i in j]

            if not found_values:
                print(f"Предупреждение: Не найден стикер для заказа {i}")
                continue

            list_pdf.append(found_values[0])

        output_pdf = PdfWriter()
        for i in list_pdf:
            output_pdf.add_page(i)

        output_pdf.write(output_pdf_buffer)

        return output_pdf_buffer.getvalue(), output_buffer_xlsx.getvalue()

    def getListFromAPI(self):
        current_time = datetime.now(timezone.utc)
        week_ago = current_time - timedelta(days=7)

        since = week_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        to = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        url = self.base_url + "v3/posting/fbs/list"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Client-Id": self.client_id,
            "Api-Key": self.key,
        }

        payload = {
            "dir": "asc",
            "filter": {
                "delivery_method_id": ["1020000152188000"],
                "since": since,
                "to": to,
                "status": "awaiting_deliver",
            },
            "limit": "1000",
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            print(f"Ошибка при выполнении запроса: {error}")
        except json.JSONDecodeError as error:
            print(f"Ошибка при декодировании JSON: {error}")

    def create_ozon_dataframe(self, response_json):
        data = []

        for i, posting in enumerate(response_json.get("result", {}).get("postings", []), 1):

            for product in posting.get("products", []):
                temp = {
                    "№": i,
                    "Поставка": posting.get("posting_number", ""),
                    "Товар": product.get("name", ""),
                    "Артикул": product.get("offer_id", ""),
                    # "SKU": product.get("sku", ""),
                    "Количество": product.get("quantity", 0),
                    # "Цена": product.get("price", ""),
                    # "Статус": posting.get("status", ""),
                    "Этикетка": posting.get("posting_number", "").split("-")[0][-4:],
                    # "Дата отгрузки": posting.get("shipment_date", ""),
                    # "Склад": posting.get("delivery_method", {}).get("warehouse", ""),
                    # "Способ доставки": posting.get("delivery_method", {}).get("name", "")
                }
                data.append(temp)

        return pd.DataFrame(data)

    def count_and_sort_by_articles(self, df, article_col='Артикул', shipment_col='Поставка'):
        """
        Считает количество артикулов и сортирует таблицу по их частоте.
        Строки с повторяющимися номерами поставок перемещаются вниз.

        Параметры:
            df (pd.DataFrame): Исходная таблица.
            article_col (str): Название колонки с артикулами. По умолчанию 'Артикул'.
            shipment_col (str): Название колонки с номерами поставок.

        Возвращает:
            tuple: (таблица_с_частотой, отсортированная_таблица)
        """

        # Проверка наличия колонок
        if article_col not in df.columns:
            raise ValueError(f"Колонка '{article_col}' не найдена в DataFrame.")
        if shipment_col not in df.columns:
            raise ValueError(f"Колонка '{shipment_col}' не найдена в DataFrame.")

        # Преобразование значений к строковому типу и удаление пробелов
        df[article_col] = df[article_col].astype(str).str.strip()
        df[shipment_col] = df[shipment_col].astype(str).str.strip()

        # Подсчет количества каждого артикула
        article_counts = df[article_col].value_counts().reset_index()
        article_counts.columns = [article_col, 'Количество_артикулов']

        # Подсчет количества каждой поставки
        shipment_counts = df[shipment_col].value_counts()

        # Отметка уникальных поставок (только один раз встречаются)
        unique_shipments = shipment_counts[shipment_counts == 1].index
        df['_shipment_is_unique'] = df[shipment_col].isin(unique_shipments)

        # Добавляем количество артикулов
        df['_article_count'] = df[article_col].map(
            article_counts.set_index(article_col)['Количество_артикулов']
        )

        # Сортировка:
        # 1. Сначала по уникальности поставки (True = уникальные вверх)
        # 2. Затем по убыванию количества артикулов
        # 3. Затем по артикулу (по возрастанию)
        df_sorted = df.sort_values(
            by=['_shipment_is_unique', '_article_count', article_col],
            ascending=[False, False, True]
        )

        # Удаление временных колонок
        df_sorted = df_sorted.drop(columns=['_shipment_is_unique', '_article_count'])

        return article_counts, df_sorted

    def merge_common_articles_with_price(self, df1, df2, article_col='Артикул', price_col='Цена за сборку', default_price=7):
        """
        Находит общие артикулы между двумя DataFrame и добавляет колонку 'Цена за сборку'.

        Параметры:
            df1 (pd.DataFrame): Первый DataFrame.
            df2 (pd.DataFrame): Второй DataFrame (должен содержать колонку с ценой).
            article_col (str): Название колонки с артикулами.
            price_col (str): Название колонки с ценой за сборку.

        Возвращает:
            pd.DataFrame: Объединённый DataFrame только с общими артикулами и ценой за сборку.
        """

        # Приведение артикула к строковому виду и удаление пробелов
        df1 = df1.copy()
        df2 = df2.copy()
        df1[article_col] = df1[article_col].astype(str).str.strip()
        df2[article_col] = df2[article_col].astype(str).str.strip()

        # Проверка наличия нужной колонки с ценой
        if price_col not in df2.columns:
            raise ValueError(f"Колонка '{price_col}' не найдена во втором DataFrame.")

        # Внутреннее объединение по артикулу
        merged_df = pd.merge(df1, df2[[article_col, price_col]], on=article_col, how='left')

        merged_df[price_col] = merged_df[price_col].fillna(default_price)
        merged_df["Общая Цена"] = f"{merged_df[price_col].sum()}₽"
        merged_df[price_col] = merged_df[price_col].apply(lambda x: f"{x}₽")
        return merged_df