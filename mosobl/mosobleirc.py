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
BASE_URL = "https://lkk.mosobleirc.ru/"
LOGIN_URL = f"{BASE_URL}#/login"
BILLS_URL = f"{BASE_URL}#/bills"
METERS_URL = f"{BASE_URL}#/meters"

# Папка для отладочных данных
DEBUG_DIR = "debug_data"
os.makedirs(DEBUG_DIR, exist_ok=True)

def main(login, password):
    #driver = init_driver_windows()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    bills_data = []
    meter_readings_data = []
    
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
            print("⌛ Проверяю успешность авторизации...")
            
            # Ждем редиректа на страницу счетов или появления элементов личного кабинета
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.url_contains("bills"),
                    EC.url_contains("personal"),
                    EC.url_contains("services"),
                    EC.url_contains("tickets"),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".Header__menuItem.active, .ui.active.item")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".personal, .account, .user-info, .user-profile")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".bills, .accounts, .dashboard")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".Header__dropdown, .ui.dropdown"))
                )
            )
            print("✓ Успешная авторизация!")
        except:
            save_debug_data(driver, "auth_failed")
            print("⚠ Проверяю наличие ошибок авторизации...")
            
            # Дополнительная проверка на случай, если ошибка не была поймана ранее
            error_message = check_login_errors(driver)
            if error_message:
                raise ValueError(f"Ошибка авторизации: {error_message}")
            
            # Проверяем, видна ли форма входа
            try:
                login_form = driver.find_element(By.CSS_SELECTOR, "form.ui.form")
                if login_form and login_form.is_displayed():
                    print("⚠ Форма входа все еще видна - авторизация не удалась")
                    raise ValueError("Форма входа все еще видна после попытки авторизации")
            except:
                pass
            
            # Проверяем текущий URL
            current_url = driver.current_url
            print(f"ℹ Текущий URL: {current_url}")
            
            # Если URL изменился и не содержит login, возможно авторизация прошла
            if "login" not in current_url and "auth" not in current_url:
                print("ℹ URL изменился и не содержит login/auth - возможно авторизация прошла")
                # Проверяем, есть ли элементы личного кабинета
                try:
                    header_elements = driver.find_elements(By.CSS_SELECTOR, ".Header, .Header__container, .ui.container")
                    if header_elements:
                        print("✓ Обнаружены элементы личного кабинета - авторизация успешна")
                        return  # Продолжаем выполнение
                except:
                    pass
            
            # Если ничего не помогло, сохраняем дополнительные данные для анализа
            print("⚠ Сохраняю дополнительные данные для анализа авторизации...")
            save_debug_data(driver, "auth_analysis")
            
            # Пробуем перейти на страницу счетов вручную
            try:
                print("⌛ Пробую перейти на страницу счетов вручную...")
                driver.get(BILLS_URL)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".Bills__main, .ui.table, .bills"))
                )
                print("✓ Удалось перейти на страницу счетов - авторизация прошла")
                return  # Продолжаем выполнение
            except:
                raise ValueError("Не удалось войти в личный кабинет (неизвестная ошибка)")

        # 4. Переходим на страницу счетов
        print(f"⌛ Перехожу на страницу счетов: {BILLS_URL}")
        driver.get(BILLS_URL)
        
        # 5. Парсим данные счетов
        try:
            bills_data = get_bills_data(driver)
        except Exception as e:
            print(f"Ошибка при получении данных счетов: {str(e)}")

        # 6. Переходим на страницу счетчиков
        print(f"⌛ Перехожу на страницу счетчиков: {METERS_URL}")
        if navigate_to_meters_page(driver):
            try:
                meter_readings_data = get_all_meter_readings(driver)
            except Exception as e:
                print(f"Ошибка при получении показаний счетчиков: {str(e)}")

        # Выводим результаты
        display_results(bills_data, meter_readings_data)

    except Exception as e:
        print(f"\nCritical error: {str(e)}")
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
        # Ожидаем загрузки страницы логина
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("✓ Страница входа загружена")
        
        # Анализируем структуру формы для лучшего понимания
        check_form_structure(driver)
        
        # Ищем форму по структуре, соответствующей предоставленному HTML
        # Сначала ищем контейнер формы
        try:
            form_container = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".content, .AuthHeader__wrapper, .Login__formError"))
            )
            print("✓ Найден контейнер формы")
        except:
            print("ℹ Контейнер формы не найден, ищем поля напрямую")
            form_container = driver
        
        # Ищем поле логина по точным селекторам из HTML
        # ВАЖНО: Игнорируем поля в NoAutofillHack - ищем только видимые поля в форме
        try:
            # Сначала ищем форму
            form = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form.ui.form"))
            )
            print("✓ Найдена форма")
            
            # Ищем поле логина в контексте формы, исключая NoAutofillHack
            login_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "form.ui.form .required.field input[name='login']"))
            )
            print("✓ Найдено поле логина в форме (исключая NoAutofillHack)")
        except:
            try:
                # Альтернативный селектор - поле в контейнере с меткой
                login_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "label[for='login'] + .ui.fluid.input input[name='login']"))
                )
                print("✓ Найдено поле логина по метке")
            except:
                try:
                    # По родительскому контейнеру
                    login_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.required.field"))
                    )
                    login_field = login_container.find_element(By.CSS_SELECTOR, "input[type='text']")
                    print("✓ Найдено поле логина через родительский контейнер")
                except:
                    # Финальная попытка - все поля логина, кроме тех в NoAutofillHack
                    all_login_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='login']")
                    for field in all_login_fields:
                        # Проверяем, что поле видимо и не находится в скрытом контейнере
                        if field.is_displayed() and field.size['height'] > 0 and field.size['width'] > 0:
                            # Дополнительная проверка - поле не должно быть пустым в NoAutofillHack
                            try:
                                parent_div = field.find_element(By.XPATH, "..")
                                parent_classes = parent_div.get_attribute("class") or ""
                                if "NoAutofillHack" not in parent_classes:
                                    login_field = field
                                    break
                            except:
                                # Если не удалось получить родителя, проверяем по умолчанию
                                login_field = field
                                break
                    else:
                        # Если не нашли, берем первое видимое
                        login_field = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR,
                                "input[name='login']:not(.NoAutofillHack *)"))
                        )
                    print("✓ Найдено поле логина (альтернативный поиск)")
        
        # Ищем поле пароля по точным селекторам из HTML
        try:
            # По name атрибуту и id в контексте формы
            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "form.ui.form .required.field input[name='password'][id='field-password']"))
            )
            print("✓ Найдено поле пароля в форме по name='password' и id='field-password'")
        except:
            try:
                # По контейнеру с иконкой глаза
                password_container = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ui.error.fluid.icon.input")))
                password_field = password_container.find_element(By.CSS_SELECTOR, "input[type='password']")
                print("✓ Найдено поле пароля через контейнер с иконкой глаза")
                
                # Пробуем переключить видимость пароля для тестирования
                toggle_password_visibility(driver)
            except:
                try:
                    # По id в контексте формы
                    password_field = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                            "form.ui.form input[id='field-password']"))
                    )
                    print("✓ Найдено поле пароля по id='field-password' в форме")
                except:
                    # Финальная попытка - все поля пароля, кроме тех in NoAutofillHack
                    all_password_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    for field in all_password_fields:
                        # Проверяем, что поле не в NoAutofillHack и видимо
                        if field.is_displayed() and "NoAutofillHack" not in field.find_element(By.XPATH, "./ancestor::*").get_attribute("class"):
                            password_field = field
                            break
                    else:
                        password_field = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR,
                                "input[type='password']:not(.NoAutofillHack *)"))
                        )
                    print("✓ Найдено поле пароля (альтернативный поиск)")
        
        print("✓ Поля ввода найдены")
        
        # Заполняем поля с дополнительной проверкой
        print("⌛ Заполняю поля формы...")
        
        # Проверяем, что поля доступны для ввода
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(login_field))
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(password_field))
        
        # Очищаем и заполняем поле логина
        login_field.clear()
        login_field.send_keys(login)
        # Проверяем, что текст введен
        if login_field.get_attribute("value") != login:
            # Если не сработало, пробуем JavaScript
            driver.execute_script("arguments[0].value = arguments[1];", login_field, login)
        print(f"✓ Введен логин: {login}")
        
        # Очищаем и заполняем поле пароля
        password_field.clear()
        password_field.send_keys(password)
        # Проверяем, что текст введен
        if password_field.get_attribute("value"):
            print(f"✓ Введен пароль: {'*' * len(password)}")
        else:
            # Если не сработало, пробуем JavaScript
            driver.execute_script("arguments[0].value = arguments[1];", password_field, password)
            print(f"✓ Введен пароль (через JS): {'*' * len(password)}")
        
        # Ищем кнопку входа
        try:
            # Ищем кнопку "Я забыл пароль" как ориентир, затем ищем кнопку входа
            forgot_password_link = driver.find_elements(By.CSS_SELECTOR, "a[role='button']")
            for link in forgot_password_link:
                if "забыл" in link.text.lower() or "пароль" in link.text.lower():
                    print("✓ Найдена ссылка 'Я забыл пароль' - форма найдена")
                    break
            
            # Ищем кнопку входа в контексте формы
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "form.ui.form .extra.content .ui.primary.button[type='submit']"))
            )
            print(f"✓ Найдена кнопка входа: {submit_button.text or 'Кнопка без текста'}")
            driver.execute_script("arguments[0].click();", submit_button)
            print("✓ Форма отправлена")
        except Exception as e:
            print(f"⚠ Не удалось найти кнопку входа: {str(e)}")
            # Пробуем отправить форму через нажатие Enter в поле пароля
            try:
                password_field.send_keys("\n")
                print("✓ Форма отправлена (Enter в поле пароля)")
            except Exception as e2:
                # Пробуем submit у формы
                try:
                    form.submit()
                    print("✓ Форма отправлена (метод submit)")
                except Exception as e3:
                    print(f"⚠ Все методы отправки формы не сработали: {str(e3)}")
                    save_debug_data(driver, "form_submit_error")
                    raise ValueError("Не удалось отправить форму входа")
        
        # Дополнительная проверка: ждем начала процесса авторизации
        try:
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.url_changes(LOGIN_URL),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, [class*='progress']"))
                )
            )
            print("✓ Начался процесс авторизации")
        except:
            print("ℹ Процесс авторизации не обнаружен, но это может быть нормально")
        
        # Ждем перехода на следующую страницу
        wait_for_page_transition(driver, 15)
        
    except Exception as e:
        save_debug_data(driver, "form_fill_error")
        raise ValueError(f"Ошибка при заполнении формы: {str(e)}")

