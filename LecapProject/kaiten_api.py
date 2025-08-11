import os
import requests
import base64
import json
import logging
import time
import hashlib
from typing import Any, Dict

# -----------------------------------------------------------------------------
# Настройки вывода
# -----------------------------------------------------------------------------
SHOW_SECRETS = os.getenv("KAITEN_LOG_SHOW_SECRETS", "0") in ("1", "true", "True", "yes")
PRINT_PREVIEW_LIMIT = None  # None = печатать тело ответа целиком; иначе ограничить символы

logger = logging.getLogger("kaiten")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)

# -----------------------------------------------------------------------------
# Утилиты
# -----------------------------------------------------------------------------
def _mask_token(value: str, keep: int = 6) -> str:
    if SHOW_SECRETS:
        return value
    try:
        if not value:
            return value
        if len(value) <= keep:
            return '*' * len(value)
        return '*' * (len(value) - keep) + value[-keep:]
    except Exception:
        return '<masked>'

def _maybe_mask_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    if SHOW_SECRETS:
        return dict(headers or {})
    safe = {}
    for k, v in (headers or {}).items():
        if k.lower() in ('authorization', 'x-api-key', 'api-key'):
            if isinstance(v, str) and v.lower().startswith('bearer '):
                safe[k] = 'Bearer ' + _mask_token(v[7:])
            else:
                safe[k] = _mask_token(str(v))
        else:
            safe[k] = v
    return safe

def _hash_payload(obj: Any) -> str:
    try:
        data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    except Exception:
        data = str(obj)
    return hashlib.sha256(data.encode('utf-8', errors='ignore')).hexdigest()

def _print_full_request_response(req_id: str, method: str, url: str, headers: Dict[str, Any], params: Dict[str, Any] = None, body: Any = None):
    # Печать ПОЛНОГО запроса
    print(f"\n[HTTP] ▶ REQUEST id={req_id}")
    print(f"[HTTP]   {method} {url}")
    if params:
        try:
            print(f"[HTTP]   params: {json.dumps(params, ensure_ascii=False)}")
        except Exception:
            print(f"[HTTP]   params(raw): {params}")
    print(f"[HTTP]   headers: {_maybe_mask_headers(headers)}")
    if body is not None:
        try:
            print(f"[HTTP]   body(json): {json.dumps(body, ensure_ascii=False)}")
        except Exception:
            print(f"[HTTP]   body(raw): {body}")

def _print_full_response(req_id: str, resp: requests.Response, elapsed_s: float):
    # Печать ПОЛНОГО ответа
    print(f"[HTTP] ◀ RESPONSE id={req_id} status={resp.status_code} time={elapsed_s:.2f}s")
    print(f"[HTTP]   resp.headers: {dict(resp.headers)}")
    text = resp.text
    if PRINT_PREVIEW_LIMIT is not None and isinstance(PRINT_PREVIEW_LIMIT, int):
        text = (text[:PRINT_PREVIEW_LIMIT] + "…") if len(text) > PRINT_PREVIEW_LIMIT else text
    print(f"[HTTP]   resp.text: {text}")
    # Попробуем распарсить JSON и вывести хэш/тип/длину
    try:
        data = resp.json()
        _type = 'list' if isinstance(data, list) else type(data).__name__
        _len = len(data) if isinstance(data, list) else ('n/a' if not isinstance(data, dict) else len(data))
        print(f"[HTTP]   resp.json.type={_type} len={_len} hash={_hash_payload(data)}")
    except Exception as _:
        print(f"[HTTP]   resp.json: <not a valid JSON>")

# Обёртка GET с полными логами запроса/ответа
def _http_get_full(method: str, url: str, headers: Dict[str, Any], params: Dict[str, Any] = None, timeout: int = 60):
    req_id = f"{int(time.time()*1000)%100000}-{hashlib.md5((url+str(params)).encode()).hexdigest()[:6]}"
    _print_full_request_response(req_id, method, url, headers, params=params, body=None)
    t0 = time.monotonic()
    resp = requests.request(method=method, url=url, headers=headers, params=params, timeout=timeout)
    dt = time.monotonic() - t0
    _print_full_response(req_id, resp, dt)
    return resp, dt

