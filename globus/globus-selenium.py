import os
import argparse
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.options import Options
import json
from datetime import datetime
import time
import sys

# Конфигурация
BASE_URL = "https://lk.globusenergo.ru/"
LOGIN_URL = f"{BASE_URL}"  # Главная страница (возможно форма входа здесь)
PERSONAL_INFO_URL = f"{BASE_URL}personal/info/"

# Папка для отладочных данных
DEBUG_DIR = "debug_data"
os.makedirs(DEBUG_DIR, exist_ok=True)

def main(login, password):
     #driver = init_driver_windows()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    account_info = {}
    meters_data = []
    
    try:
        # 1. Переходим на страницу входа
        print(f"⌛ Загружаю страницу входа: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Проверяем фактический URL после загрузки
        current_url = driver.current_url
        print(f"✓ Текущий URL: {current_url}")
        
        # 2. Находим и заполняем форму
        find_and_fill_form(driver, login, password)

        # 3. Проверяем успешность входа
        try:
            WebDriverWait(driver, 15).until(
                lambda d: "personal" in d.current_url.lower() or "account" in d.current_url.lower()
            )
            print("✓ Успешная авторизация!")
        except:
            save_debug_data(driver, "auth_failed")
            # Дополнительная проверка на случай, если ошибка не была поймана ранее
            error_message = check_login_errors(driver)
            if error_message:
                raise ValueError(f"Ошибка авторизации: {error_message}")
            else:
                raise ValueError("Не удалось войти в личный кабинет (неизвестная ошибка)")

        # 4. Переходим на страницу с информацией
        print(f"⌛ Перехожу на страницу информации: {PERSONAL_INFO_URL}")
        driver.get(PERSONAL_INFO_URL)
        
        # 5. Парсим данные
        try:
            print("⌛ Ищу информацию о лицевом счете...")
            account_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "personal-account")))
            
            account_number = account_element.find_element(By.CLASS_NAME, "personal-account__number").text.strip()
            debt = account_element.find_element(By.CLASS_NAME, "personal-account__debt").text.strip()
            address = account_element.find_element(By.CLASS_NAME, "personal-account__address").text.strip()
            
            # Определяем тип суммы (задолженность или переплата)
            # Удаляем валютные символы и оставляем только числовое значение
            debt_clean = debt.replace(' ', '').replace(',', '.').replace('руб.', '').replace('₽', '')
            debt_type = "Переплата" if float(debt_clean) < 0 else "Задолженность"
            
            account_info = {
                "number": account_number,
                "debt": debt,
                "debt_type": debt_type,
                "address": address
            }
            
            print("✓ Данные лицевого счета получены")
            
        except Exception as e:
            save_debug_data(driver, "parsing_error")
            raise ValueError(f"Ошибка при получении данных ЛС: {str(e)}")
        
        # Получаем данные счетчиков
        try:
            meters_data = get_meter_data(driver)
        except Exception as e:
            print(f"Ошибка при получении данных счетчиков: {str(e)}")

        # Выводим результаты
        display_results(account_info, meters_data)

    except Exception as e:
        print(f"\nCritical error: {str(e)}")
        # Если ошибка произошла не на этапе парсинга, сохраняем данные
        if "parsing_error" not in str(e):
            save_debug_data(driver, "unexpected_error")
    finally:
        driver.quit()
        print("\nЗавершение работы скрипта")


