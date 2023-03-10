import requests as r
import json
import os
from prettytable import PrettyTable
from datetime import datetime

class JsonFileStringManager():
    """Класс для работы с файлами в формате JSON"""
    @staticmethod
    def get(filename):
        """Возвращает данные из файла filename.json в формате JSON"""
        try:
            with open(filename + '.json', 'r') as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return []
        except json.decoder.JSONDecodeError:
            return []

    @staticmethod
    def save(json_data, filename):
        """Сохраняет данные в файле filename.json в формате JSON"""
        with open(filename + '.json', 'w') as json_file:
            json.dump(json_data, json_file, indent=4)


# Класс, сохраняющий player.json в файл и загружающий его из файла
class playerJsonManager():
    @staticmethod
    def is_player_in_json(json_data, nickname, platform):
        """Проверяет, есть ли данные об этом игроке в файле player.json"""
        for player in json_data:
            if player['nickname'] == nickname and player['platform'] == platform:
                return True
        return False




class playerData():
    """Класс для работы с данными игрока"""
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
        self.current_state_as_text = None
        self.last_online = None
        self.selected_legend = None
        self.legend_data = {}
        self.legend_kills = {}
        self.last_api_data = {}
        self.saved_data = {}

    def get_json_data(self):
        """Возвращает данные игрока в формате JSON"""
        return {
            "nickname": self.nickname,
            "platform": self.platform,
            "api_nickname": self.api_nickname,
            "data": {
                "level": self.level,
                "score": self.score,
                "rank": self.rank,
                "division": self.division,
                "is_online": self.is_online,
                "is_in_game": self.is_in_game,
                "party_full": self.party_full,
                "current_state_as_text": self.current_state_as_text,
                "selected_legend": self.selected_legend,
                "legend_data": self.legend_data,
                "legend_kills": self.legend_kills
            }
        }

    def update(self, json_data):
        """ Обновляет данные игрока """
        self.last_api_data = json_data
        self.api_nickname = json_data['global']['name']
        self.level = json_data['global']['level']
        self.score = json_data['global']['rank']['rankScore']
        self.rank = json_data['global']['rank']['rankName']
        self.division = json_data['global']['rank']['rankDiv']
        self.is_online = json_data['realtime']['isOnline'] == 1
        self.is_in_game = json_data['realtime']['isInGame'] == 1
        self.party_full = json_data['realtime']['partyFull'] == 1
        if self.is_in_game:
            # Если игрок в игре, то записываем текущее время в переменную last_online
            self.last_online = datetime.now()

        self.current_state_as_text = json_data['realtime']['currentStateAsText']
        self.selected_legend = json_data['realtime']['selectedLegend']
        self.legend_data = json_data['legends']['all']
        try:
            self.selected_legend_data = json_data['legends']['all'][self.selected_legend]['data']
            for stat in self.selected_legend_data:
                if stat['key'] == "kills":
                    self.legend_kills = stat['value']
        except KeyError:
            self.selected_legend_data = "Ошибка API"

        

class playerAPI():
    # Класс для работы с API
    @staticmethod
    def get_data(api_key, nickname, platform):
        # Получает данные игрока с API
        responce = r.get(
        f"https://api.mozambiquehe.re/bridge?auth={api_key}&player={nickname}&platform={platform}")
        return responce.json()


class divisionTransform():
    # Класс для преобразования данных дивизионов
    @staticmethod
    def to_roman(division):
        """ Принимает номер дивизиона от 1 до 4 и возвращает его римскими цифрами """
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
    # Класс для работы с дивизионами
    def __init__(self, rank_split_score):
        self.ranks_json = rank_split_score
        # Словарь с разделением очков на дивизионы
        self.divisions_json = self.calculate_divisions()

    def calculate_divisions(self):
        """Расчитывает количество дивизионов в каждом ранге"""
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
        """Расчитывает процент заполнения шкалы прогресса до следующего дивизиона"""
        for rank in self.divisions_json:
            for div in self.divisions_json[rank]:
                if score < self.divisions_json[rank][div]:
                    return (score - self.divisions_json[rank][div + 1]) / (self.divisions_json[rank][div] - self.divisions_json[rank][div + 1])

    def get_next_division_points(self, score):
        """Возвращает начальное количество очков следующего дивизиона"""
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
    if os.path.exists(f'{json_filename}.json'):
        config_json[json_filename] = JsonFileStringManager.get(json_filename)
    else:
        JsonFileStringManager.save(config_json[json_filename], json_filename)

