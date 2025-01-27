import io

import pandas as pd
from loguru import logger

class OzonTable:
    def __init__(self, sales_xlsx, markup_xlsx, goods_exclude_xlsx):
        self.required_article = []
        self.required_limit_order = 0

        self.log_stream = io.StringIO()
        logger.add(self.log_stream, format="{message}")

        goods_exclude_df = pd.read_excel(goods_exclude_xlsx, sheet_name=1, header=2)
        goods_exclude_df = goods_exclude_df.drop(0)
        goods_exclude_df["Артикул"] = goods_exclude_df['Артикул'].astype(str)

        self.first_sheets = pd.read_excel(goods_exclude_xlsx, sheet_name=0)
        self.second_header = pd.read_excel(goods_exclude_xlsx, sheet_name=1, nrows=2)
        print(self.second_header)
        self.second_table = goods_exclude_df
        xls = pd.ExcelFile(goods_exclude_xlsx)
        self.name_sheets = xls.sheet_names[1]

        markup_df = pd.read_excel(markup_xlsx, header=1)
        markup_df['Оригинальный номер'] = markup_df['Оригинальный номер'].astype(str)

        sales_df = pd.read_excel(sales_xlsx)
        sales_df['Артикул'] = sales_df['Артикул'].astype(str)

        self.merged_df = pd.merge(goods_exclude_df, markup_df, left_on='Артикул',
                                  right_on='Оригинальный номер', how='left')
        self.merged_df = pd.merge(self.merged_df, sales_df, on='Артикул', how='left')

        self.merged_df['Result'] = (self.merged_df["Рассчитанная цена для участия в акции, RUB"] - self.merged_df["Общая комиссия"]) * 100 / self.merged_df["Среднезакупочная"]

        logger.info(f"Всего строк {self.merged_df.shape[0]}.\n")

    def get_brands(self):
        return self.merged_df["Бренд"].unique()

    def get_items(self):
        return self.merged_df["Категория"].unique()

    def get_article(self):
        return self.merged_df["Артикул"].unique()

    def remove_by_percentage_order_limit(self, percentage: int, order_limit:int):
        check_article = ~self.merged_df['Артикул'].isin(self.required_article)
        check_percentage = self.merged_df['Result'] > percentage
        check_order_limit = self.merged_df['Заказано товаров'] <= order_limit
        self.required_limit_order = order_limit
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_order_limit)]
        logger.info(f"Вы убрали товары по проценту наценки после скидки и по количеству заказов. Осталось {self.merged_df.shape[0]} строк.\n")

    # def remove_by_order_limit(self, order_limit: int):
    #     check_article = ~self.merged_df['Артикул поставщика'].isin(self.required_article)
    #     check_order_limit = self.merged_df['Заказали, шт'] < order_limit
    #     self.merged_df = self.merged_df[~(check_article | check_order_limit)]
    #     logger.info(f"Вы убрали товары по количеству заказов. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_brand(self, percentage: int, brand: str):
        check_article = ~self.merged_df['Артикул'].isin(self.required_article)
        check_percentage = self.merged_df['Result'] > percentage
        check_order_limit = self.merged_df['Заказано товаров'] <= self.required_limit_order
        check_brand = self.merged_df["Бренд"] == brand
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_brand & check_order_limit)]
        logger.info(f"Вы убрали строки по бренду {brand}. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_category(self, percentage: int, category: str):
        check_article = ~self.merged_df['Артикул'].isin(self.required_article)
        check_order_limit = self.merged_df['Заказано товаров'] <= self.required_limit_order
        check_percentage = self.merged_df['Result'] > percentage
        check_category = self.merged_df["Категория"] == category
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_category & check_order_limit)]
        logger.info(f"Вы убрали строки по категории {category}. Осталось {self.merged_df.shape[0]} строк.\n")

    def download_excel(self):
        articles = self.merged_df["Артикул"].tolist()
        date = self.name_sheets.split(" ")[1]
        tmp = self.second_table.copy()
        tmp["Участие товара в акции с " + date] = tmp.apply(
            lambda row: "Да*" if row["Артикул"] in articles else "", axis=1
        )
        columns_to_drop = ['Unnamed: 19', 'Unnamed: 20', 'Unnamed: 21',
                           'Unnamed: 22', 'Unnamed: 23', 'Unnamed: 24',
                           'Unnamed: 25', 'Unnamed: 26', 'Unnamed: 27',
                           'Unnamed: 28', 'Unnamed: 29']

        tmp.drop(columns=columns_to_drop, inplace=True)
        # tmp = tmp.filter(items=self.required_headers)

        output_buffer_xlsx = io.BytesIO()
        with pd.ExcelWriter(output_buffer_xlsx, engine='xlsxwriter') as writer:
            self.first_sheets.to_excel(writer, sheet_name="Описание", index=False)
            self.second_header.to_excel(writer, sheet_name=self.name_sheets, index=False, startrow=0)
            tmp.to_excel(writer, index=False, sheet_name=self.name_sheets, startrow=len(self.second_header) + 1)

        return output_buffer_xlsx.getvalue()

    def get_logs(self):
        return self.log_stream.getvalue()

    def save_article(self, article: str):
        self.required_article.append(article.strip())
        logger.info(f"Вы убрали из акции артикул {article}. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_article(self, article: str):
        self.merged_df = self.merged_df[self.merged_df["Артикул"] != article]
        logger.info(f"Вы добавили в акцию артикул {article}. Осталось {self.merged_df.shape[0]} строк.\n")