def save_debug_data(driver, prefix):
    """Сохраняет скриншот и исходный код страницы для отладки."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(DEBUG_DIR, f"{prefix}_{timestamp}.png")
    html_path = os.path.join(DEBUG_DIR, f"{prefix}_{timestamp}.html")
    
    driver.save_screenshot(screenshot_path)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    
    print(f"Debug data saved: {screenshot_path}, {html_path}")

def init_driver_windows():
    """Инициализирует WebDriver для Windows с оптимальными настройками."""
    chrome_options = Options()
    
    # Основные настройки
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    
    # Опции для обхода детекта автоматизации
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Настройки для стабильной работы
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        # Для Chrome
        # driver = webdriver.Chrome(ChromeDriverManager().install())  # Запросенная строка
        
        # Используем ChromeDriver по указанному пути
        chrome_driver_path = r"..\..\chromedriver-win64\chromedriver.exe"
        print(f"✓ Используем ChromeDriver по пути: {chrome_driver_path}")
        
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Скрываем признаки автоматизации
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {},
                };
            """
        })
        
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {str(e)}")
        sys.exit(1)

def find_and_fill_form(driver, login, password):
    """Находит и заполняет форму входа."""
    print("⌛ Поиск формы входа...")
    
    try:
        # Поиск формы по классу с явным ожиданием
        form = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "auth__form"))
        )
        print("✓ Форма найдена")
        
        # Прокрутка к форме для уверенности
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", form)
        time.sleep(1)  # Краткая пауза для завершения прокрутки
        
        # Поиск полей ввода с явным ожиданием кликабельности
        # login_field = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='USER_LOGIN']"))
        # )
        # password_field = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='USER_PASSWORD']"))
        # )

         # Поиск полей ввода
        login_field = form.find_element(By.CSS_SELECTOR, "input[name='USER_LOGIN']")
        password_field = form.find_element(By.CSS_SELECTOR, "input[name='USER_PASSWORD']")
        remember_checkbox = form.find_element(By.CSS_SELECTOR, "input[name='USER_REMEMBER']")
        submit_button = form.find_element(By.CSS_SELECTOR, "input.auth__button[type='submit']")
        
        
        # Заполнение полей
        print("⌛ Заполняю поля формы...")
        login_field.clear()
        login_field.send_keys(login)
        print(f"✓ Введен логин: {login}")
        
        password_field.clear()
        password_field.send_keys(password)
        print(f"✓ Введен пароль: {'*' * len(password)}")
        
        # Ожидание и клик по чекбоксу через JavaScript для надежности
        remember_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='USER_REMEMBER']"))
        )
        driver.execute_script("arguments[0].click();", remember_checkbox)
        print("✓ Чекбокс 'Запомнить меня' отмечен")
        
        # Ожидание и клик по кнопке через JavaScript
        submit_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.auth__button[type='submit']"))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        print("✓ Форма отправлена")
        
    except Exception as e:
        save_debug_data(driver, "form_fill_error")
        raise ValueError(f"Ошибка при заполнении формы: {str(e)}")
    
def check_login_errors(driver):
    """Проверяет наличие сообщений об ошибках при входе."""
    try:
        # Ждем появления блока с ошибкой (с учетом того, что он может быть скрыт)
        error_block = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.block-auth-form__error")))
        
        # Проверяем, что блок видимый и содержит конкретную ошибку
        if error_block.is_displayed():
            error_text = error_block.text.strip()
            
            # Точная проверка текста ошибки
            if "Неверный логин или пароль" in error_text:
                return "Неверный логин или пароль"
            elif error_text:  # Любая другая ошибка
                return error_text
                
    except Exception as e:
        # Если элемент не найден или другие ошибки - считаем что ошибки нет
        pass
    
    return None 

