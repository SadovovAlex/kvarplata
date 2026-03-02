# Kvarplata - Автоматизация доступа к данным о кварплате и счетчиках

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-green.svg)](https://selenium.dev/)
[![ChromeDriver](https://img.shields.io/badge/ChromeDriver-120%2B-orange.svg)](https://chromedriver.chromium.org/)

## Описание

Это набор скриптов для автоматизированного доступа к личным кабинетам сервисов ЖКХ в России:
- ЛК Газ (https://lk-gaz.ru)
- Globus Energo (https://lk.globusenergo.ru)
- МосОблЕИРЦ (https://lkk.mosobleirc.ru)

Скрипты позволяют:
- Автоматически входить в личный кабинет
- Получать данные о задолженности, платежах и показаниях счетчиков
- Формировать отчёты в удобном виде

## Текущие проверяемые сайты

| Сайт | URL | Описание |
|------|-----|----------|
| ЛК Газ | https://xn--80afnfom.xn--80ahmohdapg.xn--80asehdb/auth/sign-in | Автоматизация входа и получение данных о услугах и приборах учёта |
| Globus Energo | https://lk.globusenergo.ru/ | Получение данных о лицевом счёте, балансе и показаниях счетчиков |
| МосОблЕИРЦ | https://lkk.mosobleirc.ru/#/login | Автоматизация входа и получение данных о платежах и счетчиках |

## Установка

1. Установите Python 3.8+:
   ```bash
   python --version
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

   > **Важно:** Для работы требуется ChromeDriver, соответствующий вашей версии Google Chrome. Скачайте его с https://chromedriver.chromium.org/downloads и разместите в папке `chromedriver-win64/`.

3. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/kvarplata.git
   cd kvarplata
   ```

## Запуск

### ЛК Газ

```bash
python gaz/lk-gaz-tables.py --login YOUR_LOGIN --password YOUR_PASSWORD
```

### Globus Energo

```bash
python globus/globus-selenium.py --login YOUR_LOGIN --password YOUR_PASSWORD
```

### МосОблЕИРЦ

```bash
python mosobl/mosobleirc.py --login YOUR_LOGIN --password YOUR_PASSWORD
```

## Структура проекта

```
kvarplata/
├── .gitignore
├── LICENSE
├── README.md
├── gaz/
│   ├── lk-gaz-tables.py          # Скрипт для ЛК Газ
│   └── debug_data/               # Папка для сохранения debug-файлов
├── globus/
│   ├── globus-selenium.py        # Скрипт для Globus Energo
│   └── debug_data/               # Папка для сохранения debug-файлов
├── mosobl/
│   ├── mosobleirc.py             # Скрипт для МосОблЕИРЦ
│   └── debug_data/               # Папка для сохранения debug-файлов
└── requirements.txt              # Зависимости Python
```

## Пример вывода

После успешного выполнения скрипт выводит структурированные данные в консоль и сохраняет JSON-файл с результатами. Пример вывода для ЛК Газ:

```json
{
  "services": [
    {
      "provider": "Межрегионгаз Владимир (3312025868)",
      "service": "Газоснабжение природным газом",
      "balance": "1250,50 ₽",
      "status": "к оплате"
    }
  ],
  "meters": [
    {
      "name": "Счетчик ВК-G4T Elster (№12345678)",
      "model": "N/A",
      "serial": "12345678",
      "verification_date": "2024.03.15",
      "maintenance_date": "2025.03.15"
    }
  ]
}
```

## Troubleshooting

- **Ошибка: ChromeDriver не найден** - Убедитесь, что ChromeDriver находится в правильной папке и совместим с вашей версией Chrome.
- **Ошибка авторизации** - Проверьте логин и пароль, убедитесь, что на сайте не включена дополнительная защита.
- **Элементы не находятся** - Сайт мог изменить структуру. Попробуйте обновить селекторы в коде.

## Вклад

Вклад в проект приветствуется! Пожалуйста, следуйте этим правилам:

1. Создайте issue для обсуждения новых функций или багов
2. Форматируйте код согласно PEP 8
3. Добавляйте тесты для новых функций
4. Обновляйте документацию при необходимости

## Лицензия

Этот проект распространяется под лицензией MIT. Подробнее смотрите в файле [LICENSE](LICENSE).

## Контакты

- Автор: Садовов Александр
- Email: aasdvv@gmail.com
- Telegram: [@wrwfx](https://t.me/wrwfx)
