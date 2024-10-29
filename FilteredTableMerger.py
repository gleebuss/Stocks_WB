import io

import pandas as pd
from loguru import logger

class FilteredTableMerger:
    def __init__(self, sales_xlsx, markup_xlsx, goods_exclude_xlsx):
        self.required_article = []
        self.required_limit_order = 0

        self.log_stream = io.StringIO()
        logger.add(self.log_stream, format="{message}")

        goods_exclude_data = pd.read_excel(goods_exclude_xlsx, sheet_name=None)
        goods_exclude_sheet = list(goods_exclude_data.keys())[0]
        goods_exclude_df = goods_exclude_data[goods_exclude_sheet]
        self.required_headers = goods_exclude_df.columns.tolist()

        markup_data = pd.read_excel(markup_xlsx, sheet_name=None, header=1)
        markup_sheet = list(markup_data.keys())[0]
        markup_df = markup_data[markup_sheet]
        markup_df = markup_df.drop(columns=["Наименование"])

        sales_data = pd.read_excel(sales_xlsx, sheet_name="Товары", header=1)
        sales_columns = [col for col in list(sales_data.keys()) if col in ["Артикул продавца", "Заказали, шт"]]
        sales_df = sales_data[sales_columns]

        self.merged_df = pd.merge(goods_exclude_df, markup_df, left_on='Артикул поставщика',
                                  right_on='Оригинальный номер', how='left')
        self.merged_df = pd.merge(self.merged_df, sales_df, left_on='Артикул поставщика', right_on='Артикул продавца',
                                  how='left')

        self.merged_df['Result'] = ((self.merged_df['Цена продажи'] -
                                     (self.merged_df['Среднезакупочная'] + self.merged_df['Комиссия без скидки'] +
                                      (self.merged_df['Цена продажи'] * self.merged_df[
                                          'Загружаемая скидка для участия в акции'] / 100))
                                     ) / self.merged_df['Среднезакупочная']) * 100

        logger.info(f"Всего строк {self.merged_df.shape[0]}.\n")

    def get_brands(self):
        return self.merged_df["Бренд"].unique()

    def get_items(self):
        return self.merged_df["Предмет"].unique()

    def get_article(self):
        return self.merged_df["Артикул поставщика"].unique()

    def remove_by_percentage_order_limit(self, percentage: int, order_limit:int):
        check_article = ~self.merged_df['Артикул поставщика'].isin(self.required_article)
        check_percentage = self.merged_df['Result'] > percentage
        check_order_limit = self.merged_df['Заказали, шт'] <= order_limit
        self.required_limit_order = order_limit
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_order_limit)]
        logger.info(f"Вы убрали товары по проценту наценки после скидки и по количеству заказов. Осталось {self.merged_df.shape[0]} строк.\n")

    # def remove_by_order_limit(self, order_limit: int):
    #     check_article = ~self.merged_df['Артикул поставщика'].isin(self.required_article)
    #     check_order_limit = self.merged_df['Заказали, шт'] < order_limit
    #     self.merged_df = self.merged_df[~(check_article | check_order_limit)]
    #     logger.info(f"Вы убрали товары по количеству заказов. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_brand(self, percentage: int, brand: str):
        check_article = ~self.merged_df['Артикул поставщика'].isin(self.required_article)
        check_percentage = self.merged_df['Result'] > percentage
        check_order_limit = self.merged_df['Заказали, шт'] <= self.required_limit_order
        check_brand = self.merged_df["Бренд"] == brand
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_brand & check_order_limit)]
        logger.info(f"Вы убрали строки по бренду {brand}. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_category(self, percentage: int, category: str):
        check_article = ~self.merged_df['Артикул поставщика'].isin(self.required_article)
        check_order_limit = self.merged_df['Заказали, шт'] <= self.required_limit_order
        check_percentage = self.merged_df['Result'] > percentage
        check_category = self.merged_df["Предмет"] == category
        self.merged_df = self.merged_df[~(check_article & check_percentage & check_category & check_order_limit)]
        logger.info(f"Вы убрали строки по категории {category}. Осталось {self.merged_df.shape[0]} строк.\n")

    def download_excel(self):
        tmp = self.merged_df.copy()
        tmp = tmp.filter(items=self.required_headers)

        output_buffer_xlsx = io.BytesIO()
        with pd.ExcelWriter(output_buffer_xlsx, engine='xlsxwriter') as writer:
            tmp.to_excel(writer, index=False, sheet_name='Sheet1')

        return output_buffer_xlsx.getvalue()

    def get_logs(self):
        return self.log_stream.getvalue()

    def save_article(self, article: str):
        self.required_article.append(article.strip())
        logger.info(f"Вы убрали из акции артикул {article}. Осталось {self.merged_df.shape[0]} строк.\n")

    def remove_by_article(self, article: str):
        self.merged_df = self.merged_df[self.merged_df["Артикул поставщика"] != article]
        logger.info(f"Вы добавили в акцию артикул {article}. Осталось {self.merged_df.shape[0]} строк.\n")