def check_login_errors(driver):
    """Проверяет наличие сообщений об ошибках при входе."""
    try:
        # Проверяем наличие сообщений об ошибках по специфичным селекторам для этого сайта
        error_selectors = [
            ".Login__formError", ".formError", ".error", ".alert-danger",
            ".notification.error", "[class*='error']", "[class*='alert']",
            "div[role='alert']", ".toast-error", ".message.error",
            ".ui.error.message", ".field.error", ".error.field"
        ]
        
        for selector in error_selectors:
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for error_elem in error_elements:
                    if error_elem.is_displayed():
                        error_text = error_elem.text.strip()
                        if error_text:
                            # Проверяем на наличие ключевых слов об ошибках
                            error_keywords = ['неверный', 'ошибка', 'неправильно', 'неверный логин',
                                            'пароль', 'неверные данные', 'авторизация', 'не удалось войти',
                                            'неправильный', 'не найден', 'не существует', 'не валиден']
                            if any(word in error_text.lower() for word in error_keywords):
                                print(f"⚠ Найдено сообщение об ошибке: {error_text}")
                                return error_text
            except Exception as e:
                continue
                
    except Exception as e:
        pass
    
    return None

def toggle_password_visibility(driver):
    """Переключает видимость пароля (если есть иконка глаза)."""
    try:
        # Ищем иконку глаза для переключения видимости пароля
        eye_icon = driver.find_elements(By.CSS_SELECTOR, ".eye.icon, .PasswordField__eye, i.eye")
        if eye_icon and eye_icon[0].is_displayed():
            print("✓ Найдена иконка глаза для переключения видимости пароля")
            driver.execute_script("arguments[0].click();", eye_icon[0])
            print("✓ Видимость пароля переключена")
            return True
    except Exception as e:
        print(f"ℹ Иконка глаза не найдена или не доступна: {str(e)}")
    
    return False

