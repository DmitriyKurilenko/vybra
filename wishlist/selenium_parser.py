"""
Selenium-парсер для Wildberries
Использует реальный браузер для обхода антибот-защиты
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, SessionNotCreatedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from decimal import Decimal
import time
import logging
import re
import json
import os
import shutil
import random
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)
SELENIUM_SLEEP_SCALE = max(0.1, float(os.getenv('SELENIUM_SLEEP_SCALE', '0.7')))
DEFAULT_WB_USER_AGENTS = [
    (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
]


def _sleep(seconds: float):
    """Единая точка управления задержками Selenium."""
    delay = max(0.0, seconds * SELENIUM_SLEEP_SCALE)
    if delay > 0:
        time.sleep(delay)


class SeleniumWildberriesParser:
    """Парсер Wildberries через Selenium (реальный браузер)"""

    def __init__(self, headless=True):
        """
        Args:
            headless: Запускать браузер в фоновом режиме (без GUI)
        """
        self.headless = headless
        self.driver = None
        self._cookies_loaded_for_session = False
        self._session_count = 0
        self._selected_user_agent = None
        self._selected_proxy = None
        self._user_agents = self._parse_env_list('WB_SELENIUM_USER_AGENTS') or list(DEFAULT_WB_USER_AGENTS)
        self._user_agent_index = random.randrange(len(self._user_agents)) if self._user_agents else 0
        self._proxy_pool = self._parse_env_list('WB_SELENIUM_PROXIES')
        self._proxy_index = random.randrange(len(self._proxy_pool)) if self._proxy_pool else 0
        self._retry_attempts = max(1, int(os.getenv('WB_PARSER_RETRY_ATTEMPTS', '2')))
        self._retry_base_delay = max(0.0, float(os.getenv('WB_PARSER_RETRY_BASE_DELAY', '1.5')))
        self._retry_max_delay = max(
            self._retry_base_delay,
            float(os.getenv('WB_PARSER_RETRY_MAX_DELAY', '12')),
        )
        self._retry_jitter = max(0.0, float(os.getenv('WB_PARSER_RETRY_JITTER', '0.4')))
        self._restart_session_on_retry = os.getenv('WB_PARSER_RESTART_SESSION_ON_RETRY', 'false').lower() in {
            '1', 'true', 'yes'
        }
        self._parser_cookies_enabled = os.getenv('WB_PARSER_COOKIES_ENABLED', 'true').lower() not in {
            '0', 'false', 'no'
        }
        self._parser_cookies_file = Path(
            os.getenv('WB_PARSER_COOKIES_FILE', '/tmp/wb_cookies/parser_session.json')
        )

    def _parse_env_list(self, env_name: str) -> List[str]:
        raw = os.getenv(env_name, '')
        if not raw:
            return []
        return [chunk.strip() for chunk in re.split(r'[\n,;]+', raw) if chunk.strip()]

    def _next_user_agent(self) -> str:
        if not self._user_agents:
            return DEFAULT_WB_USER_AGENTS[0]
        user_agent = self._user_agents[self._user_agent_index % len(self._user_agents)]
        self._user_agent_index += 1
        return user_agent

    def _next_proxy(self) -> Optional[str]:
        if not self._proxy_pool:
            return None
        proxy = self._proxy_pool[self._proxy_index % len(self._proxy_pool)]
        self._proxy_index += 1
        return proxy

    def _retry_delay(self, retry_number: int) -> float:
        base_delay = self._retry_base_delay * (2 ** max(0, retry_number - 1))
        delay = min(self._retry_max_delay, base_delay)
        if self._retry_jitter > 0:
            delay += random.uniform(0, self._retry_jitter)
        return delay

    def _prepare_parser_cookies(self):
        if not self._parser_cookies_enabled:
            return
        try:
            self._parser_cookies_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as error:
            logger.debug(f"Не удалось подготовить директорию cookies: {error}")

    def _ensure_wb_session_cookies(self):
        if not self._parser_cookies_enabled or self._cookies_loaded_for_session:
            return
        if not self.driver:
            return

        self._prepare_parser_cookies()
        try:
            self.driver.get('https://www.wildberries.ru')
            _sleep(1)
            if self._parser_cookies_file.exists():
                if self.load_cookies(str(self._parser_cookies_file)):
                    self.driver.get('https://www.wildberries.ru')
                    _sleep(1)
                    logger.info("WB cookies восстановлены для текущей Selenium-сессии")
            self._cookies_loaded_for_session = True
        except Exception as error:
            logger.debug(f"Не удалось применить cookies сессии WB: {error}")

    def _save_wb_session_cookies(self):
        if not self._parser_cookies_enabled or not self.driver:
            return
        self._prepare_parser_cookies()
        self.save_cookies(str(self._parser_cookies_file))

    def _init_driver(self):
        """Инициализация Chrome WebDriver"""
        if self.driver:
            return

        logger.info("Инициализация Chrome WebDriver...")

        remote_url = os.getenv('SELENIUM_REMOTE_URL')

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless=new')

        # Общие флаги (совместимы с Local и Remote)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--js-flags=--max-old-space-size=128')
        chrome_options.add_argument('--window-size=1280,720')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self._selected_user_agent = self._next_user_agent()
        self._selected_proxy = self._next_proxy()
        chrome_options.add_argument(f'user-agent={self._selected_user_agent}')
        if self._selected_proxy:
            chrome_options.add_argument(f'--proxy-server={self._selected_proxy}')

        try:
            if remote_url:
                # Remote WebDriver — не устанавливаем binary_location
                # и experimental options (они несовместимы с Remote)
                logger.info(f"Использую удалённый Selenium: {remote_url}")
                self.driver = webdriver.Remote(
                    command_executor=remote_url,
                    options=chrome_options,
                )
            else:
                # Локальный Chrome — добавляем experimental options
                chrome_options.add_argument('--disable-setuid-sandbox')
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                chrome_binary = os.getenv('CHROME_BIN')
                if not chrome_binary:
                    chrome_binary = next(
                        (
                            c for c in ('/usr/bin/chromium', '/usr/bin/chromium-browser')
                            if os.path.exists(c)
                        ),
                        None,
                    )
                if chrome_binary:
                    chrome_options.binary_location = chrome_binary

                chromedriver_path = (
                    os.getenv('CHROMEDRIVER_PATH')
                    or shutil.which('chromedriver')
                    or '/usr/bin/chromedriver'
                )
                logger.info(f"ChromeDriver: {chromedriver_path}, binary: {chrome_binary}")
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self._cookies_loaded_for_session = False
            self._session_count += 1
            logger.info(
                "Сессия Selenium #%s (proxy=%s)",
                self._session_count,
                self._selected_proxy or 'off',
            )
            logger.info("Chrome WebDriver готов")

        except Exception as e:
            logger.error(f"Ошибка инициализации WebDriver: {e}")
            raise

    def _close_driver(self):
        """Закрытие браузера"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self._cookies_loaded_for_session = False
                logger.info("Chrome WebDriver закрыт")
            except Exception as e:
                logger.error(f"Ошибка при закрытии драйвера: {e}")

    def _normalize_image_url(self, image_url):
        """Пытается преобразовать URL изображения к более высокому качеству"""
        if not image_url:
            return image_url

        normalized = image_url

        # Часто WB отдаёт превью c246x328 / c516x688 — пытаемся получить big
        replacements = [
            ('/images/c246x328/', '/images/big/'),
            ('/images/c516x688/', '/images/big/'),
            ('/images/tm/', '/images/big/'),
        ]

        for source, target in replacements:
            normalized = normalized.replace(source, target)

        return normalized

    def _extract_largest_src_from_srcset(self, srcset_value):
        """Берёт самый большой URL из srcset"""
        if not srcset_value:
            return None

        candidates = []
        for part in srcset_value.split(','):
            chunk = part.strip()
            if not chunk:
                continue

            tokens = chunk.split()
            url = tokens[0]
            weight = 0
            if len(tokens) > 1:
                size_token = tokens[1].lower().strip()
                if size_token.endswith('w'):
                    try:
                        weight = int(size_token[:-1])
                    except Exception:
                        weight = 0
                elif size_token.endswith('x'):
                    try:
                        weight = int(float(size_token[:-1]) * 1000)
                    except Exception:
                        weight = 0

            candidates.append((weight, url))

        if not candidates:
            return None

        candidates.sort(key=lambda value: value[0], reverse=True)
        return candidates[0][1]

    def _extract_structured_data(self):
        """Пробует извлечь category/rating/reviews_count из JSON-LD"""
        structured_result: Dict[str, Optional[Any]] = {
            'category': None,
            'rating': None,
            'reviews_count': None,
        }

        if not self.driver:
            return structured_result

        try:
            scripts = self.driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
            for script in scripts:
                raw_json = script.get_attribute('innerText')
                if not raw_json:
                    continue

                try:
                    payload = json.loads(raw_json)
                except Exception:
                    continue

                payload_list = payload if isinstance(payload, list) else [payload]
                for entry in payload_list:
                    if not isinstance(entry, dict):
                        continue

                    entry_type = str(entry.get('@type', '')).lower()

                    # Product schema
                    if 'product' in entry_type:
                        category = entry.get('category')
                        if isinstance(category, str) and category.strip() and not structured_result['category']:
                            structured_result['category'] = category.strip()

                        aggregate_rating = entry.get('aggregateRating')
                        if isinstance(aggregate_rating, dict):
                            rating_value = aggregate_rating.get('ratingValue')
                            review_count = aggregate_rating.get('reviewCount')

                            if rating_value is not None and structured_result['rating'] is None:
                                try:
                                    structured_result['rating'] = float(str(rating_value).replace(',', '.'))
                                except Exception:
                                    pass

                            if review_count is not None and structured_result['reviews_count'] is None:
                                try:
                                    structured_result['reviews_count'] = int(float(str(review_count).replace(',', '.')))
                                except Exception:
                                    pass

                    # Breadcrumb schema
                    if 'breadcrumblist' in entry_type and not structured_result['category']:
                        items = entry.get('itemListElement', [])
                        category_candidates = []
                        if isinstance(items, list):
                            for breadcrumb in items:
                                if not isinstance(breadcrumb, dict):
                                    continue
                                name_value = breadcrumb.get('name')
                                if isinstance(name_value, str) and name_value.strip():
                                    category_candidates.append(name_value.strip())

                        if category_candidates:
                            # Последний breadcrumb обычно сам товар, берём предпоследний как категорию
                            if len(category_candidates) >= 2:
                                structured_result['category'] = category_candidates[-2]
                            else:
                                structured_result['category'] = category_candidates[-1]

        except Exception as error:
            logger.debug(f"Не удалось извлечь JSON-LD данные: {error}")

        return structured_result

    def _extract_fields_from_page_source(self, page_source: str):
        """Fallback: вытаскивает category/rating/reviews_count из сырых JSON-фрагментов страницы."""
        fallback = {
            'category': None,
            'rating': None,
            'reviews_count': None,
        }

        if not page_source:
            return fallback

        try:
            category_match = re.search(
                r'"(?:subjectName|subject|entity|category)"\s*:\s*"([^"\\]{2,200})"',
                page_source,
                re.IGNORECASE,
            )
            if category_match:
                fallback['category'] = category_match.group(1).strip()
        except Exception:
            pass

        try:
            rating_match = re.search(
                r'"(?:reviewRating|rating|ratingValue)"\s*:\s*([0-9]+(?:[\.,][0-9]+)?)',
                page_source,
                re.IGNORECASE,
            )
            if rating_match:
                fallback['rating'] = float(rating_match.group(1).replace(',', '.'))
        except Exception:
            pass

        try:
            reviews_match = re.search(
                r'"(?:feedbacks|feedbacksCount|reviewCount|reviewsCount)"\s*:\s*([0-9]{1,9})',
                page_source,
                re.IGNORECASE,
            )
            if reviews_match:
                fallback['reviews_count'] = int(reviews_match.group(1))
        except Exception:
            pass

        return fallback

    def _normalize_product_url(self, url: str):
        """Нормализует URL карточки WB и удаляет невидимые символы."""
        if not url:
            return url, None

        # Убираем zero-width/format chars, которые иногда попадают из share-текста.
        cleaned = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]', '', str(url)).strip()
        article_match = re.search(r'/catalog/(\d+)/', cleaned)
        article_code = article_match.group(1) if article_match else None

        if article_code:
            return f"https://www.wildberries.ru/catalog/{article_code}/detail.aspx", article_code

        return cleaned, None

    def _clean_extracted_name(self, raw_name: Optional[str], article_code: Optional[str] = None):
        """Чистит склеенные WB-названия: удаляет скидки, цены, промо-блоки и хвосты рейтинга."""
        if not raw_name:
            return None

        text = str(raw_name)
        text = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]', '', text)
        text = text.replace('\u00A0', ' ').strip()
        text = re.sub(r'(?<=[A-Za-zА-Яа-яЁё])(?=\d)', ' ', text)
        text = re.sub(r'(?<=\d)(?=[A-Za-zА-Яа-яЁё])', ' ', text)

        noisy_markers = (
            '₽' in text
            or 'похожие товары' in text.lower()
            or 'wb кошельком' in text.lower()
        )

        if noisy_markers:
            text = re.sub(r'^(?:[−\-–—+]?\s*\d{1,3}\s*%\s*)+', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^(?:\d[\d\s]{1,10}\s*₽\s*){1,3}', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^\s*похожие\s*товары\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^\s*с\s*wb\s*кошельком\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'похожие\s*товары\s*с?\s*wb\s*кошельком', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bс\s*wb\s*кошельком\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bпохожие\s*товары\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'(?:\s+\d[\d\s]{1,10}\s*₽){1,3}\s*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+[1-5](?:[.,]\d{1,3})\s+\d{2,3}(?:[\s\u00A0]?\d{3})*\s*$', '', text)

        if article_code:
            text = re.sub(rf'\b{re.escape(str(article_code))}\b$', '', text).strip()

        text = re.sub(r'\s{2,}', ' ', text).strip(' \t\r\n-–—|/')
        if len(text) < 3:
            return None
        if re.fullmatch(r'[\d\s%₽.,\-–—+]+', text):
            return None
        return text[:500]

    def _extract_from_visible_text(
        self,
        page_title: str,
        body_text: str,
        article_code: Optional[str] = None,
        allow_body_fallback: bool = False,
    ):
        """Fallback по видимому тексту страницы (устойчив к изменениям внутренних JSON-полей)."""
        fallback: Dict[str, Optional[Any]] = {
            'name': None,
            'price': None,
            'rating': None,
            'reviews_count': None,
        }

        title = (page_title or '').strip()
        body = (body_text or '').strip()

        if title:
            title_match = re.search(
                r'^(.*?)\s+купить\s+за\s+([0-9\s\u00A0]+)\s*₽',
                title,
                re.IGNORECASE,
            )
            if title_match:
                name = title_match.group(1).strip()
                if article_code:
                    name = re.sub(rf'\s+{re.escape(article_code)}\s*$', '', name).strip()
                fallback['name'] = self._clean_extracted_name(name, article_code=article_code)

                price_digits = re.sub(r'\D', '', title_match.group(2))
                if price_digits:
                    try:
                        fallback['price'] = Decimal(price_digits)
                    except Exception:
                        pass

        if body and allow_body_fallback:
            if fallback['rating'] is None or fallback['reviews_count'] is None:
                rating_match = re.search(
                    r'([0-9]+(?:[.,][0-9]+)?)\s*·\s*(\d+)\s*оцен',
                    body,
                    re.IGNORECASE,
                )
                if rating_match:
                    if fallback['rating'] is None:
                        try:
                            fallback['rating'] = float(rating_match.group(1).replace(',', '.'))
                        except Exception:
                            pass
                    if fallback['reviews_count'] is None:
                        try:
                            fallback['reviews_count'] = int(rating_match.group(2))
                        except Exception:
                            pass

            if fallback['name'] is None:
                lines = [line.strip() for line in body.splitlines() if line.strip()]
                for idx, line in enumerate(lines):
                    if re.search(r'^\d+(?:[.,]\d+)?\s*·\s*\d+\s*оцен', line):
                        for prev in range(idx - 1, max(-1, idx - 4), -1):
                            candidate = lines[prev]
                            if candidate.lower() in {'оригинал', 'сезон скидок', 'похожие'}:
                                continue
                            if len(candidate) >= 3:
                                fallback['name'] = self._clean_extracted_name(candidate, article_code=article_code)
                                break
                        if fallback['name']:
                            break

            if fallback['price'] is None:
                price_match = re.search(
                    r'([0-9][0-9\s\u00A0]{2,})\s*₽',
                    body,
                    re.IGNORECASE,
                )
                if price_match:
                    price_digits = re.sub(r'\D', '', price_match.group(1))
                    if price_digits:
                        try:
                            fallback['price'] = Decimal(price_digits)
                        except Exception:
                            pass

        if fallback.get('name'):
            fallback['name'] = self._clean_extracted_name(fallback['name'], article_code=article_code)
        return fallback

    def _is_antibot_page(self, page_title: str, body_text: str):
        """Определяет страницы антибот-проверки Wildberries."""
        title = (page_title or '').lower()
        body = (body_text or '').lower()
        markers = (
            'почти готово',
            'подозрительная активность',
            'новая попытка через',
            'captcha-support@rwb.ru',
            'что-то не так',
        )
        if any(marker in title for marker in markers):
            return True
        if any(marker in body for marker in markers):
            return True
        return False

    def _parse_once(self, normalized_url: str, article_code: Optional[str], timeout: int) -> Tuple[Optional[Dict[str, Any]], str]:
        self._init_driver()
        driver = self.driver
        if driver is None:
            logger.error("WebDriver не инициализирован")
            return None, 'driver_init_failed'

        self._ensure_wb_session_cookies()

        logger.info(f"Открываю страницу: {normalized_url}")
        driver.get(normalized_url)

        wait_timed_out = False
        wait = WebDriverWait(driver, timeout)
        try:
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                ', '.join([
                    'ins.price-block__final-price',
                    '.price-block__final-price',
                    'ins[class*="price"]',
                    '[class*="price-block__final"]',
                    'h1',
                    '[class*="productTitle"]',
                ])
            )))
        except TimeoutException:
            wait_timed_out = True
            logger.warning("Таймаут ожидания загрузки страницы")

        source = driver.page_source
        result = self._extract_all_from_source(source)

        page_title = driver.title or ''
        body_text = ''
        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text or ''
        except Exception:
            pass

        has_article_marker = bool(
            article_code and re.search(rf'Артикул\s*{re.escape(article_code)}', body_text, re.IGNORECASE)
        )
        has_title_product_hint = bool(
            re.search(r'\bкупить\s+за\s+[0-9\s\u00A0]+\s*₽', page_title, re.IGNORECASE)
        )

        visible_fallback = self._extract_from_visible_text(
            page_title,
            body_text,
            article_code=article_code,
            allow_body_fallback=bool(has_article_marker or has_title_product_hint or result.get('name')),
        )
        for field in ('name', 'price', 'rating', 'reviews_count'):
            if result.get(field) in (None, '') and visible_fallback.get(field) is not None:
                result[field] = visible_fallback[field]

        if not result.get('image_url'):
            for selector in [
                '.product-page__img-wrap img',
                '.img-plug img',
                '[class*="product"] img[src*="basket"]',
                'img[src*="wbbasket"]',
            ]:
                try:
                    img_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    img_src = (
                        self._extract_largest_src_from_srcset(img_elem.get_attribute('srcset'))
                        or img_elem.get_attribute('src')
                        or img_elem.get_attribute('data-src')
                    )
                    if img_src and 'basket' in img_src:
                        result['image_url'] = self._normalize_image_url(img_src)
                        break
                except (NoSuchElementException, Exception):
                    continue

        if not result.get('image_url'):
            article_match = re.search(r'/catalog/(\d+)/', normalized_url)
            if article_match:
                article = article_match.group(1)
                vol = article[:4]
                part = article[:6]
                result['image_url'] = f"https://basket-01.wbbasket.ru/vol{vol}/part{part}/{article}/images/big/1.webp"

        if result.get('rating') is not None:
            try:
                result['rating'] = float(str(result['rating']).replace(',', '.'))
            except Exception:
                result['rating'] = None

        if self._is_antibot_page(page_title, body_text) and not (result.get('name') or result.get('price')):
            logger.warning("Страница антибот-проверки Wildberries, данные товара недоступны")
            return None, 'antibot'

        if result.get('name'):
            result['name'] = self._clean_extracted_name(result.get('name'), article_code=article_code)

        if result['name']:
            safe_name = (result.get('name') or '?')[:40]
            logger.info(f"Парсинг успешен: {safe_name}, {result.get('price')} р.")
            return result, 'ok'

        if result.get('price') and not result.get('name'):
            logger.warning("Извлечена только цена без названия, парсинг считается неуспешным")
            return None, 'price_only'
        if has_article_marker:
            logger.warning("Не удалось извлечь данные товара (карточка открыта, но поля не распознаны)")
            return None, 'fields_missing'
        if wait_timed_out:
            logger.warning("Не удалось извлечь данные товара (таймаут загрузки карточки)")
            return None, 'timeout'

        logger.warning("Не удалось извлечь данные товара (карточка недоступна/товар удален)")
        return None, 'unavailable'

    def parse(self, url, timeout=30, retries=None):
        """
        Парсинг товара Wildberries с повторными попытками.

        Args:
            url: URL товара
            timeout: Максимальное время ожидания (сек)
            retries: Количество попыток (по умолчанию из WB_PARSER_RETRY_ATTEMPTS)

        Returns:
            Dict с данными товара или None
        """
        normalized_url, article_code = self._normalize_product_url(url)
        max_attempts = self._retry_attempts if retries is None else max(1, int(retries))
        last_reason = 'unknown'
        restart_reasons = {'antibot', 'timeout', 'exception', 'driver_init_failed'}

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay = self._retry_delay(attempt - 1)
                logger.info(
                    "Повторная попытка %s/%s для %s через %.1f сек (причина: %s)",
                    attempt,
                    max_attempts,
                    article_code or normalized_url,
                    delay,
                    last_reason,
                )
                _sleep(delay)
                should_restart_session = self._restart_session_on_retry or last_reason in restart_reasons
                if should_restart_session:
                    self._close_driver()

            try:
                parsed, reason = self._parse_once(
                    normalized_url=normalized_url,
                    article_code=article_code,
                    timeout=timeout,
                )
                last_reason = reason
                if parsed:
                    self._save_wb_session_cookies()
                    return parsed
            except Exception as error:
                last_reason = 'exception'
                logger.warning(
                    "Ошибка попытки %s/%s парсинга %s: %s",
                    attempt,
                    max_attempts,
                    article_code or normalized_url,
                    error,
                )
                if attempt == max_attempts:
                    logger.error(f"Ошибка при парсинге через Selenium: {error}", exc_info=True)

        logger.warning(
            "Парсинг неуспешен после %s попыток для %s (последняя причина: %s)",
            max_attempts,
            article_code or normalized_url,
            last_reason,
        )
        return None

    def _extract_all_from_source(self, source):
        """
        Извлекает все данные товара из HTML-source за один проход.
        Быстрее чем последовательные DOM-запросы через WebDriver.
        """
        result: Dict[str, Optional[Any]] = {
            'name': None,
            'brand': None,
            'price': None,
            'old_price': None,
            'rating': None,
            'reviews_count': None,
            'category': None,
            'image_url': None,
        }

        if not source:
            return result

        # JSON-LD (самый надёжный источник)
        for ld_match in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            source, re.DOTALL | re.IGNORECASE,
        ):
            try:
                payload = json.loads(ld_match.group(1))
                entries = payload if isinstance(payload, list) else [payload]
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    entry_type = str(entry.get('@type', '')).lower()

                    if 'product' in entry_type:
                        if not result['name'] and entry.get('name'):
                            result['name'] = str(entry['name']).strip()
                        if not result['brand']:
                            brand = entry.get('brand')
                            if isinstance(brand, dict):
                                brand = brand.get('name')
                            if brand:
                                result['brand'] = str(brand).strip()
                        if not result['category'] and entry.get('category'):
                            result['category'] = str(entry['category']).strip()

                        offers = entry.get('offers')
                        if isinstance(offers, dict) and not result['price']:
                            price_val = offers.get('price')
                            if price_val is not None:
                                try:
                                    result['price'] = Decimal(str(price_val))
                                except Exception:
                                    pass

                        agg = entry.get('aggregateRating')
                        if isinstance(agg, dict):
                            if result['rating'] is None and agg.get('ratingValue') is not None:
                                try:
                                    result['rating'] = float(str(agg['ratingValue']).replace(',', '.'))
                                except Exception:
                                    pass
                            if result['reviews_count'] is None and agg.get('reviewCount') is not None:
                                try:
                                    result['reviews_count'] = int(float(str(agg['reviewCount'])))
                                except Exception:
                                    pass

                    if 'breadcrumblist' in entry_type and not result['category']:
                        items = entry.get('itemListElement', [])
                        names = [
                            str(b['name']).strip()
                            for b in items
                            if isinstance(b, dict) and b.get('name')
                        ]
                        if len(names) >= 2:
                            result['category'] = names[-2]
                        elif names:
                            result['category'] = names[-1]
            except (json.JSONDecodeError, Exception):
                continue

        # Regex fallback из встроенных JSON-фрагментов WB
        if not result['name']:
            m = re.search(
                r'"(?:imt_name|goodsName|name)"\s*:\s*"([^"\\]{2,300})"',
                source, re.IGNORECASE,
            )
            if m:
                result['name'] = self._clean_extracted_name(m.group(1).strip())

        if not result['brand']:
            m = re.search(
                r'"(?:brandName|brand_name|brand)"\s*:\s*"([^"\\]{1,100})"',
                source, re.IGNORECASE,
            )
            if m:
                result['brand'] = m.group(1).strip()

        if not result['price']:
            # salePriceU в копейках (WB API формат в page data)
            m = re.search(r'"salePriceU"\s*:\s*(\d+)', source)
            if m:
                try:
                    result['price'] = Decimal(m.group(1)) / 100
                except Exception:
                    pass

        if not result['price']:
            # Цена из HTML-текста
            m = re.search(
                r'price-block__final-price[^>]*>\s*([^<]+)',
                source, re.IGNORECASE,
            )
            if m:
                digits = re.sub(r'[^\d]', '', m.group(1))
                if digits:
                    try:
                        result['price'] = Decimal(digits)
                    except Exception:
                        pass

        if not result['old_price']:
            m = re.search(r'"priceU"\s*:\s*(\d+)', source)
            if m:
                try:
                    result['old_price'] = Decimal(m.group(1)) / 100
                except Exception:
                    pass

        if not result['category']:
            m = re.search(
                r'"(?:subjectName|subject|subj_name|category)"\s*:\s*"([^"\\]{2,200})"',
                source, re.IGNORECASE,
            )
            if m:
                result['category'] = m.group(1).strip()

        if result['rating'] is None:
            m = re.search(
                r'"(?:reviewRating|rating|ratingValue)"\s*:\s*([0-9]+(?:[.,][0-9]+)?)',
                source, re.IGNORECASE,
            )
            if m:
                try:
                    result['rating'] = float(m.group(1).replace(',', '.'))
                except Exception:
                    pass

        if result['reviews_count'] is None:
            m = re.search(
                r'"(?:feedbacks|feedbacksCount|reviewCount|feedbackCount)"\s*:\s*(\d{1,9})',
                source, re.IGNORECASE,
            )
            if m:
                try:
                    result['reviews_count'] = int(m.group(1))
                except Exception:
                    pass

        # Картинка из source
        if not result['image_url']:
            m = re.search(r'(https?://basket-\d+\.wbbasket\.ru/[^"\'<>\s]+\.(?:webp|jpg|png))', source)
            if m:
                result['image_url'] = self._normalize_image_url(m.group(1))

        if result.get('name'):
            result['name'] = self._clean_extracted_name(result.get('name'))

        return result

    def save_cookies(self, filepath):
        """Сохранить cookies в файл для повторного использования"""
        if not self.driver:
            return False

        try:
            cookies = self.driver.get_cookies()
            with open(filepath, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"✅ Cookies сохранены в {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения cookies: {e}")
            return False

    def load_cookies(self, filepath):
        """Загрузить cookies из файла"""
        if not self.driver:
            return False

        if not os.path.exists(filepath):
            logger.warning(f"Файл cookies не найден: {filepath}")
            return False

        try:
            with open(filepath, 'r') as f:
                cookies = json.load(f)

            for cookie in cookies:
                # Удаляем поля, которые могут вызвать проблемы
                cookie.pop('sameSite', None)
                cookie.pop('expiry', None)
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Не удалось добавить cookie: {e}")

            logger.info(f"✅ Cookies загружены из {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки cookies: {e}")
            return False

    def parse_favorites(self, user_id=None, wait_for_auth=True, max_items=200):
        """
        Парсинг избранного пользователя с Wildberries

        Args:
            user_id: ID пользователя (для сохранения cookies)
            wait_for_auth: Ждать авторизации пользователя (60 сек)
            max_items: Максимальное количество товаров

        Returns:
            List[str]: Список URL товаров из избранного
        """
        try:
            self._init_driver()
            driver = self.driver
            if driver is None:
                logger.error("WebDriver не инициализирован")
                return []

            # Путь к файлу cookies
            cookies_dir = Path('/tmp/wb_cookies')
            cookies_dir.mkdir(exist_ok=True)
            cookies_file = cookies_dir / f'user_{user_id}_cookies.json' if user_id else cookies_dir / 'cookies.json'

            logger.info("Открываю Wildberries...")
            driver.get('https://www.wildberries.ru')
            _sleep(2)

            # Пытаемся загрузить cookies
            cookies_loaded = self.load_cookies(str(cookies_file))

            if cookies_loaded:
                # Обновляем страницу, чтобы cookies применились
                logger.info("Обновляю страницу с загруженными cookies...")
                driver.refresh()
                _sleep(3)

            # Переходим на страницу избранного
            logger.info("Переходжу на страницу избранного...")
            driver.get('https://www.wildberries.ru/lk/favorites')
            _sleep(5)

            # Проверяем, авторизован ли пользователь
            current_url = driver.current_url
            is_authorized = '/lk/favorites' in current_url

            if not is_authorized and wait_for_auth:
                logger.info("⏳ Пользователь не авторизован. Ожидание авторизации (60 секунд)...")
                logger.info("📱 Пожалуйста, войдите в аккаунт Wildberries в открывшемся браузере")

                # Ждем до 60 секунд, пока пользователь авторизуется
                wait_time = 60
                start_time = time.time()

                while time.time() - start_time < wait_time:
                    _sleep(2)
                    current_url = driver.current_url
                    if '/lk/favorites' in current_url or '/lk/' in current_url:
                        logger.info("✅ Пользователь авторизован!")
                        is_authorized = True

                        # Сохраняем cookies для будущего использования
                        self.save_cookies(str(cookies_file))

                        # Переходим на избранное, если попали в другой раздел ЛК
                        if '/lk/favorites' not in current_url:
                            driver.get('https://www.wildberries.ru/lk/favorites')
                            _sleep(3)
                        break

                if not is_authorized:
                    logger.error("❌ Авторизация не выполнена в течение 60 секунд")
                    return []
            elif not is_authorized:
                logger.error("❌ Пользователь не авторизован. Необходим вход в аккаунт")
                return []

            logger.info("✅ На странице избранного. Начинаю сбор товаров...")

            # Даем время на загрузку JavaScript и товаров
            _sleep(5)

            # Скроллим страницу для подгрузки всех товаров
            logger.info("Скроллю страницу для загрузки всех товаров...")
            last_height = 0
            no_change_count = 0

            while no_change_count < 3:
                # Скроллим вниз
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                _sleep(2)

                # Проверяем изменение высоты
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_change_count += 1
                else:
                    no_change_count = 0
                    last_height = new_height

            logger.info("Собираю ссылки на товары...")

            # Ищем все карточки товаров в избранном
            product_urls = set()

            # Селекторы для поиска товаров
            # В избранном товары могут быть в разных форматах
            selectors = [
                'article.product-card[data-nm-id]',  # Основные карточки
                'a[href*="/catalog/"][href*="/detail.aspx"]',  # Прямые ссылки на товары
            ]

            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Найдено {len(elements)} элементов по селектору: {selector}")

                    for elem in elements:
                        if len(product_urls) >= max_items:
                            break

                        try:
                            # Если это карточка с data-nm-id
                            if elem.tag_name == 'article':
                                article_code = elem.get_attribute('data-nm-id')
                                if article_code:
                                    url = f"https://www.wildberries.ru/catalog/{article_code}/detail.aspx"
                                    product_urls.add(url)
                            # Если это прямая ссылка
                            elif elem.tag_name == 'a':
                                href = elem.get_attribute('href')
                                if href and '/catalog/' in href and '/detail.aspx' in href:
                                    product_urls.add(href)
                        except Exception as e:
                            logger.debug(f"Ошибка обработки элемента: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"Ошибка поиска по селектору {selector}: {e}")
                    continue

            product_list = list(product_urls)[:max_items]
            logger.info(f"✅ Найдено {len(product_list)} товаров в избранном")

            return product_list

        except Exception as e:
            logger.error(f"Ошибка при парсинге избранного: {e}", exc_info=True)
            return []

    def close(self):
        """Явное закрытие парсера"""
        self._close_driver()

    def __enter__(self):
        """Context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие при выходе из context manager"""
        self.close()

    def parse_catalog(self, url, max_items=100, scroll_pause=2):
        """
        Парсинг каталога товаров Wildberries

        Args:
            url: URL страницы каталога
            max_items: Максимальное количество товаров для парсинга
            scroll_pause: Пауза между прокрутками (сек)

        Returns:
            List[Dict] со списком товаров
        """
        try:
            self._init_driver()
            driver = self.driver
            if driver is None:
                logger.error("WebDriver не инициализирован")
                return []

            logger.info(f"Открываю каталог: {url}")
            driver.get(url)

            # Ждем загрузки и прохождения антибота (больше времени для JS)
            logger.info("Ожидание загрузки JavaScript...")
            _sleep(5)

            # Попробуем прокрутить страницу, чтобы триггернуть загрузку контента
            logger.info("Скроллю страницу для загрузки контента...")
            for i in range(5):
                driver.execute_script("window.scrollBy(0, 500);")
                _sleep(1)

            # Ещё немного ждём после скроллинга
            _sleep(5)

            # Логируем что видим на странице
            page_title = driver.title
            page_url = driver.current_url
            logger.info(f"Загружена страница: {page_title} | URL: {page_url}")

            # Дополнительная диагностика
            all_links_on_page = driver.find_elements(By.TAG_NAME, 'a')
            logger.info(f"Всего ссылок на странице: {len(all_links_on_page)}")

            # Посмотрим на первые 10 ссылок
            if all_links_on_page:
                logger.info("Примеры ссылок на странице:")
                for i, link in enumerate(all_links_on_page[:10]):
                    href = link.get_attribute('href')
                    logger.info(f"  [{i+1}] {href}")

            # Проверим, есть ли на странице хоть какой-то контент
            body_text = driver.find_element(By.TAG_NAME, 'body').text[:500]
            logger.info(f"Начало текста страницы: {body_text}")

            products = []
            last_height = 0
            no_new_products_count = 0

            logger.info("Начинаю скроллинг и сбор товаров...")

            while len(products) < max_items:
                # Ищем карточки товаров по классу product-card
                product_cards = driver.find_elements(By.CSS_SELECTOR, 'article.product-card[data-nm-id]')

                logger.info(f"Найдено {len(product_cards)} карточек товаров на странице")

                # Извлекаем данные из каждой карточки
                for card in product_cards:
                    if len(products) >= max_items:
                        break

                    try:
                        # Артикул из data-nm-id
                        article_code = card.get_attribute('data-nm-id')
                        if not article_code:
                            continue

                        # Проверяем, не добавили ли уже этот товар
                        if any(p.get('article_code') == article_code for p in products):
                            continue

                        # URL товара
                        product_url = f"https://www.wildberries.ru/catalog/{article_code}/detail.aspx"

                        # Название - ищем бренд и название товара
                        name = ""
                        try:
                            brand_elem = card.find_element(By.CSS_SELECTOR, '.product-card__brand')
                            brand = brand_elem.text.strip()
                            name_elem = card.find_element(By.CSS_SELECTOR, '.product-card__name')
                            product_name = name_elem.text.strip()
                            # Убираем разделитель " / "
                            product_name = product_name.replace(' / ', '').strip()
                            name = f"{brand} {product_name}" if brand else product_name
                        except:
                            name = f"Товар {article_code}"
                        name = self._clean_extracted_name(name, article_code=article_code) or f"Товар {article_code}"

                        # Цена - ищем элемент с классом price__lower-price
                        price = None
                        try:
                            price_elem = card.find_element(By.CSS_SELECTOR, 'ins.price__lower-price')
                            price_text = price_elem.text.strip()
                            # Убираем все кроме цифр
                            price_clean = re.sub(r'[^\d]', '', price_text)
                            if price_clean:
                                price = Decimal(price_clean)
                        except:
                            pass

                        # Изображение
                        image_url = None
                        try:
                            img_elem = card.find_element(By.CSS_SELECTOR, '.j-thumbnail')
                            image_url = (
                                self._extract_largest_src_from_srcset(img_elem.get_attribute('srcset'))
                                or img_elem.get_attribute('src')
                                or img_elem.get_attribute('data-src-pb')
                            )
                            image_url = self._normalize_image_url(image_url)
                        except:
                            pass

                        # Добавляем товар
                        product = {
                            'article_code': article_code,
                            'name': name,
                            'price': price,
                            'url': product_url,
                            'image_url': image_url
                        }
                        products.append(product)
                        logger.info(f"✓ Товар {len(products)}/{max_items}: {product['name'][:40]} - {price}₽")

                    except Exception as e:
                        logger.debug(f"Ошибка обработки карточки: {e}")
                        continue

                # Проверяем, есть ли новые товары
                if len(products) == last_height:
                    no_new_products_count += 1
                    if no_new_products_count >= 3:
                        logger.info("Больше нет новых товаров, завершаем")
                        break
                else:
                    no_new_products_count = 0
                    last_height = len(products)

                # Скроллим вниз для подгрузки новых товаров
                if len(products) < max_items:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    _sleep(scroll_pause)

            logger.info(f"✅ Собрано {len(products)} товаров из каталога")
            return products

        except Exception as e:
            logger.error(f"Ошибка при парсинге каталога: {e}", exc_info=True)
            return []


# Удобные функции для быстрого парсинга
def parse_with_selenium(url, headless=True):
    """
    Быстрый парсинг товара через Selenium

    Args:
        url: URL товара
        headless: Фоновый режим

    Returns:
        Dict с данными или None
    """
    with SeleniumWildberriesParser(headless=headless) as parser:
        return parser.parse(url)


def parse_catalog_with_selenium(url, max_items=100, headless=True):
    """
    Быстрый парсинг каталога через Selenium

    Args:
        url: URL каталога
        max_items: Максимальное количество товаров
        headless: Фоновый режим

    Returns:
        List[Dict] со списком товаров
    """
    with SeleniumWildberriesParser(headless=headless) as parser:
        return parser.parse_catalog(url, max_items=max_items)


def parse_favorites_with_selenium(user_id=None, headless=False, max_items=200):
    """
    Быстрый парсинг избранного через Selenium

    Args:
        user_id: ID пользователя для сохранения cookies
        headless: Фоновый режим (рекомендуется False для первого запуска)
        max_items: Максимальное количество товаров

    Returns:
        List[str]: Список URL товаров из избранного
    """
    with SeleniumWildberriesParser(headless=headless) as parser:
        return parser.parse_favorites(user_id=user_id, max_items=max_items)


def parse_ozon_product_with_selenium(url, headless=True, timeout=30):
    """
    Быстрый парсинг карточки Ozon через Selenium.

    Returns:
        Dict с полями name/price/image_url/rating/reviews_count/category/brand или None
    """
    parser = SeleniumWildberriesParser(headless=headless)
    driver = None
    try:
        parser._init_driver()
        driver = parser.driver
        if driver is None:
            return None

        driver.get(url)
        _sleep(3)
        wait = WebDriverWait(driver, timeout)

        result = {
            'name': None,
            'brand': None,
            'price': None,
            'rating': None,
            'reviews_count': None,
            'category': None,
            'image_url': None,
        }

        try:
            for selector in [
                'h1',
                '[data-widget="webProductHeading"] h1',
                '[class*="tsHeadline"]',
            ]:
                try:
                    elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if elem and elem.text.strip():
                        result['name'] = elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass

        try:
            for selector in [
                '[data-widget="webPrice"]',
                '[class*="price"]',
                '[data-widget="webCurrentPrice"]',
            ]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    text = elem.text.strip() if elem else ''
                    m = re.search(r'(\d[\d\s]{1,20})\s*[₽р]', text)
                    if not m:
                        m = re.search(r'(\d[\d\s]{1,20})', text)
                    if m:
                        digits = re.sub(r'\D', '', m.group(1))
                        if digits:
                            result['price'] = Decimal(digits)
                            break
                except Exception:
                    continue
        except Exception:
            pass

        try:
            for selector in [
                'img[src*="ozon"]',
                '[data-widget="webGallery"] img',
                'img',
            ]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    img = elem.get_attribute('src') or elem.get_attribute('data-src')
                    if img and img.startswith('http'):
                        result['image_url'] = img
                        break
                except Exception:
                    continue
        except Exception:
            pass

        source = driver.page_source or ''

        try:
            category_match = re.search(
                r'"(?:category|subjectName|title)"\s*:\s*"([^"\\]{2,200})"',
                source,
                re.IGNORECASE,
            )
            if category_match:
                result['category'] = category_match.group(1).strip()
        except Exception:
            pass

        try:
            rating_match = re.search(
                r'"(?:ratingValue|rating|reviewRating)"\s*:\s*([0-9]+(?:[\.,][0-9]+)?)',
                source,
                re.IGNORECASE,
            )
            if rating_match:
                result['rating'] = float(rating_match.group(1).replace(',', '.'))
        except Exception:
            pass

        try:
            reviews_match = re.search(
                r'"(?:reviewCount|reviewsCount|feedbacks|feedbacksCount)"\s*:\s*([0-9]{1,9})',
                source,
                re.IGNORECASE,
            )
            if reviews_match:
                result['reviews_count'] = int(reviews_match.group(1))
        except Exception:
            pass

        try:
            brand_match = re.search(
                r'"(?:brand|brandName)"\s*:\s*"([^"\\]{2,120})"',
                source,
                re.IGNORECASE,
            )
            if brand_match:
                result['brand'] = brand_match.group(1).strip()
        except Exception:
            pass

        if result['name'] or result['price']:
            return result
        return None
    except Exception as e:
        logger.error(f"Ошибка парсинга Ozon карточки: {e}", exc_info=True)
        return None
    finally:
        if driver:
            parser._close_driver()


def parse_ozon_favorites_with_selenium(user_id=None, headless=False, max_items=500, _allow_headless_fallback=True):
    """
    Массовый сбор ссылок из избранного Ozon.

    Для первого запуска headless=False: пользователь авторизуется в открытом браузере.
    """
    parser = SeleniumWildberriesParser(headless=headless)
    driver = None
    try:
        try:
            parser._init_driver()
        except SessionNotCreatedException as init_error:
            logger.warning(f"Не удалось запустить Chrome (headless={headless}): {init_error}")

            if not headless and _allow_headless_fallback:
                logger.info("Пробую fallback в headless режиме для Ozon импорта...")
                return parse_ozon_favorites_with_selenium(
                    user_id=user_id,
                    headless=True,
                    max_items=max_items,
                    _allow_headless_fallback=False,
                )

            return []

        driver = parser.driver
        if driver is None:
            return []

        cookies_dir = Path('/tmp/ozon_cookies')
        cookies_dir.mkdir(exist_ok=True)
        cookies_file = cookies_dir / f'user_{user_id}_cookies.json' if user_id else cookies_dir / 'cookies.json'

        logger.info("Открываю Ozon...")
        driver.get('https://www.ozon.ru')
        _sleep(3)

        # Пробуем восстановить сессию из cookies
        cookies_loaded = parser.load_cookies(str(cookies_file))
        if cookies_loaded:
            logger.info("Cookies Ozon загружены, обновляю страницу...")
            driver.refresh()
            _sleep(3)

        def requires_auth(current_url):
            url = (current_url or '').lower()
            return ('login' in url) or ('auth' in url) or ('passport' in url)

        def is_ozon_authorized():
            """Проверка авторизации через переход в личный кабинет."""
            try:
                driver.get('https://www.ozon.ru/my/')
                _sleep(2)
                current = (driver.current_url or '').lower()
                if requires_auth(current):
                    return False

                page = (driver.page_source or '').lower()
                # Если явно видим форму логина/ozon id — считаем неавторизованным
                auth_markers = ['ozon id', 'войти в ozon', 'войти или зарегистрироваться']
                if any(marker in page for marker in auth_markers):
                    return False
                return True
            except Exception:
                return False

        def extract_product_links_from_source(source_text):
            links = set()
            if not source_text:
                return links

            # Абсолютные ссылки
            for match in re.findall(r'https?://www\.ozon\.ru/product/[^"\'\s<>]+', source_text, flags=re.IGNORECASE):
                clean = match.split('?')[0].rstrip('/') + '/'
                links.add(clean)

            # Относительные ссылки
            for match in re.findall(r'/product/[^"\'\s<>]+', source_text, flags=re.IGNORECASE):
                clean = ('https://www.ozon.ru' + match).split('?')[0].rstrip('/') + '/'
                links.add(clean)

            return links

        # Проверяем, удалось ли восстановить авторизацию cookies
        authorized = is_ozon_authorized()

        # Пытаемся перейти в избранное
        favorites_urls = [
            'https://www.ozon.ru/my/favorites',
            'https://www.ozon.ru/favorites',
            'https://www.ozon.ru/my/favorites/products',
            'https://www.ozon.ru/my/favorites?miniapp=favorite',
        ]

        for fav_url in favorites_urls:
            driver.get(fav_url)
            _sleep(3)
            if not requires_auth(driver.current_url):
                break

        # Если нужна авторизация — в headless режиме это невозможно интерактивно
        if (requires_auth(driver.current_url) or not authorized) and headless:
            logger.warning("Ozon требует авторизацию, а браузер запущен в headless. Нужна предварительно сохраненная сессия.")
            return []

        # Если нужна авторизация — ждём до 120 секунд для ручного логина
        if requires_auth(driver.current_url) or not authorized:
            logger.info("Ожидание авторизации Ozon (120 секунд)...")
            start = time.time()
            while time.time() - start < 120:
                _sleep(2)
                if is_ozon_authorized():
                    authorized = True
                    break

            for fav_url in favorites_urls:
                driver.get(fav_url)
                _sleep(3)
                if 'favorites' in driver.current_url.lower():
                    break

        if requires_auth(driver.current_url) or not authorized:
            logger.warning("Не удалось пройти авторизацию Ozon. Импорт избранного недоступен.")
            return []

        # Сохраняем сессию для следующих запусков
        parser.save_cookies(str(cookies_file))

        # Скроллим для подгрузки товаров
        prev_height = 0
        stale = 0
        source_links = set()
        while stale < 4:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == prev_height:
                stale += 1
            else:
                stale = 0
                prev_height = new_height

            # На каждом шаге пробуем достать ссылки из исходника страницы
            source_links.update(extract_product_links_from_source(driver.page_source or ''))
            if len(source_links) >= max_items:
                break

        product_urls = set()
        candidates = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/product/"]')
        for elem in candidates:
            href = elem.get_attribute('href')
            if not href:
                continue
            if '/product/' not in href:
                continue
            clean = href.split('?')[0].rstrip('/') + '/'
            product_urls.add(clean)
            if len(product_urls) >= max_items:
                break

        # Добавляем найденное в page_source (часто там есть ссылки, даже если DOM ещё не дорендерился)
        product_urls.update(list(source_links)[:max_items])

        result = list(product_urls)[:max_items]
        logger.info(f"✅ Ozon избранное: найдено {len(result)} ссылок")
        return result
    except Exception as e:
        logger.error(f"Ошибка парсинга избранного Ozon: {e}", exc_info=True)
        return []
    finally:
        if driver:
            parser._close_driver()


def connect_ozon_session_with_selenium(user_id=None, headless=False, _allow_headless_fallback=True):
    """
    Явное подключение Ozon-сессии: открывает Ozon, ждёт авторизацию и сохраняет cookies.
    """
    parser = SeleniumWildberriesParser(headless=headless)
    driver = None
    try:
        try:
            parser._init_driver()
        except SessionNotCreatedException as init_error:
            logger.warning(f"Не удалось запустить Chrome (headless={headless}): {init_error}")
            if not headless and _allow_headless_fallback:
                logger.info("Пробую fallback в headless режиме для подключения Ozon...")
                return connect_ozon_session_with_selenium(
                    user_id=user_id,
                    headless=True,
                    _allow_headless_fallback=False,
                )
            return {
                'success': False,
                'message': 'Не удалось запустить браузер для подключения Ozon.'
            }

        driver = parser.driver
        if driver is None:
            return {
                'success': False,
                'message': 'WebDriver не инициализирован.'
            }

        cookies_dir = Path('/tmp/ozon_cookies')
        cookies_dir.mkdir(exist_ok=True)
        cookies_file = cookies_dir / f'user_{user_id}_cookies.json' if user_id else cookies_dir / 'cookies.json'

        def requires_auth(current_url):
            url = (current_url or '').lower()
            return ('login' in url) or ('auth' in url) or ('passport' in url)

        def is_ozon_authorized():
            try:
                driver.get('https://www.ozon.ru/my/')
                _sleep(2)
                current = (driver.current_url or '').lower()
                if requires_auth(current):
                    return False
                page = (driver.page_source or '').lower()
                auth_markers = ['ozon id', 'войти в ozon', 'войти или зарегистрироваться']
                if any(marker in page for marker in auth_markers):
                    return False
                return True
            except Exception:
                return False

        driver.get('https://www.ozon.ru')
        _sleep(3)

        cookies_loaded = parser.load_cookies(str(cookies_file))
        if cookies_loaded:
            driver.refresh()
            _sleep(3)

        if headless and not cookies_loaded:
            return {
                'success': False,
                'message': 'Не удалось подключить Ozon: в headless-режиме нет сохраненной сессии. Откройте подключение в окружении с видимым браузером или импортируйте существующие cookies.'
            }

        authorized = is_ozon_authorized()

        # В headless режиме можем только проверить сохранённую сессию
        if not authorized and headless:
            return {
                'success': False,
                'message': 'Сессия Ozon не подключена. Нужна авторизация в не-headless режиме.'
            }

        if not authorized:
            logger.info('Ожидание авторизации Ozon (120 секунд)...')
            start = time.time()
            while time.time() - start < 120:
                _sleep(2)
                if is_ozon_authorized():
                    authorized = True
                    break

        if not authorized:
            return {
                'success': False,
                'message': 'Не удалось подтвердить авторизацию Ozon.'
            }

        parser.save_cookies(str(cookies_file))
        return {
            'success': True,
            'message': 'Ozon успешно подключен. Сессия сохранена.'
        }
    except Exception as e:
        logger.error(f"Ошибка подключения Ozon сессии: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Ошибка подключения Ozon: {e}'
        }
    finally:
        if driver:
            parser._close_driver()
