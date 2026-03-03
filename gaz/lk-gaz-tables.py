import os
import argparse
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import sys
import json
from datetime import datetime

# Конфигурация
BASE_URL = "https://xn--80afnfom.xn--80ahmohdapg.xn--80asehdb/auth/sign-in"
LOGIN_URL = f"{BASE_URL}"
METERS_URL = f"{BASE_URL}meters"

# Папка для отладочных данных
DEBUG_DIR = "debug_data"
os.makedirs(DEBUG_DIR, exist_ok=True)

def main(login, password):
     #driver = init_driver_windows()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    services_data = []
    meters_data = []
    
    try:
        # 1. Переходим на страницу входа
        print(f"⌛ Загружаю страницу входа: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Проверяем фактический URL after загрузки
        current_url = driver.current_url
        print(f"✓ Текущий URL: {current_url}")

        #1.1 проверка на информационную форму
        
        
        # 2. Находим and заполняем форму
        find_and_fill_form(driver, login, password)

        # Шаг 3: Проверка и пропуск обучающего диалога
        print("⌛ Проверяю наличие обучающего диалога...")
        skip_training_dialog(driver)

        # 3.1 Проверяем успешность входа
        try:
            print("⌛ Проверяю успешность авторизации...")
            
            # # Ждем редиректа на внутреннюю страницу или появления элементов авторизации
            # WebDriverWait(driver, 20).until(
            #     EC.any_of(
            #         EC.url_changes(driver.current_url),
            #         EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Газоснабжение природным газом')]"))
            #     )
            # )
            # print_ts("✓ Успешная авторизация!")
            
            # Проверяем наличие элементов после авторизации (если хотя бы один найден - успешно)
            auth_elements = [
                (By.XPATH, "//*[contains(text(), 'Газоснабжение природным газом')]"),
                (By.XPATH, "//*[contains(text(), 'Расчеты')]"),
                (By.XPATH, "//*[contains(text(), 'Приборы учета')]"),
            ]
            
            found_element = None
            for selector, by in auth_elements:
                try:
                    element = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    found_element = element
                    break
                except:
                    continue
            
            if found_element:
                print_ts(f"✓ Найдены элементы успешного входа после авторизации")
            else:
                print_ts("ℹ Элементы авторизации не найдены, но редирект произошёл")
            
            # Дополнительная проверка на конкретные элементы с slot="title"
            title_elements = [
                (By.XPATH, "//h3[@slot='title' and contains(., 'Расчеты')]"),
                (By.XPATH, "//h3[@slot='title' and contains(., 'Приборы учета')]"),
            ]
            
            title_found = False
            for selector, by in title_elements:
                try:
                    element = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    title_found = True
                    print_ts(f"✓ Найдён заголовок: {element.text.strip()}")
                    break
                except:
                    continue
            
            if not title_found:
                print_ts("ℹ Заголовки 'Расчеты' или 'Приборы учета' не найдены")
            
           
            
        except:
            save_debug_data(driver, "auth_failed")
            raise ValueError("Не удалось войти в личный кабинет")
        
        # 4. Сохраняем скриншот успешного входа
        print("⌛ Сохраняю скриншот успешного входа...")
        save_debug_data(driver, "successful_login")
        
        # 4.1. Извлекаем информацию об услугах с текущей страницы
        print("⌛ Извлекаем информацию об услугах с текущей страницы...")
        try:
            print("⌛ Сохраняю скриншот услуг...")
            save_debug_data(driver, "successful_services")
            services_data = get_services_info_from_current_page(driver)
            if services_data:
                print(f"✓ Успешно получены данные об услугах: {len(services_data)} записей")
            else:
                print("ℹ Данные об услугах not found на текущей странице")
        except Exception as e:
            print(f"⚠ Ошибка при получении information об услугах: {str(e)}")
        
        # 5. Переходим на страницу приборов учета
        try:
            print("⌛ Перехожу на страницу приборов учета...")
            driver.get(METERS_URL)
            
            # Ожидаем загрузки страницы
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Приборы учета') or contains(text(), 'Счетчики') or contains(text(), 'Метры')]"))
                )
                print("✓ Страница приборов учета загружена")
            except:
                print("ℹ Страница приборов учета загружена")
            
            # Сохраняем скриншот для отладки
            save_debug_data(driver, "meters_page")
            
            # Извлекаем данные о приборах учета
            meters_data = get_meters_info_from_current_page(driver)
            
            # Выводим все данные
            display_all_info(services_data, [], meters_data)
            
            return {
                "services": services_data,
                "meters": meters_data
            }
                
        except Exception as e:
            print(f"⚠ Ошибка при получении данных о приборах учета: {str(e)}")
            # Выводим данные об услугах, even if not удалось получить данные о счетчиках
            if services_data:
                display_all_info(services_data, [], [])
                return {"services": services_data, "meters": []}
            else:
                return None

    except Exception as e:
        print(f"\nCritical error: {str(e)}")
        save_debug_data(driver, "unexpected_error")
    finally:
        # Задержка перед закрытием для визуальной проверки
        print("\n⏳ Задержка 5 секунд для визуальной проверки...")
        time.sleep(5)
        driver.quit()
        print("\nЗавершение работы скрипта")