def wait_for_page_transition(driver, timeout=10):
    """Ожидает перехода на следующую страницу после отправки формы."""
    try:
        # Ждем изменения URL или появления элементов следующей страницы
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.url_changes(driver.current_url),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".personal, .account, .user-info, .bills, .accounts")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, .progress")),
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "input[name='login']"))
            )
        )
        print("✓ Страница начала изменяться после отправки формы")
        return True
    except:
        print("ℹ Страница не изменилась в течение ожидаемого времени")
        return False

def check_form_structure(driver):
    """Анализирует структуру формы для лучшего понимания элементов."""
    try:
        print("🔍 Анализирую структуру формы...")
        
        # Ищем все поля ввода
        inputs = driver.find_elements(By.CSS_SELECTOR, "input")
        print(f"ℹ Найдено {len(inputs)} полей ввода:")
        
        for i, inp in enumerate(inputs):
            name = inp.get_attribute("name") or "no-name"
            type_attr = inp.get_attribute("type") or "no-type"
            placeholder = inp.get_attribute("placeholder") or "no-placeholder"
            id_attr = inp.get_attribute("id") or "no-id"
            classes = inp.get_attribute("class") or ""
            
            print(f"  Поле {i+1}: name='{name}', type='{type_attr}', id='{id_attr}', placeholder='{placeholder}'")
            print(f"    Классы: {classes}")
        
        # Ищем кнопки
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        print(f"ℹ Найдено {len(buttons)} кнопок:")
        
        for i, btn in enumerate(buttons):
            btn_type = btn.get_attribute("type") or "no-type"
            btn_text = btn.text.strip()
            btn_classes = btn.get_attribute("class") or ""
            print(f"  Кнопка {i+1}: type='{btn_type}', text='{btn_text}', classes='{btn_classes}'")
        
        # Ищем ссылки
        links = driver.find_elements(By.CSS_SELECTOR, "a")
        print(f"ℹ Найдено {len(links)} ссылок:")
        
        for i, link in enumerate(links):
            link_text = link.text.strip()
            link_role = link.get_attribute("role") or "no-role"
            print(f"  Ссылка {i+1}: text='{link_text}', role='{link_role}'")
            
        return True
        
    except Exception as e:
        print(f"⚠ Ошибка при анализе структуры формы: {str(e)}")
        return False