def get_meter_data(driver):
    """Получает данные счетчиков с страницы /personal/meters/"""
    METERS_URL = "https://lk.globusenergo.ru/personal/meters/"
    
    try:
        print(f"⌛ Перехожу на страницу счетчиков: {METERS_URL}")
        driver.get(METERS_URL)
        
        # Сохраняем скриншот для отладки
        save_debug_data(driver, "meters_page_load")
        
        # Ожидаем загрузки основной таблицы
        print("⌛ Ожидаем загрузки таблицы счетчиков...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.meters")))
        
        # Получаем HTML страницы для анализа
        page_source = driver.page_source
        print(f"✓ Страница счетчиков загружена. Длина HTML: {len(page_source)} символов")
        
        print("⌛ Получаю данные счетчиков...")
        
        # Находим все строки с данными счетчиков
        meter_rows = driver.find_elements(By.CSS_SELECTOR, "div.table1__row.table1__pos")
        print(f"ℹ Найдено {len(meter_rows)} строк с счетчиками")
        
        meters_data = []
        
        for i, row in enumerate(meter_rows):
            try:
                print(f"🔍 Обрабатываю счетчик {i+1}/{len(meter_rows)}")
                
                # Извлекаем название счетчика
                try:
                    name_element = row.find_element(By.CSS_SELECTOR, "div.meters__name.table__align")
                    name = name_element.text.strip()
                    print(f"  ✓ Название счетчика: {name}")
                except Exception as e:
                    print(f"  ⚠ Не удалось найти название счетчика: {str(e)}")
                    name = f"Счетчик {i+1}"
                
                # Получаем предыдущие показания
                try:
                    # Ищем элемент с классом prev_value_input156812 (динамический номер)
                    prev_reading_input = row.find_element(By.CSS_SELECTOR, "input.meters__input[readonly]")
                    previous_reading = prev_reading_input.get_attribute("value").strip()
                    print(f"  ✓ Предыдущие показания: {previous_reading}")
                except Exception as e:
                    print(f"  ⚠ Не удалось найти предыдущие показания: {str(e)}")
                    previous_reading = "N/A"
                
                # Получаем текущие показания (поле для ввода)
                try:
                    # Ищем элемент с классом check__input и data-meterid
                    current_reading_input = row.find_element(By.CSS_SELECTOR, "input.check__input[data-meterid]")
                    current_reading = current_reading_input.get_attribute("value").strip()
                    print(f"  ✓ Текущие показания: {current_reading}")
                except Exception as e:
                    print(f"  ⚠ Не удалось найти текущие показания: {str(e)}")
                    current_reading = "N/A"
                
                # Извлекаем дополнительную информацию (даты и ссылки)
                try:
                    additional_info_div = row.find_element(By.CSS_SELECTOR, "div.meters__theme-title.padding-default.table__align")
                    additional_info_elements = additional_info_div.find_elements(By.CSS_SELECTOR, "div.table1__date b")
                    
                    additional_info = ""
                    if additional_info_elements:
                        dates_info = []
                        for date_elem in additional_info_elements:
                            date_text = date_elem.text.strip()
                            # Найдем текст перед датой
                            parent = date_elem.find_element(By.XPATH, "..")
                            full_text = parent.text.strip()
                            dates_info.append(full_text)
                            print(f"  ✓ Найдена дата: {full_text}")
                        additional_info = " | ".join(dates_info)
                    
                    # Добавляем ссылку на историю
                    try:
                        history_link = row.find_element(By.CSS_SELECTOR, "a[href*='type=history']")
                        history_text = history_link.text.strip()
                        print(f"  ✓ Ссылка на историю: {history_text}")
                        if additional_info:
                            additional_info += f" | {history_text}"
                        else:
                            additional_info = history_text
                    except Exception as e:
                        print(f"  ℹ Ссылка на историю не найдена: {str(e)}")
                    
                    print(f"  ✓ Дополнительная информация: {additional_info}")
                except Exception as e:
                    print(f"  ⚠ Ошибка при получении дополнительной информации: {str(e)}")
                    additional_info = "N/A"
                
                meter_data = {
                    "name": name,
                    "previous_reading": previous_reading,
                    "current_reading": current_reading,
                    "additional_info": additional_info
                }
                
                print(f"  ✓ Счетчик {i+1} обработан успешно: {meter_data}")
                meters_data.append(meter_data)
                
            except Exception as e:
                print(f"⚠ Ошибка при парсинге строки счетчика {i+1}: {str(e)}")
                continue
        
        if not meters_data:
            print("ℹ На странице не найдено данных счетчиков")
            return None
        
        print(f"✓ Успешно получены данные {len(meters_data)} счетчиков")
        for i, meter in enumerate(meters_data):
            print(f"  Счетчик {i+1}: {meter['name']} - Предыдущие: {meter['previous_reading']}, Текущие: {meter['current_reading']}")
        
        return meters_data
        
    except Exception as e:
        print(f"❌ Фатальная ошибка при получении данных счетчиков: {str(e)}")
        save_debug_data(driver, "meter_data_error")
        raise ValueError(f"Ошибка при получении данных счетчиков: {str(e)}")