# -----------------------------------------------------------------------------
# Функции API (оригинальная логика сохранена)
# -----------------------------------------------------------------------------
def fetch_kaiten_boards(domain, bearer_key, space_id):
    url = f"https://{domain}.kaiten.ru/api/latest/spaces/{space_id}/boards"
    headers = {
         "Authorization": f"Bearer {bearer_key}",
         "Accept": "application/json",
         "Content-Type": "application/json",
    }
    logger.debug(f"Запрос досок: url={url}, для пространства {space_id}")
    logger.debug(f"Headers={_maybe_mask_headers(headers)}")

    try:
         response, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=60)
         logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s")
         response.raise_for_status()
         boards = response.json()
         logger.debug(f"Ответ (hash={_hash_payload(boards)}, len={len(boards) if isinstance(boards, list) else 'n/a'})")
         logger.info(f"Получено досок: {len(boards) if isinstance(boards, list) else 'n/a'} для пространства {space_id}")
         return [{"id": str(board.get("id")), "title": board.get("title")} for board in boards]
    except Exception as e:
         logger.error(f"Ошибка при получении досок для пространства {space_id}: {e}", exc_info=True)
         return []

def fetch_kaiten_cards(domain, bearer_key, project_id, billing_field_id, billing_field_value):
    # Получение списка карточек (задач) по проекту, отфильтрованных по кастомному полю Billing (дата фильтруется вне класса)
    filter_data = {
        "key": "and",
        "value": [
            {
                "key": "and",
                "value": [
                    {
                        "key": "custom_property",
                        "comparison": "eq",
                        "id": int(billing_field_id),
                        "type": "select",
                        "value": int(billing_field_value)
                    }
                ]
            }
        ]
    }
    filter_str = json.dumps(filter_data)
    filter_encoded = base64.b64encode(filter_str.encode('utf-8')).decode('utf-8')

    url = f"https://{domain}.kaiten.ru/api/latest/cards"
    params = {
        "space_id": project_id,
        "offset": 0,
        "limit": 1000,
        "filter": filter_encoded,
    }
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос карточек: url={url}, params={params}, headers={_maybe_mask_headers(headers)}")
    try:
        response, dt = _http_get_full("GET", url, headers=headers, params=params, timeout=60)
        logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s (params hash={_hash_payload(params)})")
        response.raise_for_status()
        cards = response.json()
        logger.debug(f"Ответ карточек (hash={_hash_payload(cards)}, "
                     f"type={'list' if isinstance(cards, list) else type(cards).__name__}, "
                     f"len={len(cards) if isinstance(cards, list) else 'n/a'})")
        logger.info(f"Получено карточек: {len(cards) if isinstance(cards, list) else 'n/a'}")
        return cards
    except Exception as e:
        logger.error(f"Ошибка при получении карточек: {e}", exc_info=True)
        return []

