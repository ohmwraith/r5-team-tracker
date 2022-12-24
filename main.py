import requests as r
import json
import os
from prettytable import PrettyTable
from abc import ABCMeta, abstractmethod

class JSONFile():
    @staticmethod
    def get(filename):
        """
        Возвращает данные из файла filename.json в формате JSON
        """
        try:
            with open(filename + '.json', 'r') as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return []
        except json.decoder.JSONDecodeError:
            return []

    @staticmethod
    def save(json_data, filename):
        """
        Сохраняет игроков в файле players.json в формате JSON
        """
        with open(filename + '.json', 'w') as json_file:
            json.dump(json_data, json_file, indent=4)

    @staticmethod
    def exists(filename):
        return os.path.exists(f'{filename}.json')


class playerData():
    def __init__(self, nickname, platform):
        self.nickname = nickname
        self.api_nickname = nickname
        self.platform = platform
        self.level = 0
        self.score = 0
        self.rank = 0
        self.division = 0
        self.is_online = False
        self.is_in_game = False
        self.party_full = False
        self.current_state_as_text = "undefined"
        self.selected_legend = "undefined"
        self.legend_data = {}
        self.legend_kills = {}
        self.data = {}


    def update(self, json_data):
        self.data = json_data
        self.api_nickname = json_data['global']['name']
        self.level = json_data['global']['level']
        self.score = json_data['global']['rank']['rankScore']
        self.rank = json_data['global']['rank']['rankName']
        self.division = json_data['global']['rank']['rankDiv']
        self.is_online = json_data['realtime']['isOnline'] == 1
        self.is_in_game = json_data['realtime']['isInGame'] == 1
        self.party_full = json_data['realtime']['partyFull'] == 1
        self.current_state_as_text = json_data['realtime']['currentStateAsText']
        self.selected_legend = json_data['realtime']['selectedLegend']
        try:
            self.legend_data = json_data['legends']['all'][self.selected_legend]['data']
            for stat in self.legend_data:
                if stat['key'] == "kills":
                    self.legend_kills = stat['value']
        except KeyError:
            self.legend_data = "API Error"
        

class playerAPI():
    @staticmethod
    def get_data(api_key, nickname, platform):
        responce = r.get(
        f"https://api.mozambiquehe.re/bridge?auth={api_key}&player={nickname}&platform={platform}")
        return responce.json()


class divisionTransform():
    @staticmethod
    def to_roman(division):
        return ('I' * division).replace('IIII', 'IV')


config_json = {
    "settings": {
        "API_KEY": "",
        "RANK_SPLIT_SCORE": {
            "Unranked": 0,
            "Bronze": 1000,
            "Silver": 3000,
            "Gold": 5400,
            "Platinum": 8200,
            "Diamond": 11400,
            "Master": 15000,
            "Predator": 100000
        }
    },
    "players": [
        {
            "Nickname": "",
            "Platform": ""
        }
    ]
}

# Загрузка конфигов
for json_filename in ['settings', 'players']:
    if JSONFile.exists(json_filename):
        config_json[json_filename] = JSONFile.get(json_filename)
    else:
        JSONFile.save(config_json[json_filename], json_filename)

# Создание таблицы
players_table = PrettyTable()
players_table.field_names = ['No', 'Nickname(Steam)', 'Rank', 'PO', 'Legend(Kills)', 'State']


# Создание объектов игроков
players_list = []
for pl in config_json['players']:
    players_list.append(playerData(pl["Nickname"], pl["Platform"]))

print("Loading..")
while True:
    
    # Очистка переменных и таблицы
    increment = 1
    players_table.clear_rows()

    for player in players_list:
        # Получение информации от API
        json_data = playerAPI.get_data(config_json['settings']['API_KEY'], player.nickname, player.platform)
        player.update(json_data)

        # Заполнение полей таблицы
        player_nickname = player.nickname
        if player.nickname != player.api_nickname:
            player_nickname += f"({player.api_nickname})"

        player_rank = f"{player.rank} {divisionTransform.to_roman(player.division)}"

        player_legend = player.selected_legend
        if player.legend_kills != {}:
            player_legend += f"({player.legend_kills})"

        player_state = player.current_state_as_text
        
        players_table.add_row([increment, player_nickname, player_rank, player.score, player_legend, player_state])

        increment += 1
    os.system('cls')
    print(players_table)