def get_apartments_list(driver):
    """Получает список всех доступных квартир."""
    try:
        print("⌛ Поиск выпадающего списка квартир...")
        
        # Ищем dropdown с квартирами с точным соответствием структуре
        try:
            # Ищем dropdown, в котором есть слово "Квартира"
            apartment_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    "//div[@role='listbox' and @aria-expanded and contains(@class, 'dropdown')][.//*[contains(text(), 'Квартира')]]"))
            )
            print("✓ Найден выпадающий список квартир (содержит 'Квартира')")
        except:
            try:
                # CSS вариант: dropdown с атрибутами и текстом "Квартира"
                apartment_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "div[role='listbox'][aria-expanded][class*='dropdown']")))
                # Проверяем, что в dropdown есть текст "Квартира"
                dropdown_text = apartment_dropdown.text
                if "Квартира" not in dropdown_text:
                    raise Exception("Dropdown не содержит текст 'Квартира'")
                print("✓ Найден выпадающий список квартир (CSS + проверка текста)")
            except:
                try:
                    # Альтернативный поиск по более общим селекторам с проверкой текста
                    apartment_dropdown = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                            ".ui.floating.inline.dropdown[role='listbox']"))
                    )
                    # Проверяем наличие текста "Квартира"
                    dropdown_text = apartment_dropdown.text
                    if "Квартира" not in dropdown_text:
                        raise Exception("Dropdown не содержит текст 'Квартира'")
                    print("✓ Найден выпадающий список квартир (альтернативный поиск + проверка текста)")
                except:
                    # Поиск по тексту "Квартира" и поиск родительского dropdown
                    text_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Квартира')]")
                    apartment_dropdown = None
                    for text_elem in text_elements:
                        try:
                            # Ищем родительский dropdown
                            parent_dropdown = text_elem.find_element(By.XPATH,
                                ".//ancestor::div[@role='listbox' and contains(@class, 'dropdown')]")
                            apartment_dropdown = parent_dropdown
                            print("✓ Найден выпадающий список квартир (через текст 'Квартира')")
                            break
                        except:
                            continue
                    
                    if not apartment_dropdown:
                        print("⚠ Выпадающий список квартир с текстом 'Квартира' не найден")
                        return []
        
        if not apartment_dropdown:
            print("ℹ Выпадающий список квартир не найден")
            return []
        
        # Проверяем состояние dropdown
        is_expanded = apartment_dropdown.get_attribute("aria-expanded") == "true"
        print(f"ℹ Dropdown expanded: {is_expanded}")
        
        # Пытаемся получить текущую квартиру разными способами
        current_apartment = ""
        try:
            # Способ 1: Поиск по тегу b
            current_elem = apartment_dropdown.find_element(By.TAG_NAME, "b")
            current_apartment = current_elem.text.strip()
        except:
            try:
                # Способ 2: Поиск по классу Bills__mainData
                current_elem = apartment_dropdown.find_element(By.XPATH,
                    ".//following-sibling::div[contains(@class, 'Bills__mainData')][1]")
                current_apartment = current_elem.text.strip()
            except:
                try:
                    # Способ 3: Поиск текста "Квартира" в самом dropdown
                    text_elements = apartment_dropdown.find_elements(By.XPATH,
                        ".//*[contains(text(), 'Квартира')]")
                    for elem in text_elements:
                        text = elem.text.strip()
                        if "Квартира" in text and len(text) > 5:  # Фильтр для коротких слов
                            current_apartment = text
                            break
                except:
                    current_apartment = ""
        
        if current_apartment:
            print(f"ℹ Текущая квартира: {current_apartment}")
        else:
            print("ℹ Текущая квартира не определена")
        
        if not is_expanded:
            # Кликаем для раскрытия dropdown
            driver.execute_script("arguments[0].click();", apartment_dropdown)
            print("⌛ Раскрываю список квартир...")
            
            # Ждем появления опций
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".menu.transition .item"))
                )
                print("✓ Меню квартир раскрыто")
                
                # Добавляем паузу для стабилизации меню
                # print("⏳ Пауза для стабилизации выпадающего меню...")
                # time.sleep(5)
                # print("✓ Меню стабилизировано")
                
                # После раскрытия меню, повторно ищем все элементы с "Квартира"
                print("🔍 Повторный поиск элементов после раскрытия меню...")
                expanded_quarter_elements = driver.find_elements(By.XPATH,
                    "//*[contains(text(), 'Квартира')]")
                
                print(f"  Теперь найдено {len(expanded_quarter_elements)} элементов с текстом 'Квартира' на странице:")
                
                for i, elem in enumerate(expanded_quarter_elements):
                    try:
                        element_text = elem.text.strip()
                        element_displayed = elem.is_displayed()
                        element_tag = elem.tag_name
                        element_classes = elem.get_attribute("class") or "no-class"
                        element_id = elem.get_attribute("id") or "no-id"
                        element_role = elem.get_attribute("role") or "no-role"
                        element_aria_checked = elem.get_attribute("aria-checked") or "no-aria"
                        element_aria_selected = elem.get_attribute("aria-selected") or "no-aria"
                        
                        # Get the outer HTML of the element
                        try:
                            element_html = elem.get_attribute("outerHTML")
                        except:
                            element_html = "Could not retrieve HTML"
                        
                        print(f"    Элемент {i+1}:")
                        print(f"      Текст: '{element_text}'")
                        print(f"      Тег: {element_tag}")
                        print(f"      Видимый: {element_displayed}")
                        print(f"      ID: {element_id}")
                        print(f"      Classes: {element_classes}")
                        print(f"      Role: {element_role}")
                        print(f"      Aria-checked: {element_aria_checked}")
                        print(f"      Aria-selected: {element_aria_selected}")
                        print(f"      HTML код:")
                        print(f"        {element_html}")
                        
                        # Добавляем новые квартиры из раскрытого меню
                        if element_text and "Квартира" in element_text:
                            if element_text not in apartments:
                                apartments.append(element_text)
                                print(f"        ✓ Добавлена квартира из раскрытого меню: {element_text}")
                            else:
                                print(f"        ℹ Квартира уже добавлена: {element_text}")
                        else:
                            if not element_displayed:
                                print(f"        ⚠ Элемент не видим: {element_text}")
                            elif not element_text:
                                print(f"        ⚠ Пустой текст")
                            else:
                                print(f"        ⚠ Не соответствует критериям: {element_text}")
                        print()  # Empty line for better readability
                            
                    except Exception as e:
                        print(f"    ⚠ Ошибка при обработке элемента {i+1}: {str(e)}")
                        continue
                        
            except:
                print("ℹ Меню может быть уже видимо")
        else:
            print("ℹ Dropdown уже раскрыт")
        
        # Собираем все доступные квартиры
        apartments = []
        
        # Добавляем текущую квартиру в список
        if current_apartment and "Квартира" in current_apartment:
            apartments.append(current_apartment)
            print(f"  Добавлена текущая квартира: {current_apartment}")
        
        #todo
        apartments.append("Квартира 53")
        
        # Закрываем dropdown (если он был раскрыт)
        if not is_expanded:
            try:
                driver.execute_script("arguments[0].click();", apartment_dropdown)
                print("ℹ Закрыл dropdown")
            except:
                print("ℹ Не удалось закрыть dropdown")
        
        if not apartments:
            print("⚠ Квартиры не найдены в списке")
            # Сохраняем HTML для анализа структуры dropdown
            with open(os.path.join(DEBUG_DIR, "apartment_dropdown_analysis.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        print(f"✓ Найдено {len(apartments)} квартир: {', '.join(apartments)}")
        return apartments
        
    except Exception as e:
        print(f"⚠ Ошибка при получении списка квартир: {str(e)}")
        # Сохраняем HTML для анализа ошибки
        with open(os.path.join(DEBUG_DIR, "apartment_dropdown_error.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return []

def switch_to_apartment(driver, apartment_name):
    """Переключается на указанную квартиру."""
    try:
        print(f"⌛ Переключаюсь на {apartment_name}...")
        
         # Ищем dropdown, в котором есть слово "Квартира"
        apartment_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                "//div[@role='listbox' and @aria-expanded and contains(@class, 'dropdown')][.//*[contains(text(), 'Квартира')]]"))
        )
        print("✓ Найден выпадающий список квартир (содержит 'Квартира')")
        
        # Кликаем для раскрытия dropdown
        driver.execute_script("arguments[0].click();", apartment_dropdown)
        # print(f"Открыл список квартир...")
        # time.sleep(5)  # Даем время на загрузку данных

        # Ждем появления опций
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".menu.transition .item"))
        )
        
        # Ищем нужную квартиру и кликаем
        apartment_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[@role='option']//span[contains(text(), '{apartment_name}')]/ancestor::div[@role='option']"))
        )
        
        driver.execute_script("arguments[0].click();", apartment_option)
        print(f"✓ Переключился на {apartment_name}")
        
        # Ждем загрузки данных для новой квартиры
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui.inverted.dimmer .loader"))
        )
        
        # time.sleep(2)  # Даем время на загрузку данных
        return True
        
    except Exception as e:
        print(f"⚠ Ошибка при переключении на {apartment_name}: {str(e)}")
        return False