def fetch_kaiten_time_logs(domain, bearer_key, card_id):
    # Получение списка списаний времени для конкретной карточки.
    url = f"https://{domain}.kaiten.ru/api/latest/cards/{card_id}/time-logs"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос списаний времени: url={url}, headers={_maybe_mask_headers(headers)}")
    print(f"Запрос списаний времени: url={url}, headers={_maybe_mask_headers(headers)}")  # исходная печать сохранена

    # Корреляционный id
    _req_id = f"{card_id}-{int(time.time()*1000)%100000}"

    try:
        print(f"[TIMELOG] ▶ start req={_req_id} GET {url}")
        t0 = time.monotonic()
        # Полный GET с логами
        response, _ = _http_get_full("GET", url, headers=headers, params=None, timeout=60)
        dt = time.monotonic() - t0
        logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s")
        print(f"[TIMELOG] ◀ done  req={_req_id} status={response.status_code} time={dt:.2f}s")

        response.raise_for_status()
        time_logs = response.json()
        logger.debug(f"Ответ time-logs (hash={_hash_payload(time_logs)}, "
                     f"type={'list' if isinstance(time_logs, list) else type(time_logs).__name__}, "
                     f"len={len(time_logs) if isinstance(time_logs, list) else 'n/a'})")

        _len = len(time_logs) if isinstance(time_logs, list) else "n/a"
        _hash = _hash_payload(time_logs)
        # Полный JSON тоже уже распечатан в _http_get_full -> _print_full_response
        print(f"[TIMELOG] ✔ req={_req_id} len={_len} hash={_hash}")
        logger.info(f"Получено списаний времени для карточки {card_id}: {_len}")
        return time_logs
    except Exception as e:
        logger.error(f"Ошибка при получении списаний времени для карточки {card_id}: {e}", exc_info=True)
        print(f"[TIMELOG] ✖ req={_req_id} error={e}")
        return []

def fetch_kaiten_roles(domain, bearer_key):
    # Получние списка ролей из Kaiten API по заданному домену и Bearer key. (Исключает роль с id = -1)
    url = f"https://{domain}.kaiten.ru/api/latest/user-roles"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос ролей: url={url}, headers={_maybe_mask_headers(headers)}")
    try:
        response, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=60)
        logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s")
        response.raise_for_status()
        roles_raw = response.json()
        logger.debug(f"Ответ API по ролям (hash={_hash_payload(roles_raw)}, "
                     f"type={'list' if isinstance(roles_raw, list) else type(roles_raw).__name__}, "
                     f"len={len(roles_raw) if isinstance(roles_raw, list) else 'n/a'})")
        roles = [
            {"id": str(role.get("id")), "name": role.get("name")}
            for role in roles_raw
            if str(role.get("id")) != "-1"
        ]
        logger.info(f"Получено ролей (без id=-1): {len(roles)}")
        return roles
    except Exception as e:
        logger.error(f"Ошибка при получении ролей: {e}", exc_info=True)
        return []

def fetch_kaiten_projects(domain, bearer_key):
    # Получение списка проектов из Kaiten API
    url = f"https://{domain}.kaiten.ru/api/latest/spaces"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос проектов: url={url}, headers={_maybe_mask_headers(headers)}")
    try:
        response, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=60)
        logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Ответ проектов (hash={_hash_payload(data)}, "
                     f"type={'list' if isinstance(data, list) else type(data).__name__}, "
                     f"len={len(data) if isinstance(data, list) else 'n/a'})")
        projects = [{"id": project.get("id"), "title": project.get("title")} for project in data]
        logger.info(f"Получено проектов: {len(projects)}")
        return projects
    except Exception as e:
        logger.error(f"Ошибка при получении проектов: {e}", exc_info=True)
        return []

def fetch_kaiten_users(domain, bearer_key, timeout=10):
    url = f"https://{domain}.kaiten.ru/api/latest/users"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос пользователей: url={url}, timeout={timeout}, headers={_maybe_mask_headers(headers)}")
    response, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=timeout)
    logger.debug(f"HTTP GET {url} -> {response.status_code} за {dt:.2f}s")
    response.raise_for_status()
    data = response.json()
    logger.debug(f"Ответ пользователей (hash={_hash_payload(data)}, "
                 f"type={'list' if isinstance(data, list) else type(data).__name__})")
    if isinstance(data, dict):
        users = data.get("users", [])
        logger.info(f"Получено пользователей (dict.users): {len(users)}")
        return users
    elif isinstance(data, list):
        logger.info(f"Получено пользователей (list): {len(data)}")
        return data
    else:
        logger.warning("Неожиданный тип ответа пользователей, возвращаю []")
        return []

