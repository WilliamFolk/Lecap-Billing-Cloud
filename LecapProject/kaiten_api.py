import requests
import base64
import json
import logging

logger = logging.getLogger('kaiten')

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
        response = requests.get(url, headers=headers, timeout=10)
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        roles = response.json()
        logger.debug(f"Ответ API по ролям: {roles}")
        roles = [role for role in roles if str(role.get('id')) != "-1"]
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        projects = [{"id": project.get("id"), "title": project.get("title")} for project in data]
        logger.info(f"Получено проектов: {len(projects)}")
        return projects
    except Exception as e:
        logger.error(f"Ошибка при получении проектов: {e}", exc_info=True)
        return []
