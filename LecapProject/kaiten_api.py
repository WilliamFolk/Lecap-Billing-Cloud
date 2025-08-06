import requests
import base64
import json
import logging

logger = logging.getLogger('kaiten')

def fetch_kaiten_boards(domain, bearer_key, space_id):
    url = f"https://{domain}.kaiten.ru/api/latest/spaces/{space_id}/boards"
    headers = {
         "Authorization": f"Bearer {bearer_key}",
         "Accept": "application/json",
         "Content-Type": "application/json",
    }
    logger.debug(f"Запрос досок: url={url}, для пространства {space_id}")
    try:
         response = requests.get(url, headers=headers, timeout=60)
         response.raise_for_status()
         boards = response.json()
         logger.info(f"Получено досок: {len(boards)} для пространства {space_id}")
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
    logger.debug(f"Запрос карточек: url={url}, params={params}, headers={headers}")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        cards = response.json()
        logger.info(f"Получено карточек: {len(cards)}")
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
    logger.debug(f"Запрос списаний времени: url={url}, headers={headers}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        time_logs = response.json()
        logger.info(f"Получено списаний времени для карточки {card_id}: {len(time_logs)}")
        return time_logs
    except Exception as e:
        logger.error(f"Ошибка при получении списаний времени для карточки {card_id}: {e}", exc_info=True)
        return []


def fetch_kaiten_roles(domain, bearer_key):
    # Получние списка ролей из Kaiten API по заданному домену и Bearer key. (Исключает роль с id = -1)
    url = f"https://{domain}.kaiten.ru/api/latest/user-roles"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug(f"Запрос ролей: url={url}, headers={headers}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        roles = response.json()
        logger.debug(f"Ответ API по ролям: {roles}")
        roles = [
            {"id": str(role.get("id")), "name": role.get("name")}
            for role in response.json()
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
    logger.debug(f"Запрос проектов: url={url}, headers={headers}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
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
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        return data.get("users", [])
    elif isinstance(data, list):
        return data
    else:
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
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        roles = resp.json()
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
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return [
            {"id": str(item["id"]), "name": item.get("value", "")}
            for item in resp.json()
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
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Преобразуем: id и название
    data = resp.json()
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
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Преобразуем: id и название. В API для lanes поле может быть "title" или "name"
    lanes = []
    for lane in data:
        lanes.append({
            "id": str(lane["id"]),
            "title": lane.get("title") or lane.get("name", ""),
        })
    return lanes