def fetch_kaiten_board_roles(domain, bearer_key, space_id, board_id):
    """
    Получение списка ролей (roles) конкретной доски в проекте (space).
    Каждый элемент — словарь с 'id' и 'name'.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/spaces/{space_id}/boards/{board_id}/roles"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос ролей доски: url={url}, headers={_maybe_mask_headers(headers)}")
    try:
        resp, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=10)
        logger.debug(f"HTTP GET {url} -> {resp.status_code} за {dt:.2f}s")
        resp.raise_for_status()
        roles = resp.json()
        logger.debug(f"Ответ ролей доски (hash={_hash_payload(roles)}, "
                     f"type={'list' if isinstance(roles, list) else type(roles).__name__}, "
                     f"len={len(roles) if isinstance(roles, list) else 'n/a'})")
        return roles  # список {"id": ..., "name": ...}
    except Exception as e:
        logger.error(f"Ошибка при получении ролей доски {board_id}: {e}", exc_info=True)
        return []

def fetch_kaiten_custom_property_values(domain, bearer_key, space_id, property_id):
    """
    Получение списка значений select-поля custom_property по его ID в контексте space_id.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/company/custom-properties/{property_id}/select-values"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос custom property values: url={url}, headers={_maybe_mask_headers(headers)}")
    try:
        resp, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=10)
        logger.debug(f"HTTP GET {url} -> {resp.status_code} за {dt:.2f}s")
        resp.raise_for_status()
        raw = resp.json()
        logger.debug(f"Ответ custom property values (hash={_hash_payload(raw)}, "
                     f"type={'list' if isinstance(raw, list) else type(raw).__name__}, "
                     f"len={len(raw) if isinstance(raw, list) else 'n/a'})")
        return [
            {"id": str(item["id"]), "name": item.get("value", "")}
            for item in raw
            if not item.get("deleted", False)
        ]
    except Exception as e:
        logger.error(f"Ошибка fetch_custom_property_values: {e}", exc_info=True)
        return []

def fetch_kaiten_board_statuses(domain, bearer_key, space_id, board_id):
    """
    Получение списка статусов (колонок) доски.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/boards/{board_id}/columns"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
    }
    logger.debug(f"Запрос статусов доски: url={url}, headers={_maybe_mask_headers(headers)}")
    resp, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=10)
    logger.debug(f"HTTP GET {url} -> {resp.status_code} за {dt:.2f}s")
    resp.raise_for_status()
    data = resp.json()
    logger.debug(f"Ответ статусов (hash={_hash_payload(data)}, "
                 f"type={'list' if isinstance(data, list) else type(data).__name__}, "
                 f"len={len(data) if isinstance(data, list) else 'n/a'})")

    # Преобразуем: id и название — в Kaiten в колонках поле называется "name"
    return [
        {
            "id":   str(col["id"]),
            "title": col.get("name") or col.get("title","")
        }
        for col in data
    ]

def fetch_kaiten_swimlanes(domain, bearer_key, board_id):
    """
    Получение списка swimlane’ов (дорожек) доски по endpoint /boards/{board_id}/lanes.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/boards/{board_id}/lanes"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
    }
    logger.debug(f"Запрос дорожек: url={url}, headers={_maybe_mask_headers(headers)}")
    resp, dt = _http_get_full("GET", url, headers=headers, params=None, timeout=10)
    logger.debug(f"HTTP GET {url} -> {resp.status_code} за {dt:.2f}s")
    resp.raise_for_status()
    data = resp.json()
    logger.debug(f"Ответ дорожек (hash={_hash_payload(data)}, "
                 f"type={'list' if isinstance(data, list) else type(data).__name__}, "
                 f"len={len(data) if isinstance(data, list) else 'n/a'})")

    lanes = []
    for lane in data:
        lanes.append({
            "id": str(lane["id"]),
            "title": lane.get("title") or lane.get("name", ""),
        })
    return lanes