def print_ts(message):
    """Печатает сообщение с timestamp в миллисекундах."""
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

def save_debug_data(driver, prefix):
    """Сохраняет скриншот и исходный код страницы для отладки."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(DEBUG_DIR, f"{prefix}_{timestamp}.png")
    html_path = os.path.join(DEBUG_DIR, f"{prefix}_{timestamp}.html")
    
    driver.save_screenshot(screenshot_path)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    
    print_ts(f"Debug data saved: {screenshot_path}, {html_path}")

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
        # Используем ChromeDriver по указанному пути
        chrome_driver_path = r"e:\SOFT\chromedriver-win64\chromedriver.exe"
        print_ts(f"✓ Используем ChromeDriver по пути: {chrome_driver_path}")
        
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
        # Ожидаем загрузки страницы логина
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("✓ Страница входа загружена")
        
        # Шаг 1.1: Проверка и закрытие информационной формы
        print("⌛ Проверяю наличие информационной формы...")
        close_info_dialog(driver)
        
        # Ищем поле логина
        try:
            login_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            print_ts("✓ Найдено поле логина")
        except:
            raise ValueError("Поле логина not found")
        
        # Ищем поле пароля
        try:
            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            print_ts("✓ Найдено поле пароля")
        except:
            raise ValueError("Поле пароля not found")
        
        print_ts("✓ Поля ввода found")
        
        # Заполняем поля
        print_ts("⌛ Заполняю поля формы...")
        
        # Очищаем and заполняем поле логина
        login_field.clear()
        login_field.send_keys(login)
        print_ts(f"✓ Введен логин: {login}")
        
        # Очищаем and заполняем поле пароля
        password_field.clear()
        password_field.send_keys(password)
        print_ts(f"✓ Введен пароль: {'*' * len(password)}")
        
        # Ищем кнопку входа
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            driver.execute_script("arguments[0].click();", submit_button)
            print_ts("✓ Форма отправлена")
        except:
            # Пытаемся отправить Enter в поле пароля
            try:
                password_field.send_keys("\n")
                print_ts("✓ Форма отправлена (Enter в поле пароля)")
            except:
                raise ValueError("Не удалось отправить форму входа")
        
        # Ждем начала процесса авторизации
        try:
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.url_changes(driver.current_url),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, [class*='progress']"))
                )
            )
            print_ts("✓ Начался процесс авторизации")
        except:
            print_ts("ℹ Процесс авторизации not обнаружен")
        
        # Ждем перехода на следующую страницу
        try:
            WebDriverWait(driver, 15).until(
                EC.url_changes(driver.current_url)
            )
            print_ts("✓ Страница начала изменяться after отправки формы")
        except:
            print_ts("ℹ Страница not изменилась в течение ожидаемого времени")
        
    except Exception as e:
        save_debug_data(driver, "form_fill_error")
        raise ValueError(f"Ошибка при заполнении формы: {str(e)}")


def close_info_dialog(driver):
    """
    Проверяет наличие информационной формы и закрывает её.
    
    Информационная форма имеет:
    - data-dialog атрибут
    - data-card атрибут
    - Кнопку "Закрыть" с slot="close"
    """
    try:
        print("⌛ Проверяю наличие информационной формы...")
        
        # Ищем информационную форму по data-dialog атрибуту
        dialog = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-dialog]"))
        )
        print("✓ Найдена информационная форма")
        
        # Сохраняем скриншот перед закрытием
        save_debug_data(driver, "info_dialog_open")
        
        # Ищем кнопку закрытия
        close_button = driver.find_element(By.CSS_SELECTOR, "[slot='close']")
        if close_button.is_displayed():
            print("✓ Найдена кнопка 'Закрыть'")
            
            # Сохраняем скриншот с открытой формой
            save_debug_data(driver, "info_dialog_close_button")
            
            # Кликаем по кнопке закрытия
            driver.execute_script("arguments[0].click();", close_button)
            print("✓ Кликнул по кнопке 'Закрыть'")
            
            # Ждем закрытия диалога
            WebDriverWait(driver, 3).until(
                lambda d: not d.find_element(By.CSS_SELECTOR, "[data-dialog]").is_displayed() or True
            )
            print("✓ Информационная форма закрыта")
            
            # Сохраняем скриншот после закрытия
            save_debug_data(driver, "info_dialog_closed")
        else:
            print("ℹ Кнопка 'Закрыть' not found, форма может закрыться автоматически")
            
    except Exception as e:
        print(f"ℹ Не удалось обработать информационную форму: {str(e)}")
        # Не прерываем выполнение, если форма не найдена или не удалось её закрыть


def skip_training_dialog(driver):
    """
    Проверяет наличие обучающего диалога и пропускает его.
    
    Обучающий диалог имеет:
    - role="dialog" атрибут
    - Кнопку "Пропустить обучение" или кнопку закрытия
    """
    try:
        print("⌛ Проверяю наличие обучающего диалога...")
        
        # Ищем обучающий диалог по role="dialog"
        training_dialog = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
        )
        print("✓ Найдён обучающий диалог")
        
        # Сохраняем скриншот перед пропуском
        save_debug_data(driver, "training_dialog_open")
        
        # Вариант 1: Ищем кнопку "Пропустить обучение" по span внутри кнопки
        skip_button = None
        try:
            # Ищем кнопку, у которой есть span с текстом "Пропустить обучение"
            skip_button = driver.find_element(By.XPATH, "//button[contains(., 'Пропустить обучение')]")
            if skip_button.is_displayed():
                print("✓ Найдена кнопка 'Пропустить обучение'")
            else:
                print("ℹ Кнопка 'Пропустить обучение' не отображается")
        except:
            print("ℹ Кнопка 'Пропустить обучение' не найдена")
        
        # Вариант 2: Ищем кнопку закрытия (крестик) в диалоге
        if not skip_button:
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, "[aria-label*='закрыть'], [aria-label*='close'], [aria-label*='Закрыть']")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка закрытия диалога")
                    skip_button = close_button
            except:
                print("ℹ Кнопка закрытия диалога не найдена")
        
        # Вариант 2.5: Ищем кнопку с SVG иконкой закрытия (крестик)
        if not skip_button:
            try:
                # Ищем кнопку, содержащую SVG с путём закрытия (крестик)
                close_button = driver.find_element(By.XPATH, "//button[contains(., 'Пропустить обучение')]")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка с SVG иконкой закрытия")
                    skip_button = close_button
            except:
                print("ℹ Кнопка с SVG иконкой закрытия не найдена")
        
        # Вариант 2.6: Ищем кнопку по классу (Tailwind CSS классы)
        if not skip_button:
            try:
                # Ищем кнопку с классами, характерными для обучающего диалога
                close_button = driver.find_element(By.CSS_SELECTOR, ".w-full.h-10.px-2.space-x-1.text-white.rounded-inherit.outline-none.tap-highlight-none")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка по Tailwind классам")
                    skip_button = close_button
            except:
                print("ℹ Кнопка по Tailwind классам не найдена")
        
        # Вариант 2.7: Ищем кнопку по span с текстом внутри
        if not skip_button:
            try:
                # Ищем кнопку, у которой есть span с текстом "Пропустить обучение"
                close_button = driver.find_element(By.XPATH, "//button[span[contains(text(), 'Пропустить обучение')]]")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка по span с текстом")
                    skip_button = close_button
            except:
                print("ℹ Кнопка по span с текстом не найдена")
        
        # Вариант 2.8: Ищем кнопку по data-testid или data-атрибутам
        if not skip_button:
            try:
                # Ищем кнопку с data-testid или data-атрибутами, характерными для обучающего диалога
                close_button = driver.find_element(By.CSS_SELECTOR, "[data-testid*='training'], [data-testid*='tutorial'], [data-testid*='onboarding'], [data-testid*='dialog']")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка по data-testid")
                    skip_button = close_button
            except:
                print("ℹ Кнопка по data-testid не найдена")
        
        # Вариант 2.9: Ищем кнопку внутри диалога по role="button"
        if not skip_button:
            try:
                # Ищем кнопку внутри диалога с role="button"
                close_button = training_dialog.find_element(By.CSS_SELECTOR, "[role='button']")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка внутри диалога с role='button'")
                    skip_button = close_button
            except:
                print("ℹ Кнопка внутри диалога с role='button' не найдена")
        
        # Вариант 3: Ищем кнопку с текстом "Закрыть"
        if not skip_button:
            try:
                close_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Закрыть')]")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка 'Закрыть'")
                    skip_button = close_button
            except:
                print("ℹ Кнопка 'Закрыть' не найдена")
        
        # Вариант 4: Ищем кнопку с текстом "X" или крестик
        if not skip_button:
            try:
                close_button = driver.find_element(By.XPATH, "//button[contains(text(), 'X') or contains(text(), '×')]")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка 'X'")
                    skip_button = close_button
            except:
                print("ℹ Кнопка 'X' не найдена")
        
        # Вариант 5: Ищем кнопку с aria-label="Close"
        if not skip_button:
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, "[aria-label='Close']")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка с aria-label='Close'")
                    skip_button = close_button
            except:
                print("ℹ Кнопка с aria-label='Close' не найдена")
        
        # Вариант 6: Ищем кнопку с классом reactour__close-btn
        if not skip_button:
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, ".reactour__close-btn")
                if close_button.is_displayed():
                    print("✓ Найдена кнопка с классом reactour__close-btn")
                    skip_button = close_button
            except:
                print("ℹ Кнопка с классом reactour__close-btn не найдена")
        
        # Вариант 7: Ищем кнопку с текстом внутри диалога
        if not skip_button:
            try:
                dialog_buttons = training_dialog.find_elements(By.TAG_NAME, "button")
                if dialog_buttons:
                    print(f"✓ Найдено {len(dialog_buttons)} кнопок внутри диалога")
                    for btn in dialog_buttons:
                        if btn.is_displayed():
                            text = btn.text.strip()
                            print(f"  - Кнопка: '{text}'")
                            # Кликаем по кнопке, у которой есть текст
                            if text:
                                skip_button = btn
                                break
            except Exception as e:
                print(f"ℹ Не удалось найти кнопки внутри диалога: {str(e)}")
        
        # Вариант 8: Если ничего не нашли, используем JavaScript для закрытия диалога
        if not skip_button:
            try:
                print("ℹ Кнопки закрытия не найдены, пытаемся закрыть диалог через JavaScript")
                # Пытаемся найти и кликнуть по кнопке закрытия через JS
                close_buttons = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'] button")
                if close_buttons:
                    for btn in close_buttons:
                        if btn.is_displayed():
                            print(f"✓ Найдена кнопка через JS: '{btn.text.strip()}'")
                            driver.execute_script("arguments[0].click();", btn)
                            skip_button = btn
                            break
            except Exception as e:
                print(f"ℹ Не удалось закрыть диалог через JS: {str(e)}")
        
        # Если кнопка найдена - кликаем по ней
        if skip_button and skip_button.is_displayed():
            print("✓ Кликнул по кнопке закрытия диалога")
            save_debug_data(driver, "training_dialog_skip_button")
            driver.execute_script("arguments[0].click();", skip_button)
            
            # Ждем закрытия диалога
            try:
                WebDriverWait(driver, 3).until(
                    lambda d: not d.find_element(By.CSS_SELECTOR, "[role='dialog']").is_displayed() or True
                )
                print("✓ Обучающий диалог закрыт")
                save_debug_data(driver, "training_dialog_closed")
            except:
                print("ℹ Диалог, возможно, уже закрылся автоматически")
        else:
            print("ℹ Обучающий диалог не удалось закрыть")
            
    except Exception as e:
        print(f"ℹ Не удалось обработать обучающий диалог: {str(e)}")
        # Не прерываем выполнение, если диалог не найден или не удалось его пропустить


def get_services_info_from_current_page(driver):
    """Получает информацию об услугах с текущей страницы, извлекая данные из таблиц."""
    try:
        print_ts("⌛ Извлечение информации об услугах из таблиц...")
        
        services_data = []
        
        # Поиск таблиц на странице
        tables = driver.find_elements(By.TAG_NAME, "table")
        print_ts(f"Найдено {len(tables)} таблиц на странице")
        
        for table_index, table in enumerate(tables):
            if not table.is_displayed():
                continue
                
            try:
                print_ts(f"Анализирую таблицу {table_index + 1}")
                
                # Получаем все строки таблицы
                rows = table.find_elements(By.TAG_NAME, "tr")
                print_ts(f"Найдено {len(rows)} строк в таблице")
                
                for row_index, row in enumerate(rows):
                    if not row.is_displayed():
                        continue
                        
                    try:
                        # Получаем все ячейки в строке
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 0:
                            # Проверяем th элементы
                            cells = row.find_elements(By.TAG_NAME, "th")
                        
                        if len(cells) > 0:
                            print_ts(f"  Строка {row_index + 1}: найдено {len(cells)} ячеек")
                            
                            # Собираем текст из всех ячеек строки
                            row_text = ""
                            cell_data = []
                            for cell in cells:
                                if cell.is_displayed():
                                    cell_text = cell.text.strip()
                                    if cell_text:
                                        row_text += cell_text + " "
                                        cell_data.append(cell_text)
                            
                            if len(row_text.strip()) > 5:  # Фильтр пустых строк
                                print_ts(f"    Текст строки: {row_text.strip()[:100]}...")
                                
                                # Анализируем строку на предмет услуги
                                service_info = extract_service_from_row(cell_data, row_text)
                                if service_info:
                                    services_data.append(service_info)
                                    print_ts(f"    ✓ Найдена услуга: {service_info}")
                        
                    except Exception as e:
                        print_ts(f"    ⚠ Ошибка при обработке строки {row_index + 1}: {str(e)}")
                        continue
                        
            except Exception as e:
                print_ts(f"⚠ Ошибка при обработке таблицы {table_index + 1}: {str(e)}")
                continue
        
        # Если not found в таблицах, ищем в других структурах
        if not services_data:
            print_ts("ℹ Поиск услуг в других структурах...")
            
            # Поиск по data-card секциям с таблицами
            card_sections = driver.find_elements(By.CSS_SELECTOR, "[data-card]")
            for section_index, section in enumerate(card_sections):
                if not section.is_displayed():
                    continue
                    
                try:
                    # Проверяем, contains ли секция заголовок "Услуги"
                    section_text = section.text
                    if "Услуги" in section_text:
                        print_ts(f"Найдена секция с 'Услуги': {section_text[:50]}...")
                        
                        # Ищем таблицы внутри секции
                        section_tables = section.find_elements(By.TAG_NAME, "table")
                        for section_table in section_tables:
                            if section_table.is_displayed():
                                # Обрабатываем таблицу так же как and выше
                                rows = section_table.find_elements(By.TAG_NAME, "tr")
                                for row in rows:
                                    if row.is_displayed():
                                        cells = row.find_elements(By.TAG_NAME, "td")
                                        if len(cells) == 0:
                                            cells = row.find_elements(By.TAG_NAME, "th")
                                        
                                        if len(cells) > 0:
                                            cell_data = []
                                            for cell in cells:
                                                if cell.is_displayed():
                                                    cell_text = cell.text.strip()
                                                    if cell_text:
                                                        cell_data.append(cell_text)
                                            
                                            service_info = extract_service_from_row(cell_data, " ".join(cell_data))
                                            if service_info:
                                                services_data.append(service_info)
                                                print_ts(f"✓ Найдена услуга в секции: {service_info}")
                                                break
                                        
                except Exception as e:
                    print_ts(f"⚠ Ошибка при обработке секции {section_index + 1}: {str(e)}")
                    continue
        
        # Если все еще not found, используем текстовый поиск как fallback
        if not services_data:
            print_ts("ℹ Использую текстовый поиск как fallback...")
            full_text = driver.execute_script("return document.body.innerText;")
            services_data = extract_services_from_text_fallback(full_text)
        
        return services_data
            
    except Exception as e:
        print_ts(f"⚠ Ошибка при получении информации об услугах: {str(e)}")
        return []

def extract_service_from_row(cell_data, row_text):
    """Извлекает информацию об услуге из строки таблицы."""
    try:
        import re
        
        service_info = {
            "provider": "N/A",
            "service": "N/A",
            "balance": "N/A",
            "status": "N/A"
        }
        
        # Поиск поставщика
        provider_match = re.search(r'Межрегионгаз\s+Владимир\s*\(3312025868\)', row_text)
        if provider_match:
            service_info["provider"] = provider_match.group(0)
        
        # Поиск АО «Газпром газораспределение Владимир»
        gazprom_match = re.search(r'АО\s+«Газпром\s+газораспределение\s+Владимир»\s*\(12559868\)', row_text)
        if gazprom_match:
            service_info["provider"] = gazprom_match.group(0)
        
        # Поиск услуги
        if "Газоснабжение природным газом" in row_text:
            service_info["service"] = "Газоснабжение природным газом"
        elif "Техническое обслуживание газового оборудования" in row_text:
            service_info["service"] = "Техническое обслуживание газового оборудования"
        elif "Пени за ТО" in row_text:
            service_info["service"] = "Пени за ТО"
        elif "Госпошлина за ТО" in row_text:
            service_info["service"] = "Госпошлина за ТО"
        
        # Поиск статуса and суммы
        if "переплата" in row_text.lower():
            service_info["status"] = "переплата"
        elif "к оплате" in row_text.lower():
            service_info["status"] = "к оплате"
        elif "задолженность" in row_text.lower():
            service_info["status"] = "задолженность"
        
        # Поиск суммы
        balance_match = re.search(r'([0-9\s]+,[0-9]+)\s*₽', row_text)
        if balance_match:
            amount = balance_match.group(1).strip()
            service_info["balance"] = f"{amount} ₽"
        
        # Проверяем, что хотя бы что-то нашли
        if (service_info["provider"] != "N/A" or 
            service_info["service"] != "N/A" or 
            service_info["balance"] != "N/A"):
            return service_info
        else:
            return None
            
    except Exception as e:
        print_ts(f"⚠ Ошибка при извлечении из строки: {str(e)}")
        return None

def extract_services_from_text_fallback(full_text):
    """Извлекает услуги из полного текста страницы как fallback."""
    try:
        import re
        
        services_data = []
        
        # Разделяем текст на блоки по переносам строк
        lines = full_text.split('\n')
        
        current_provider = None
        current_service = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Поиск поставщика
            provider_match = re.search(r'Межрегионгаз\s+Владимир\s*\(3312025868\)|АО\s+«Газпром\s+газораспределение\s+Владимир»\s*\(12559868\)', line)
            if provider_match:
                current_provider = provider_match.group(0)
                continue
            
            # Поиск услуги
            service_match = re.search(r'Газоснабжение\s+природным\s+газом|Техническое\s+обслуживание\s+газового\s+оборудования|Пени\s+за\s+ТО|Госпошлина\s+за\s+ТО', line)
            if service_match:
                current_service = service_match.group(0)
                continue
            
            # Поиск статуса и суммы
            if ("переплата" in line.lower() or 
                "к оплате" in line.lower() or 
                "задолженность" in line.lower()):
                
                balance_match = re.search(r'([0-9\s]+,[0-9]+)\s*₽', line)
                if balance_match:
                    service_info = {
                        "provider": current_provider or "N/A",
                        "service": current_service or "N/A",
                        "balance": f"{balance_match.group(1)} ₽",
                        "status": "переплата" if "переплата" in line.lower() else 
                                  "задолженность" if "задолженность" in line.lower() else "к оплате"
                    }
                    services_data.append(service_info)
                    print_ts(f"✓ Найдена услуга из текста: {service_info}")
                    
                    # Сбрасываем для следующей записи
                    current_service = None
        
        return services_data
        
    except Exception as e:
        print_ts(f"⚠ Ошибка при fallback текстовом поиске: {str(e)}")
        return []

def get_meters_info_from_current_page(driver):
    """Получает информацию o приборах учета с текущей страницы."""
    try:
        print_ts("⌛ Извлечение информации o приборах учета...")
        
        # Собираем весь текст со страницы
        full_text = driver.execute_script("return document.body.innerText;")
        print_ts(f"Собрано текста: {len(full_text)} символов")
        
        meters_data = []
        
        # Ищем информацию o счетчиках в тексте
        import re
        
        # Поиск счетчиков
        meter_patterns = [
            r'Счетчик.*?ВК-G4T.*?Elster.*?№[0-9]+',
            r'Счетчик.*?ВК-G4T.*?[0-9]+',
            r'ВК-G4T.*?Elster.*?№[0-9]+'
        ]
        
        for pattern in meter_patterns:
            meter_matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in meter_matches:
                meter_text = match.group(0)
                print_ts(f"Найден счетчик: {meter_text}")
                
                meter_info = {
                    "name": meter_text.strip(),
                    "model": "N/A",
                    "serial": "N/A", 
                    "verification_date": "N/A",
                    "maintenance_date": "N/A"
                }
                
                # Ищем серийный номер
                serial_match = re.search(r'([0-9]{8})', meter_text)
                if serial_match:
                    meter_info["serial"] = serial_match.group(1)
                
                # Ищем дату поверки
                verification_match = re.search(r'(?:Дата.*?поверки|Дата.*?очередной.*?поверки)[\s:]*(\d{2}\.\d{2}\.\d{4})', full_text, re.IGNORECASE)
                if verification_match:
                    meter_info["verification_date"] = verification_match.group(1)
                
                # Ищем плановую дату ТО
                maintenance_match = re.search(r'(?:Плановая.*?дата.*?ТО|ТО)[\s:]*(\d{2}\.\d{2}\.\d{4})', full_text, re.IGNORECASE)
                if maintenance_match:
                    meter_info["maintenance_date"] = maintenance_match.group(1)
                
                meters_data.append(meter_info)
                print_ts(f"✓ Найден прибор учета: {meter_info}")
        
        # Если not found по паттернам, ищем по ключевым словам
        if not meters_data:
            if "Счетчик" in full_text and "ВК-G4T" in full_text:
                # Ищем все упоминания счетчиков
                counter_matches = re.finditer(r'Счетчик[^\n]*', full_text, re.IGNORECASE)
                for match in counter_matches:
                    counter_text = match.group(0).strip()
                    if len(counter_text) > 10:  # Фильтр коротких совпадений
                        meter_info = {
                            "name": counter_text,
                            "model": "N/A",
                            "serial": "N/A", 
                            "verification_date": "N/A",
                            "maintenance_date": "N/A"
                        }
                        
                        # Ищем серийный номер
                        serial_match = re.search(r'([0-9]{8})', counter_text)
                        if serial_match:
                            meter_info["serial"] = serial_match.group(1)
                        
                        meters_data.append(meter_info)
                        print_ts(f"✓ Найден прибор учета: {meter_info}")
        
        # Поиск по структуре страницы
        if not meters_data:
            # Ищем элементы со счетчиками
            meter_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Счетчик') or contains(text(), 'ВК-G4T') or contains(text(), 'Elster')]")
            for elem in meter_elements:
                if elem.is_displayed():
                    try:
                        elem_text = elem.text.strip()
                        if "Счетчик" in elem_text and len(elem_text) > 20:
                            meter_info = {
                                "name": elem_text,
                                "model": "N/A",
                                "serial": "N/A", 
                                "verification_date": "N/A",
                                "maintenance_date": "N/A"
                            }
                            
                            # Ищем серийный номер
                            serial_match = re.search(r'([0-9]{8})', elem_text)
                            if serial_match:
                                meter_info["serial"] = serial_match.group(1)
                            
                            meters_data.append(meter_info)
                            print_ts(f"✓ Найден прибор учета: {meter_info}")
                            break
                    except:
                        continue
        
        return meters_data
            
    except Exception as e:
        print_ts(f"⚠ Ошибка при получении информации o приборах учета: {str(e)}")
        return []

def display_all_info(services_data, charges_data, meters_data):
    """Выводит всю информацию в форматированном виде."""
    print("\n" + "="*60)
    print("ИНФОРМАЦИЯ ИЗ ЛК ГАЗ")
    print("="*60)
    
    # Выводим информацию об услугах
    if services_data:
        print("\n📋 УСЛУГИ:")
        for i, service in enumerate(services_data, 1):
            print(f"\n{i}. {service['provider']}")
            print(f"   Услуга: {service['service']}")
            print(f"   Баланс: {service['balance']} ({service['status']})")
    else:
        print("\n📋 УСЛУГИ: not found")
    
    # Выводим информацию o приборах учета
    if meters_data:
        print(f"\n🔧 ПРИБОРЫ УЧЕТА ({len(meters_data)}):")
        for i, meter in enumerate(meters_data, 1):
            print(f"\n{i}. {meter['name']}")
            if meter['model'] != "N/A":
                print(f"   Модель оборудования: {meter['model']}")
            if meter['serial'] != "N/A":
                print(f"   Серийный номер: {meter['serial']}")
            if meter['verification_date'] != "N/A":
                print(f"   Дата очередной поверки: {meter['verification_date']}")
            if meter['maintenance_date'] != "N/A":
                print(f"   Плановая дата ТО: {meter['maintenance_date']}")
    else:
        print("\n🔧 ПРИБОРЫ УЧЕТА: not found")
    
    # Выводим JSON
    print("\n" + "="*60)
    print("JSON ФОРМАТ:")
    print("="*60)
    
    result_data = {
        "services": services_data,
        "meters": meters_data,
        "charges": charges_data
    }
    
    print(json.dumps(result_data, ensure_ascii=False, indent=2))

def parse_arguments():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description='Автоматизированная авторизация в личный кабинет ЛК Газ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python lk-gaz-tables.py --login mylogin --password mypass
  python lk-gaz-tables.py -l user123 -p secret123
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

if __name__ == "__main__":
    args = parse_arguments()
    main(args.login, args.password)