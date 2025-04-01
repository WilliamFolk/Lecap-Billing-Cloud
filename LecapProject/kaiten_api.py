import requests
import base64
import json

def fetch_kaiten_cards(domain, bearer_key, project_id, billing_field_id, billing_field_value):
    """
    Получает список карточек (задач) по проекту, отфильтрованных по кастомному полю Billing.
    (Дата не фильтруется здесь – она будет отфильтрована по списаниям времени).
    """
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
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        cards = response.json()
        return cards
    except Exception as e:
        print("Ошибка при получении карточек:", e)
        return []

def fetch_kaiten_time_logs(domain, bearer_key, card_id):
    """
    Получает список списаний времени для конкретной карточки.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/cards/{card_id}/time-logs"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        time_logs = response.json()
        return time_logs
    except Exception as e:
        print(f"Ошибка при получении списаний времени для карточки {card_id}:", e)
        return []


def fetch_kaiten_roles(domain, bearer_key):
    """
    Получает список ролей из Kaiten API по заданному домену и Bearer key.
    Исключает роль с id = -1.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/user-roles"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        roles = response.json()
        # Исключает роль с id = -1
        print("Ответ API по ролям:", roles)
        roles = [role for role in roles if str(role.get('id')) != "-1"]
        return roles
    except Exception as e:
        print("Ошибка при получении ролей:", e)
        return []

def fetch_kaiten_projects(domain, bearer_key):
    print("Запрос проектов для домена:", domain, "с ключом:", bearer_key)
    url = f"https://{domain}.kaiten.ru/api/latest/spaces"
    headers = {
        "Authorization": f"Bearer {bearer_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        #print("Ответ API по проектам:", data)
        projects = [{"id": project.get("id"), "title": project.get("title")} for project in data]
        return projects
    except Exception as e:
        print("Ошибка при получении проектов:", e)
        return []