def get_bills_data_for_current_apartment(driver, apartment_name=""):
    """Получает данные счетов для текущей выбранной квартиры."""
    try:
        apartment_data = {
            "apartment": apartment_name or "Текущая квартира",
            "account_number": "N/A",
            "address": "N/A",
            "balance": "N/A",
            "status": "N/A"
        }
        
        print(f"⌛ Получаю данные для {apartment_data['apartment']}...")
        
        # Ищем данные квартиры
        try:
            # Ищем номер лицевого счета
            account_elements = driver.find_elements(By.CSS_SELECTOR,
                ".Bills__mainData")
            
            for elem in account_elements:
                text = elem.text.strip()
                if "Лицевой счет" in text and any(c.isdigit() for c in text):
                    apartment_data["account_number"] = text
                    break
            
            # Ищем адрес
            for elem in account_elements:
                text = elem.text.strip()
                if text and "Лицевой счет" not in text and any(c.isalpha() for c in text):
                    apartment_data["address"] = text
                    break
            
            # Ищем баланс
            balance_elements = driver.find_elements(By.CSS_SELECTOR,
                ".Bills__balance, .right.aligned.Bills__balance, .Bills__balance span")
            
            for elem in balance_elements:
                text = elem.text.strip()
                if text and any(c.isdigit() for c in text):
                    apartment_data["balance"] = text
                    break
            
            # Ищем статус
            status_elements = driver.find_elements(By.CSS_SELECTOR,
                ".error, .Bills__error, .ui.error.message")
            
            for elem in status_elements:
                text = elem.text.strip()
                if text:
                    apartment_data["status"] = text
                    break
        
        except Exception as e:
            print(f"    ⚠ Ошибка при парсинге данных: {str(e)}")
        
        if apartment_data["account_number"] != "N/A" or apartment_data["address"] != "N/A":
            print(f"✓ Получены данные для {apartment_data['apartment']}:")
            print(f"    Адрес: {apartment_data['address']}")
            print(f"    Счет: {apartment_data['account_number']}")
            print(f"    Баланс: {apartment_data['balance']}")
            print(f"    Статус: {apartment_data['status']}")
            return apartment_data
        else:
            print(f"⚠ Данные для {apartment_data['apartment']} не найдены")
            return None
        
    except Exception as e:
        print(f"⚠ Ошибка при получении данных для {apartment_name}: {str(e)}")
        return None