def parse_arguments():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description='Автоматизированная авторизация в личный кабинет Globus Energo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python globus-selenium.py --login mylogin --password mypass
  python globus-selenium.py -l user123 -p secret123
        """
    )
    
    parser.add_argument(
        '-l', '--login',
        type=str,
        required=True,
        help='Логин для авторизации в личном кабинете'
    )
    
    parser.add_argument(
        '-p', '--password',
        type=str,
        required=True,
        help='Пароль для авторизации в личном кабинете'
    )
    
    return parser.parse_args()

def format_date_info(additional_info):
    """Извлекает и форматирует даты из дополнительной информации."""
    import re
    
    # Ищем дату последнего показания
    last_reading_match = re.search(r'Дата ввода последнего показания\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})', additional_info)
    verification_match = re.search(r'Дата следующей поверки\s+(\d{2}\.\d{2}\.\d{4})', additional_info)
    
    result = {}
    
    if last_reading_match:
        last_reading_date = datetime.strptime(last_reading_match.group(1), '%d.%m.%Y %H:%M:%S')
        result['last_reading_date'] = last_reading_date
        # Рассчитываем количество дней назад
        now = datetime.now()
        days_ago = (now - last_reading_date).days
        result['days_ago'] = days_ago
    
    if verification_match:
        verification_date = datetime.strptime(verification_match.group(1), '%d.%m.%Y')
        result['verification_date'] = verification_date
        
        # Рассчитываем количество месяцев до поверки
        now = datetime.now()
        if verification_date > now:
            # Разница в месяцах
            months_remaining = (verification_date.year - now.year) * 12 + (verification_date.month - now.month)
            # Если день месяца verification_date меньше текущего дня, уменьшаем на 1
            if verification_date.day < now.day:
                months_remaining -= 1
            # Обеспечиваем, что months_remaining не будет отрицательным
            months_remaining = max(0, months_remaining)
            result['months_remaining'] = months_remaining
        else:
            result['months_remaining'] = 0
    
    return result

def display_results(account_info, meters_data):
    """Форматирует и выводит результаты в JSON и текстовом формате."""
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ПАРСИНГА")
    print("="*60)
    
    # Определяем тип суммы (задолженность или переплата) для JSON
    debt_value = account_info.get('debt', 'N/A')
    if debt_value != 'N/A':
        try:
            debt_num = float(debt_value.replace(' ', '').replace(',', '.').replace('руб.', '').replace('₽', ''))
            debt_type = "Переплата" if debt_num < 0 else "Задолженность"
        except:
            debt_type = "Задолженность"
    else:
        debt_type = "Задолженность"
    
    # Подготовка данных для JSON
    result_data = {
        "account_info": {
            "number": account_info.get('number', 'N/A'),
            "debt": debt_value,
            "debt_type": debt_type,
            "address": account_info.get('address', 'N/A')
        },
        "meters": []
    }
    
    # Форматируем информацию о лицевом счете
    # Определяем тип суммы (задолженность или переплата)
    debt_value = account_info.get('debt', 'N/A')
    if debt_value != 'N/A':
        try:
            debt_num = float(debt_value.replace(' ', '').replace(',', '.').replace('руб.', '').replace('₽', ''))
            debt_type = "Переплата" if debt_num < 0 else "Задолженность"
        except:
            debt_type = "Задолженность"
    else:
        debt_type = "Задолженность"
    
    print(f"\nЛицевой счет: {account_info.get('number', 'N/A')}")
    print(f"• {debt_type}: {debt_value}")
    print(f"• Адрес: {account_info.get('address', 'N/A')}")
    
    # Обрабатываем данные счетчиков
    if meters_data:
        for meter in meters_data:
            meter_result = {
                "name": meter['name'],
                "previous_reading": meter['previous_reading'],
                "current_reading": meter['current_reading']
            }
            
            # Извлекаем информацию о датах
            date_info = format_date_info(meter['additional_info'])
            
            print(f"\nНазвание счетчика: {meter['name']}")
            print(f"  ✓ Предыдущие показания: {meter['previous_reading']}")
            
            if 'last_reading_date' in date_info:
                last_date = date_info['last_reading_date'].strftime('%d.%m.%Y %H:%M:%S')
                days_ago = date_info['days_ago']
                print(f"  ✓ Дата передачи: {last_date} ({days_ago} дней назад)")
                meter_result["last_reading_date"] = last_date
                meter_result["days_ago"] = days_ago
            else:
                print(f"  ✓ Дата передачи: неизвестно")
                meter_result["last_reading_date"] = None
                meter_result["days_ago"] = None
            
            if 'verification_date' in date_info:
                verification_date = date_info['verification_date'].strftime('%d.%m.%Y')
                months_remaining = date_info.get('months_remaining', 0)
                print(f"  ✓ Дата поверки: {verification_date} (осталось {months_remaining} месяцев)")
                meter_result["verification_date"] = verification_date
                meter_result["months_remaining"] = months_remaining
            else:
                print(f"  ✓ Дата поверки: неизвестно")
                meter_result["verification_date"] = None
                meter_result["months_remaining"] = None
            
            meter_result["additional_info"] = meter['additional_info']
            result_data["meters"].append(meter_result)
    
    # Выводим JSON
    print("\n" + "="*60)
    print("JSON ФОРМАТ:")
    print("="*60)
    print(json.dumps(result_data, ensure_ascii=False, indent=2))
    
    print("\n" + "="*60)
    print("ТЕКСТОВЫЙ ФОРМАТ:")
    print("="*60)
    
    # Определяем тип суммы (задолженность или переплата)
    debt_value = account_info.get('debt', 'N/A')
    if debt_value != 'N/A':
        try:
            debt_num = float(debt_value.replace(' ', '').replace(',', '.').replace('руб.', '').replace('₽', ''))
            debt_type = "Переплата" if debt_num < 0 else "Задолженность"
        except:
            debt_type = "Задолженность"
    else:
        debt_type = "Задолженность"
    
    print(f"Лицевой счет: {account_info.get('number', 'N/A')}")
    print(f"{debt_type}: {debt_value}")
    print(f"Адрес: {account_info.get('address', 'N/A')}")
    
    if meters_data:
        for i, meter in enumerate(meters_data, 1):
            print(f"\n{i}. {meter['name']}")
            print(f"   Предыдущие показания: {meter['previous_reading']}")
            date_info = format_date_info(meter['additional_info'])
            if 'last_reading_date' in date_info:
                last_date = date_info['last_reading_date'].strftime('%d.%m.%Y %H:%M:%S')
                days_ago = date_info['days_ago']
                print(f"   Дата передачи: {last_date} ({days_ago} дней назад)")
            if 'verification_date' in date_info:
                verification_date = date_info['verification_date'].strftime('%d.%m.%Y')
                months_remaining = date_info.get('months_remaining', 0)
                print(f"   Дата поверки: {verification_date} (осталось {months_remaining} месяцев)")


if __name__ == "__main__":
    args = parse_arguments()
    main(args.login, args.password)