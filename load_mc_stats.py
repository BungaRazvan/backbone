import json
import glob
import requests
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    user_cache_pattern = "usercache.json"
    player_stats_pattern = "world/stats/*.json"

    users = {}

    uuid_set = set()
    user_stats = {}

    api_key = os.getenv("API_KEY")
    url = os.getenv("URL")
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    for file in glob.glob(user_cache_pattern):
        with open(file, "r") as f:
            file_json = json.loads(f.read())
            users = file_json

            for user in file_json:
                uuid_set.add(user["uuid"])

    for file in glob.glob(player_stats_pattern):
        with open(file, "r") as f:
            file_json = json.loads(f.read())
            file_name = str(f.name).replace(".json", "").replace("world/stats/", "")
            print(file_name)
            user_stats[file_name] = file_json

    resp_users = requests.post(
        "{}/discord/minecraft-players".format(url),
        data=json.dumps({"mc_server_id": 1, "mc_players": users}),
        headers=headers,
    )

    print(resp_users)
    print(json.dumps(users))

    for user in users:
        if user["uuid"] in user_stats:
            stat_resp = requests.post(
                "{}/discord/minecraft-stats".format(url),
                data=json.dumps(
                    {
                        "uuid": user["uuid"],
                        "stats": user_stats[user["uuid"]],
                        "mc_server_id": 1,
                    }
                ),
                headers=headers,
            )
            print(stat_resp)


if __name__ == "__main__":
    main()