def get_bills_data(driver):
    """Получает данные счетов для всех доступных квартир с страницы /#/bills"""
    try:
        print(f"⌛ Перехожу на страницу счетов: {BILLS_URL}")
        driver.get(BILLS_URL)
        
        # Ожидаем загрузки страницы
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("⌛ Ожидаю полной загрузки страницы счетов...")
        
        # Ждем исчезновения лоадера
        try:
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui.loader, .ui.active.loader, .ui.inverted.dimmer .loader"))
            )
            print("✓ Лоадер исчез, страница загружена")
        except:
            print("ℹ Лоадер не найден или страница загружена")
        
        # Ждем появления заголовка "Платежи"
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Платежи')]"))
            )
            print("✓ Заголовок 'Платежи' найден")
        except:
            print("⚠ Заголовок 'Платежи' не найден")
        
        # Ждем появление хотя бы одного элемента с текстом "Квартира"
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Квартира')]"))
            )
            print("✓ Элементы с 'Квартира' найдены")
        except:
            print("⚠ Элементы с 'Квартира' не найдены")
        
        print("⌛ Получаю данные счетов...")
        
        # Сохраняем скриншот для отладки
        save_debug_data(driver, "bills_page")
        
        bills_data = []
        
        # Получаем список всех квартир
        apartments = get_apartments_list(driver)
        
        if not apartments:
            print("ℹ Квартиры не найдены, получаю данные для текущей...")
            # Получаем данные для текущей квартиры
            current_data = get_bills_data_for_current_apartment(driver)
            if current_data:
                bills_data.append(current_data)
        else:
            # Обрабатываем каждую квартиру
            for i, apartment in enumerate(apartments):
                print(f"\n🏢 Обработка квартиры {i+1}/{len(apartments)}: {apartment}")
                
                # Переключаемся на квартиру (если это не первая квартира)
                if i > 0:
                    if not switch_to_apartment(driver, apartment):
                        print(f"⚠ Не удалось переключиться на {apartment}, пропускаю...")
                        continue
                
                # Получаем данные для текущей квартиры
                apartment_data = get_bills_data_for_current_apartment(driver, apartment)
                if apartment_data:
                    bills_data.append(apartment_data)
                else:
                    print(f"⚠ Не удалось получить данные для {apartment}")
        
        if not bills_data:
            print("ℹ На странице не найдено данных счетов")
            # Сохраняем HTML для анализа
            with open(os.path.join(DEBUG_DIR, "bills_page_analysis.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return None
        
        print(f"\n✓ Успешно получены данные для {len(bills_data)} квартир")
        return bills_data
        
    except Exception as e:
        save_debug_data(driver, "bills_data_error")
        raise ValueError(f"Ошибка при получении данных счетов: {str(e)}")


def display_results(bills_data, meter_readings_data=None):
    """Форматирует и выводит объединенные результаты по квартирам в JSON и текстовом формате."""
    
    # Подготовка объединенных данных
    apartments_data = []
    
    # Создаем словарь для быстрого доступа к данным счетов по адресу
    bills_by_address = {}
    if bills_data:
        for bill in bills_data:
            address = bill['address']
            if address and address != "N/A":
                bills_by_address[address] = bill
    
    # Объединяем данные по квартирам
    all_apartments = set()
    
    # Добавляем квартиры из счетов
    if bills_data:
        for bill in bills_data:
            if bill['address'] and bill['address'] != "N/A":
                all_apartments.add(bill['address'])
    
    # Добавляем квартиры из показаний счетчиков
    if meter_readings_data:
        for meter_apartment in meter_readings_data:
            all_apartments.add(meter_apartment['apartment'])
    
    # Формируем объединенные данные для каждой квартиры
    for apartment_name in sorted(all_apartments):
        apartment_info = {
            "apartment": apartment_name,
            "account_number": "N/A",
            "address": apartment_name,
            "balance": "N/A",
            "status": "N/A",
            "meters": []
        }
        
        # Добавляем данные счетов если есть
        if apartment_name in bills_by_address:
            bill_data = bills_by_address[apartment_name]
            apartment_info.update({
                "account_number": bill_data['account_number'],
                "balance": bill_data['balance'],
                "status": bill_data['status']
            })
        
        # Добавляем показания счетчиков
        if meter_readings_data:
            for meter_apartment in meter_readings_data:
                if meter_apartment['apartment'] == apartment_name:
                    if meter_apartment['meters']:
                        apartment_info["meters"] = meter_apartment['meters']
                    break
        
        apartments_data.append(apartment_info)
    
    result_data = {
        "apartments": apartments_data
    }
    
    # Выводим JSON формат
    print("\n" + "="*60)
    print("JSON ФОРМАТ:")
    print("="*60)
    print(json.dumps(result_data, ensure_ascii=False, indent=2))
    
    # Выводим текстовый формат
    print("\n" + "="*60)
    print("ТЕКСТОВЫЙ ФОРМАТ:")
    print("="*60)
    
    if apartments_data:
        for i, apartment in enumerate(apartments_data, 1):
            print(f"\n{i}. Квартира: {apartment['apartment']}")
            
            # Информация о лицевом счете
            if apartment['account_number'] != "N/A":
                print(f"   Лицевой счет: {apartment['account_number']}")
            if apartment['balance'] != "N/A":
                print(f"   Баланс: {apartment['balance']}")
            if apartment['status'] != "N/A":
                print(f"   Статус: {apartment['status']}")
            
            # Показания счетчиков
            if apartment['meters']:
                print(f"   Счетчики ({len(apartment['meters'])}):")
                for j, meter in enumerate(apartment['meters'], 1):
                    print(f"     {j}. {meter['type']}")
                    if meter['serial_number'] != "N/A":
                        print(f"        Серийный номер: {meter['serial_number']}")
                    if meter['period'] != "N/A":
                        print(f"        Период: {meter['period']}")
                    if meter['reading'] != "N/A":
                        print(f"        Показания: {meter['reading']}")
                    if meter['consumption'] != "N/A":
                        print(f"        Расход: {meter['consumption']}")
                    if meter['date'] != "N/A":
                        print(f"        Дата: {meter['date']}")
            else:
                print(f"   Счетчики: не найдены")
    else:
        print("Квартиры не найдены")

def parse_arguments():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description='Автоматизированная авторизация в личный кабинет МосОблЕИРЦ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python mosobleirc.py --login mylogin --password mypass
  python mosobleirc.py -l user123 -p secret123
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

def navigate_to_meters_page(driver):
    """Переходит на страницу счетчиков."""
    try:
        print(f"⌛ Перехожу на страницу счетчиков: {METERS_URL}")
        driver.get(METERS_URL)
        
        # Ожидаем загрузки страницы
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("⌛ Ожидаю полной загрузки страницы счетчиков...")
        
        # Ждем исчезновения лоадера
        try:
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui.loader, .ui.active.loader, .ui.inverted.dimmer .loader"))
            )
            print("✓ Лоадer исчез, страница счетчиков загружена")
        except:
            print("ℹ Лоадер не найден или страница загружена")
        
        # Дополнительная загрузка для обновления данных (избегаем кэширования)
        print("🔄 Обновляю страницу для получения актуальных данных...")
        driver.refresh()
        
        # Ждем повторной загрузки после refresh
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui.loader, .ui.active.loader, .ui.inverted.dimmer .loader"))
            )
            print("✓ Страница обновлена после refresh")
        except:
            print("ℹ Лоадer после refresh не найден")
        
        # Ждем появление хотя бы одного элемента с текстом "Квартира"
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Квартира')]"))
            )
            print("✓ Элементы с 'Квартира' найдены на странице счетчиков")
        except:
            print("⚠ Элементы с 'Квартира' не найдены на странице счетчиков")
        
        # Сохраняем скриншот для отладки
        save_debug_data(driver, "meters_page")
        return True
        
    except Exception as e:
        print(f"⚠ Ошибка при переходе на страницу счетчиков: {str(e)}")
        save_debug_data(driver, "meters_page_error")
        return False