# Создание таблицы
players_table = PrettyTable()
players_table.field_names = ['№', 'Никнейм (Steam)', 'Ранг', 'Счёт [Изменения]', 'Легенда [Убийства]', 'Состояние']

div_handler = divisionHandler(config_json['settings']['rank_split_score'])

# Загрузка сохраненных данных
saved_players_json = JsonFileStringManager.get('storage')

# Проверка наличия API ключа
if config_json['settings']['api_key'] == "":
    print("API ключ не найден! Укажите ключ в файле settings.json")
    exit()

# Создание объектов игроков
players_list = []
for pl in config_json['players']:
    players_list.append(playerData(pl["nickname"], pl["platform"]))
print("Загрузка..")
first_cycle = True
try:
    while True:

        # Очистка переменных и таблицы
        increment = 1
        players_table.clear_rows()

        for player in players_list:
            # Получение информации от API
            json_data = playerAPI.get_data(config_json['settings']['api_key'], player.nickname, player.platform)
            if 'Error' in json_data:
                print(f"API вернула ошибку: {json_data['Error']}. Игрок {player.nickname} не будет отображен в таблице")
                pass
            player.update(json_data)

            # Заполнение полей таблицы
            # Никнейм
            player_nickname = player.nickname
            if player.nickname != player.api_nickname:
                player_nickname += f" ({player.api_nickname})"

            # Ранг
            player_rank = f"{player.rank} {divisionTransform.to_roman(player.division)}".upper()
            
            # Очки
            player_rank_progress = div_handler.calculate_percent2next(player.score)
            player_po = f"{divisionTransform.to_progress(player_rank_progress, 14)} {player.score}/{div_handler.get_next_division_points(player.score)}"
            for saved_player in saved_players_json:
                if player.nickname == saved_player['nickname']:
                    saved_points_delta = player.score - saved_player['data']['score']
                    if saved_points_delta > 0:
                        player_po += f" [ +{saved_points_delta} ]"
                    elif saved_points_delta < 0:
                        player_po += f" [ {saved_points_delta} ]"
            # Легенда
            player_legend = player.selected_legend
            if player.legend_kills != {}:
                player_legend += f" [ {player.legend_kills} ]"

            # Состояние
            player_state = player.current_state_as_text
            
            if player_state == "Offline":
                # Проверка на наличие сохраненного времени последнего онлайна
                if player.last_online is not None:
                    last_online_delta = datetime.now() - player.last_online
                    player_state += " ["
                    if last_online_delta.days > 0:
                        player_state += f" {last_online_delta.days}d"
                    if last_online_delta.seconds//3600 > 0:
                        player_state += f" {last_online_delta.seconds//3600}h"
                    if last_online_delta.seconds//60%60 > 0:
                        player_state += f" {last_online_delta.seconds//60%60}m"
                    player_state += "]"

            # Добавление в таблицу
            players_table.add_row([increment, player_nickname, player_rank, player_po, player_legend, player_state])

            players_table.align['Счёт [Изменения]'] = 'l'

            increment += 1

            # Проверка наличия игрока в базе данных
            if first_cycle:
                if playerJsonManager.is_player_in_json(saved_players_json, player.nickname, player.platform):
                    for saved_player in saved_players_json:
                        if saved_player['nickname'] == player.nickname and saved_player['platform'] == player.platform:
                            player.saved_data = saved_player['data']
                else:
                    saved_players_json.append(player.get_json_data())
                first_cycle = False


        # Очистка консоли и вывод таблицы
        os.system('cls')
        print(players_table)
except Exception as e:
    print(f"Во время работы программы возникла ошибка: {e}")
finally:
    print("Сохранение..")
    JsonFileStringManager.save(saved_players_json, 'storage')
    print("Сохранено!")
    exit()