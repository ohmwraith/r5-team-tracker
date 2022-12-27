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
        Сохраняет данные в файле players.json в формате JSON
        """
        with open(filename + '.json', 'w') as json_file:
            json.dump(json_data, json_file, indent=4)

    @staticmethod
    def exists(filename):
        """
        Проверяет, существует ли файл players.json в формате JSON
        """
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
    
    @staticmethod
    def to_progress(perc2next_div, progress_lenght = 20):
        """
        Принимает процент заполнения шкалы прогресса от 0 до 1 и общую длину шкалы
        Возвращает заполненную шкалу прогресса
        """
        progress_bar = ''
        success_lenght = int(round(perc2next_div * progress_lenght))
    
        for n in range(0, success_lenght):
            progress_bar += '█'
        for n in range(0, progress_lenght - success_lenght):
            progress_bar += '▁'
    
        return progress_bar


class divisionHandler():
    def __init__(self, rank_split_score):
        self.ranks_json = rank_split_score
        self.divisions_json = self.calculate_divisions()

    def calculate_divisions(self):
        '''
        Расчитывает количество дивизионов в каждом ранге
        '''
        div_json= {}

        # Список рангов
        ranks_list = list(self.ranks_json.keys())
    
        # Перебираем все ранги, кроме последнего
        for rank_index in range(0, len(ranks_list) - 1):
            # Создаем словарь для текущего ранга
            div_json[ranks_list[rank_index]] = {}

            # Расчитываем количество очков в одном дивизионе
            one_div_score = ((self.ranks_json[ranks_list[rank_index + 1]]['score']
             - self.ranks_json[ranks_list[rank_index]]['score'])
             / self.ranks_json[ranks_list[rank_index]]['divisions'])

            # Расчитываем количество очков в каждом дивизионе
            for div_number in range(self.ranks_json[ranks_list[rank_index]]['divisions'], -1, -1):
                div_json[ranks_list[rank_index]][div_number] = int(self.ranks_json[ranks_list[rank_index + 1]]['score'] - one_div_score * div_number)
        return div_json

    def calculate_percent2next(self, score):
        for rank in self.divisions_json:
            for div in self.divisions_json[rank]:
                if score < self.divisions_json[rank][div]:
                    return (score - self.divisions_json[rank][div + 1]) / (self.divisions_json[rank][div] - self.divisions_json[rank][div + 1])

    def get_next_division_points(self, score):
        '''
        Возвращает начальное количество очков следующего дивизиона
        '''
        for rank in self.divisions_json:
            for div in self.divisions_json[rank]:
                if score < self.divisions_json[rank][div]:
                    return self.divisions_json[rank][div]
config_json = {
    "settings": {
        "api_key": "",
        "rank_split_score": {
            "unranked": {
                "score": 0,
                "divisions": 1
            },
            "bronze": {
                "score": 1000,
                "divisions": 4
            },
            "silver": {
                "score": 3000,
                "divisions": 4
            },
            "gold": {
                "score": 5400,
                "divisions": 4
            },
            "platinum": {
                "score": 8200,
                "divisions": 4
            },
            "diamond": {
                "score": 11400,
                "divisions": 4
            },
            "master": {
                "score": 15000,
                "divisions": 1
            },
            "predator": {
                "score": 100000,
                "divisions": 1
            }
        }
    },
    "players": [
        {
            "nickname": "",
            "platform": ""
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

div_handler = divisionHandler(config_json['settings']['rank_split_score'])

# Создание объектов игроков
players_list = []
for pl in config_json['players']:
    players_list.append(playerData(pl["nickname"], pl["platform"]))
print("Loading..")
while True:

    # Очистка переменных и таблицы
    increment = 1
    players_table.clear_rows()

    for player in players_list:
        # Получение информации от API
        json_data = playerAPI.get_data(config_json['settings']['api_key'], player.nickname, player.platform)
        player.update(json_data)

        # Заполнение полей таблицы
        player_nickname = player.nickname
        if player.nickname != player.api_nickname:
            player_nickname += f"({player.api_nickname})"

        player_rank = f"{player.rank} {divisionTransform.to_roman(player.division)}".upper()
        
        player_rank_progress = div_handler.calculate_percent2next(player.score)
        player_po = f"{divisionTransform.to_progress(player_rank_progress, 14)} {player.score}/{div_handler.get_next_division_points(player.score)}"

        player_legend = player.selected_legend
        if player.legend_kills != {}:
            player_legend += f"({player.legend_kills})"

        player_state = player.current_state_as_text
        
        players_table.add_row([increment, player_nickname, player_rank, player_po, player_legend, player_state])

        players_table.align['PO'] = 'l'

        increment += 1
    os.system('cls')
    print(players_table)