def get_meter_readings_for_current_apartment(driver, apartment_name=""):
    """Получает показания счетчиков для текущей выбранной квартиры."""
    try:
        apartment_meters = {
            "apartment": apartment_name or "Текущая квартира",
            "meters": []
        }
        
        print(f"⌛ Получаю показания счетчиков для {apartment_meters['apartment']}...")
        
        # Ищем таблицу с показаниями счетчиков
        try:
            # Ищем таблицу по классу из HTML структуры
            meter_table = driver.find_elements(By.CSS_SELECTOR,
                ".MeterWidget__table, .ui.unstackable.very.basic.padded.table")
            
            if not meter_table:
                print("⚠ Таблица счетчиков не найдена, пробую альтернативный поиск...")
                # Альтернативный поиск
                meter_table = driver.find_elements(By.CSS_SELECTOR,
                    ".ui.table tbody, table tbody")
            
            if meter_table:
                # Ищем строки таблицы
                meter_rows = meter_table[0].find_elements(By.CSS_SELECTOR, "tr")
                print(f"ℹ Найдено {len(meter_rows)} строк в таблице счетчиков")
            else:
                meter_rows = []
            
            for i, row in enumerate(meter_rows):
                try:
                    meter_data = {
                        "type": "N/A",
                        "serial_number": "N/A",
                        "period": "N/A",
                        "reading": "N/A",
                        "consumption": "N/A",
                        "date": "N/A"
                    }
                    
                    # Ищем ячейки в строке
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 5:
                        continue
                    
                    print(f"  Обрабатываю строку счетчика {i+1} с {len(cells)} ячейками...")
                    
                    # 1-я ячейка: тип счетчика и серийный номер
                    cell1 = cells[0]
                    if cell1.text:
                        # Ищем тип счетчика
                        meter_types = ["ХВС", "ГВС", "Электричество", "Electricity", "Electric"]
                        for meter_type in meter_types:
                            if meter_type in cell1.text:
                                meter_data["type"] = meter_type
                                break
                        
                        # Ищем серийный номер в элементе с классом Item__description quiet
                        serial_elements = cell1.find_elements(By.CSS_SELECTOR, ".Item__description.quiet")
                        for elem in serial_elements:
                            serial_text = elem.text.strip()
                            if serial_text and serial_text.isdigit() and len(serial_text) >= 8:
                                meter_data["serial_number"] = serial_text
                                break
                    
                    # 2-я ячейка: период
                    cell2 = cells[1]
                    if cell2.text:
                        meter_data["period"] = cell2.text.strip()
                    
                    # 3-я ячейка: показания
                    cell3 = cells[2]
                    if cell3.text:
                        reading_text = cell3.text.strip()
                        # Ищем число в показаниях
                        import re
                        reading_match = re.search(r'(\d+)', reading_text)
                        if reading_match:
                            meter_data["reading"] = reading_match.group(1)
                    
                    # 4-я ячейка: расход
                    cell4 = cells[3]
                    if cell4.text:
                        consumption_text = cell4.text.strip()
                        # Ищем число в расходе
                        consumption_match = re.search(r'(\d+)', consumption_text)
                        if consumption_match:
                            meter_data["consumption"] = consumption_match.group(1)
                    
                    # 5-я ячейка: дата
                    cell5 = cells[4] if len(cells) > 4 else None
                    if cell5:
                        date_text = cell5.text.strip()
                        if date_text:
                            # Ищем дату в формате "Дата внесения 12 ноября" или "15—26 число месяца"
                            date_match = re.search(r'(?:Дата внесения|Сроки внесения)?\s*(.+)', date_text, re.IGNORECASE)
                            if date_match:
                                extracted_date = date_match.group(1).strip()
                                meter_data["date"] = extracted_date
                    
                    # Проверяем, что хотя бы тип счетчика найден
                    if meter_data["type"] != "N/A":
                        apartment_meters["meters"].append(meter_data)
                        print(f"    ✓ Найден счетчик: {meter_data['type']} (серия: {meter_data['serial_number']}, период: {meter_data['period']}, показания: {meter_data['reading']}, дата: {meter_data['date']})")
                    else:
                        print(f"    ⚠ Счетчик не распознан в строке {i+1}")
                    
                except Exception as e:
                    print(f"    ⚠ Ошибка при обработке строки {i+1}: {str(e)}")
                    continue
            
            # Если не нашли через таблицу, пробуем альтернативный подход
            if not apartment_meters["meters"]:
                print("ℹ Попробую альтернативный поиск счетчиков...")
                
                # Ищем блоки с информацией о счетчиках
                meter_blocks = driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'meter') or contains(@class, 'counter') or contains(@class, 'reading')]")
                
                for block in meter_blocks:
                    try:
                        block_text = block.text.strip()
                        if not block_text:
                            continue
                            
                        print(f"  Обрабатываю блок: {block_text[:100]}...")
                        
                        # Анализируем текст блока
                        if "ХВС" in block_text or "ГВС" in block_text or "Электричество" in block_text:
                            meter_data = {
                                "type": "N/A",
                                "serial_number": "N/A",
                                "period": "N/A",
                                "reading": "N/A",
                                "consumption": "N/A",
                                "date": "N/A"
                            }
                            
                            # Определяем тип счетчика
                            if "ХВС" in block_text:
                                meter_data["type"] = "ХВС"
                            elif "ГВС" in block_text:
                                meter_data["type"] = "ГВС"
                            elif "Электричество" in block_text or "Electricity" in block_text:
                                meter_data["type"] = "Электричество"
                            
                            # Ищем серийный номер в формате длинного числа
                            serial_match = re.search(r'\b\d{8,}\b', block_text)
                            if serial_match:
                                meter_data["serial_number"] = serial_match.group()
                            
                            # Ищем показания
                            reading_match = re.search(r'(\d+)\s*(?:показания|reading|reading)', block_text, re.IGNORECASE)
                            if not reading_match:
                                reading_match = re.search(r'(\d+)\s*[^0-9]*$', block_text)
                            if reading_match:
                                meter_data["reading"] = reading_match.group(1)
                            
                            apartment_meters["meters"].append(meter_data)
                            print(f"    ✓ Найден счетчик в блоке: {meter_data['type']}")
                            
                    except Exception as e:
                        print(f"    ⚠ Ошибка при обработке блока: {str(e)}")
                        continue
                         
        except Exception as e:
            print(f"    ⚠ Ошибка при парсинге показаний счетчиков: {str(e)}")
        
        if apartment_meters["meters"]:
            print(f"✓ Получены показания для {len(apartment_meters['meters'])} счетчиков для {apartment_meters['apartment']}")
            return apartment_meters
        else:
            print(f"⚠ Показания счетчиков для {apartment_meters['apartment']} не найдены")
            return None
            
    except Exception as e:
        print(f"⚠ Ошибка при получении показаний счетчиков для {apartment_name}: {str(e)}")
        return None

