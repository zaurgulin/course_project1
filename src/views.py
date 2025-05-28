import json
from datetime import datetime

import pandas as pd

from src.utils import external_api_currency, external_api_marketstack, reading_xlsx


def changing_df(path: str, date: str) -> pd.DataFrame:
    """Функция, которая возвращает датафрейм для дальнейших работ с ним."""
    df = reading_xlsx(path=path)
    date = pd.to_datetime(date, dayfirst=False)
    df = df[(df['Дата операции'] >= date.replace(day=1)) & (df['Дата операции'] <= date)]
    return df


def each_card(path: str, date: str) -> list[dict]:
    """Функция, которая возвращает список словарей с данными о картах и затратах по ним."""
    df = changing_df(path=path, date=date)
    if len(df) == 0:
        return []
    else:
        df_expanse = df[(df['Статус'] == 'OK')
                        & (df['Сумма платежа'] <= 0)
                        & (df['Валюта операции'] != 'RUB')
                        & (df['Валюта платежа'] == 'RUB')].\
            groupby(['Номер карты'], as_index=False).\
            agg({'Сумма платежа': 'sum'}).\
            rename(columns={'Сумма платежа': 'Сумма операции'})
        df_operation = df[(df['Статус'] == 'OK')
                          & (df['Сумма операции'] <= 0)
                          & (df['Валюта платежа'] != 'RUB')
                          & (df['Валюта операции'] == 'RUB')].\
            groupby(['Номер карты'], as_index=False).\
            agg({'Сумма операции': 'sum'})
        df_operation_2 = df[(df['Статус'] == 'OK')
                            & (df['Сумма операции'] <= 0)
                            & (df['Валюта платежа'] == 'RUB')
                            & (df['Валюта операции'] == 'RUB')].\
            groupby(['Номер карты'], as_index=False).\
            agg({'Сумма операции': 'sum'})

        df = pd.concat([df_expanse, df_operation, df_operation_2])
        df = df.groupby(['Номер карты'], as_index=False).agg({'Сумма операции': 'sum'})
        df['last_digits'] = df['Номер карты'].str[1:]
        df['total_spent'] = abs(df['Сумма операции'])
        df['cashback'] = abs(round(df['total_spent'] / 100, 2))
        df = df.drop(columns={'Сумма операции', 'Номер карты'})
        return df.to_dict('records')


def top_transactions(path: str, date: str) -> list[dict]:
    """Функция, которая возвращает список словарей с Топ-5 транзакций по сумме платежа."""
    df = changing_df(path=path, date=date)
    if len(df) == 0:
        return []
    else:
        df_expanse = df[(df['Статус'] == 'OK')
                        & (df['Валюта платежа'] == 'RUB')
                        & (df['Валюта операции'] != 'RUB')][['Дата операции',
                                                             'Сумма платежа', 'Категория', 'Описание']].\
            rename(columns={'Сумма платежа': 'Сумма операции'})
        df_operation = df[(df['Статус'] == 'OK')
                          & (df['Валюта платежа'] != 'RUB')
                          & (df['Валюта операции'] == 'RUB')][['Дата операции',
                                                               'Сумма операции', 'Категория', 'Описание']]
        df_operation_2 = df[(df['Статус'] == 'OK')
                            & (df['Валюта платежа'] == 'RUB')
                            & (df['Валюта операции'] == 'RUB')][['Дата операции',
                                                                 'Сумма операции', 'Категория', 'Описание']]

        df = pd.concat([df_expanse, df_operation, df_operation_2])
        df['Сумма операции'] = abs(df['Сумма операции'])
        df['Дата операции'] = df['Дата операции'].dt.strftime('%d.%m.%Y')
        df = df.sort_values('Сумма операции', ascending=False)[0:4]
        df = df.rename(columns={'Дата операции': 'date',
                                'Сумма операции': 'amount',
                                'Категория': 'category',
                                'Описание': 'description'})
        return df.to_dict('records')


def greetings() -> str:
    """Функция, которая возвращает строку с приветствием в зависимости от времени."""
    hour = int(datetime.now().strftime('%H'))
    if 6 <= hour <= 12:
        return 'Доброе утро'
    elif 13 <= hour <= 17:
        return 'Добрый день'
    elif 18 <= hour <= 23:
        return 'Добрый вечер'
    else:
        return 'Доброй ночи'


def views(path: str, date: str) -> json:
    """Функция, которая возвращает json с веб-страницей."""
    return json.dumps({'greetings': greetings(),
                       'cards''': each_card(path, date),
                       'top_transactions': top_transactions(path, date),
                       'currency_rates': external_api_currency(),
                       'stock_prices': external_api_marketstack()
                       }, ensure_ascii=False)