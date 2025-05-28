import json
import logging
import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('logs/utils.log', mode='w')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)


def reading_json_file(path: str) -> list[dict]:
    """Функция, которая принимает на вход путь до JSON-файла
    и возвращает список словарей с пользовательскими параметрами"""
    try:
        logger.info('Попытка открыть JSON-файл')
        with open(path, encoding='utf-8') as f:
            lst = json.load(f)
        if not isinstance(lst, list) or not lst:
            logger.warning('Проблема с содержимым JSON-файла')
            return []
        else:
            return lst
    except FileNotFoundError:
        logger.warning('Возможна проблема с путем до JSON-файла')
        return []


def reading_xlsx(path: str) -> pd.DataFrame:
    """Функция, которая принимает на вход путь до XLSX-файла
        и возвращает датафрейм по операциям."""
    try:
        fieldnames = {'Дата операции': str, 'Номер карты': str,
                      'Статус': str, 'Сумма операции': float, 'Валюта операции': str,
                      'Сумма платежа': float, 'Валюта платежа': str,
                      'Категория': str, 'Описание': str}
        df = pd.read_excel(path, decimal=';', dtype=fieldnames)[['Дата операции',
                                                                 'Номер карты',
                                                                 'Статус',
                                                                 'Сумма операции',
                                                                 'Валюта операции',
                                                                 'Сумма платежа',
                                                                 'Валюта платежа',
                                                                 'Категория',
                                                                 'Описание']]
        df['Дата операции'] = pd.to_datetime(df['Дата операции'], dayfirst=True)
        return df
    except FileNotFoundError:
        return pd.DataFrame()


def df_to_transactions(lst: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Функция, которая возвращает список для дальнейших работ с ним."""
    df = pd.DataFrame(lst)
    df_expanse = df[(df['Статус'] == 'OK')
                    & (df['Сумма платежа'] <= 0)
                    & (df['Валюта операции'] != 'RUB')
                    & (df['Валюта платежа'] == 'RUB')].\
        groupby(['Дата операции'], as_index=False). \
        agg({'Сумма платежа': 'sum'}). \
        rename(columns={'Сумма платежа': 'Сумма операции'})
    df_operation = df[(df['Статус'] == 'OK')
                      & (df['Сумма операции'] <= 0)
                      & (df['Валюта платежа'] != 'RUB')
                      & (df['Валюта операции'] == 'RUB')].\
        groupby(['Дата операции'], as_index=False).\
        agg({'Сумма операции': 'sum'})
    df_operation_2 = df[(df['Статус'] == 'OK')
                        & (df['Сумма операции'] <= 0)
                        & (df['Валюта платежа'] == 'RUB')
                        & (df['Валюта операции'] == 'RUB')].\
        groupby(['Дата операции'], as_index=False).\
        agg({'Сумма операции': 'sum'})

    df = pd.concat([df_expanse, df_operation, df_operation_2])
    df = df.groupby(['Дата операции'], as_index=False).agg({'Сумма операции': 'sum'})
    transactions = df.to_dict('records')
    return transactions


def external_api_marketstack() -> list[dict]:
    """Функция для получения последних имеющихся цен на акции"""
    load_dotenv()
    apikey = os.getenv('API_KEY_MARKETSTACK')
    user_stocks = reading_json_file("user_settings.json")[0]['user_stocks']
    lst = []
    try:
        logger.info('Попытка подключения через API к сайту со стоимостью акций')
        for i in user_stocks:
            url = f"http://api.marketstack.com/v1/intraday?access_key={apikey}&symbols={i}&sort=DESC&limit=1"
            response = requests.get(url)
            dct = {"stock": i, "price": response.json()['data'][0]['close']}
            logger.info('Успешное подключение через API к сайту со стоимостью акций')
            lst.append(dct)
        return lst
    except requests.exceptions.RequestException:
        logger.warning('Возможна проблема с подключением через API к сайту со стоимостью акций')


def external_api_currency() -> list[dict]:
    """Функция для получения текущего курса валют"""
    load_dotenv()
    apikey = os.getenv('API_KEY_CURRENCY')
    headers = {
        "apikey": f"{apikey}"
    }
    user_currencies = reading_json_file("user_settings.json")[0]['user_currencies']
    lst = []
    try:
        for i in user_currencies:
            logger.info('Попытка подключения через API к сайту с курсом валют')
            url = f"https://api.apilayer.com/exchangerates_data/convert?to=RUB&from={i}&amount=1"
            response = requests.get(url, headers=headers)
            dct = {"currency": i, "rate": response.json()['info']['rate']}
            lst.append(dct)
            logger.info('Успешное подключение через API к сайту с курсом валют')
        return lst
    except requests.exceptions.RequestException:
        logger.warning('Возможна проблема с подключением через API к сайту с курсом валют')