def get_all_meter_readings(driver):
    """Получает показания счетчиков для всех доступных квартир."""
    try:
        print("⌛ Получаю показания счетчиков для всех квартир...")
        
        # Сохраняем текущую квартиру
        current_apartment = None
        try:
            apartment_dropdown = driver.find_element(By.XPATH,
                "//div[@role='listbox' and @aria-expanded and contains(@class, 'dropdown')][.//*[contains(text(), 'Квартира')]]")
            current_elem = apartment_dropdown.find_element(By.TAG_NAME, "b")
            current_apartment = current_elem.text.strip()
        except:
            pass
        
        meter_readings_data = []
        
        # Получаем список всех квартир
        apartments = get_apartments_list(driver)
        
        if not apartments:
            print("ℹ Квартиры не найдены, получаю данные для текущей...")
            # Получаем данные для текущей квартиры
            current_data = get_meter_readings_for_current_apartment(driver)
            if current_data:
                meter_readings_data.append(current_data)
        else:
            # Обрабатываем каждую квартиру
            for i, apartment in enumerate(apartments):
                print(f"\n🏢 Обработка показаний для квартиры {i+1}/{len(apartments)}: {apartment}")
                
                # Переключаемся на квартиру (если это не первая квартира)
                if i > 0 or (current_apartment and apartment != current_apartment):
                    if not switch_to_apartment(driver, apartment):
                        print(f"⚠ Не удалось переключиться на {apartment}, пропускаю...")
                        continue
                
                # Получаем показания для текущей квартиры
                apartment_data = get_meter_readings_for_current_apartment(driver, apartment)
                if apartment_data:
                    meter_readings_data.append(apartment_data)
                else:
                    print(f"⚠ Не удалось получить показания для {apartment}")
        
        if not meter_readings_data:
            print("ℹ На странице не найдено показаний счетчиков")
            # Сохраняем HTML для анализа
            with open(os.path.join(DEBUG_DIR, "meters_page_analysis.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return None
        
        print(f"\n✓ Успешно получены показания для {len(meter_readings_data)} квартир")
        return meter_readings_data
        
    except Exception as e:
        save_debug_data(driver, "meter_readings_error")
        raise ValueError(f"Ошибка при получении показаний счетчиков: {str(e)}")

if __name__ == "__main__":
    args = parse_arguments()
    main(args.login, args.password)