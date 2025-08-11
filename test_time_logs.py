#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time
import json
import hashlib
import requests
import difflib
import sys

# Весь список card_id, полученный из логов
ALL_CARD_IDS = [
    50475540, 50475669, 50475761, 50475835, 50480305,
    50480357, 52432954, 53162864, 53169094, 53415405,
    53415611, 53465637, 53503642, 53556970, 53559612,
    53567449, 53587588, 53727572, 53926135
]

def fetch_logs(domain, bearer, card_id, no_cache=True):
    """
    Запрос списаний времени для одной карточки.
    Если no_cache=True, добавляем фейковый GET-параметр, чтобы обойти кеширование.
    """
    url = f"https://{domain}.kaiten.ru/api/latest/cards/{card_id}/time-logs"
    if no_cache:
        url += f"?_={int(time.time() * 1000)}"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def hash_json(obj):
    """
    Стабильный MD5 от JSON-объекта (с сортировкой ключей).
    """
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def main():
    p = argparse.ArgumentParser(description="Тест консистентности time-logs из Kaiten API")
    p.add_argument("--domain",   "-d", default="lecap",
                   help="Домен без .kaiten.ru (по умолчанию: %(default)s)")
    p.add_argument("--bearer",   "-b", required=True,
                   help="Ваш Bearer token")
    p.add_argument("--runs",     "-n", type=int, default=3,
                   help="Сколько раз подряд запрашивать каждую карточку (по умолчанию %(default)s)")
    p.add_argument("--delay",    "-t", type=float, default=1.0,
                   help="Задержка между запросами в секундах (по умолчанию %(default)s)")
    args = p.parse_args()

    for cid in ALL_CARD_IDS:
        print(f"\n=== Card ID {cid} ===")
        hashes = []
        dumps  = []

        for i in range(args.runs):
            try:
                data = fetch_logs(args.domain, args.bearer, cid, no_cache=True)
            except Exception as e:
                print(f" Run {i+1}: Ошибка запроса: {e}", file=sys.stderr)
                hashes.append(None)
                dumps.append(None)
            else:
                h = hash_json(data)
                hashes.append(h)
                dumps.append(data)
                print(f" Run {i+1}/{args.runs}: hash={h}, items={len(data)}")
            if i < args.runs - 1:
                time.sleep(args.delay)

        uniq = set(hashes)
        if len(uniq) == 1:
            print(" ✔ Все ответы идентичны.")
        else:
            print(" ✖ Ответы отличаются!")
            for idx, h in enumerate(hashes, 1):
                print(f"   Run {idx}: hash={h}")
            # Выводим diff первых двух удачных запусков
            if dumps[0] is not None and dumps[1] is not None:
                txt1 = json.dumps(dumps[0], ensure_ascii=False, sort_keys=True, indent=2)
                txt2 = json.dumps(dumps[1], ensure_ascii=False, sort_keys=True, indent=2)
                print("\n Diff между run1 и run2:")
                for line in difflib.unified_diff(
                        txt1.splitlines(), txt2.splitlines(),
                        fromfile="run1", tofile="run2", lineterm=""):
                    print(line)
        print("-" * 40)

if __name__ == "__main__":
    main()
