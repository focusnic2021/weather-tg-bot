"""
навеяно - Telegram bot на Python + aiogram | Прогноз погоды в любом городе | API погоды | Парсинг JSON
https://www.youtube.com/watch?v=fa1FUW1jLAE
"""
import requests
import datetime
import sqlite3
from config import open_weather_token, tg_bot_token
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

bot = Bot(token=tg_bot_token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)
# print(f'open_weather_token={open_weather_token}, tg_bot_token={tg_bot_token}')


def protocol(event_mesaage):
    """Заносит в файл лога принятое сообщение. Сама определяется с датой - либо новый файл, либо дописывает в существующий
    """
    try:
        # открыть файл-протокол, занести сведения:
        file_name = f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
        f = open(file_name, 'a')
        f.write(event_mesaage)
    finally:
        f.close()
    # ...def protocol(event_mesaage)


def db_insert_user(data):
    """Insert record about new user - his id, first_name, last_name, datetime"""
    try:
        # запись в базу данных:
        connect = sqlite3.connect('users_query.db')
        cursor = connect.cursor()
        sql = f"SELECT dt FROM users WHERE id = {data[0]}"
        cursor.execute(sql)
        user_is_exist = cursor.fetchone()
        if user_is_exist is None:
            # такого пользователя нет - вставить запись о нем:
            sql = "INSERT INTO users(id, first_name, last_name, dt) VALUES(?,?,?,?);"
            print(sql)
            cursor.execute(sql, data)
            connect.commit()
        else:
            print(f"Знаем такого, был здесь {user_is_exist}")
    except Exception as ex:
        print('Ошибка записи в БД', ex)
    # ...def db_insert_user(sql)


def db_insert_event(data):
    """Insert record about user's query  - user_id, message_text, result, dt"""
    try:
        # запись в базу данных:
        connect = sqlite3.connect('users_query.db')
        cursor = connect.cursor()
        sql = "INSERT INTO events(user_id, message_text, result, dt) VALUES(?,?,?,?);"
        cursor.execute(sql, data)
        connect.commit()
        # запрос предыдущих запросов этого пользователя:
        old_records = [] # список для заполнения
        # sql = f"SELECT DISTINCT message_text FROM events WHERE user_id = {data[0]} AND result <> 'city not found' ORDER BY dt DESC LIMIT 3"
        sql = f"""SELECT DISTINCT message_text FROM
            (SELECT message_text FROM events WHERE user_id = {data[0]} AND result <> 'city not found'
            ORDER BY dt DESC LIMIT 10)
        LIMIT 3"""
        # print(sql)
        cursor.execute(sql)
        [old_records.append(elem[0]) for elem in cursor.fetchmany(3)]
        return old_records
    except Exception as ex:
        print('Ошибка записи в БД', ex)
        return ['error!', ex]
    # ...def db_insert_event(data)


@dp.message_handler(commands=['start','help'])
async def start_command(message: types.Message):
    # внести сообщение о событии в протокол и БД:
    event_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')};" \
                f"{message.from_user.id};" \
                f"{message.from_user.first_name} {message.from_user.last_name};" \
                f"command={message.text};\n"
    # запись в лог-файл:
    protocol(event_msg)
    # запись в БД:
    db_insert_user((
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.last_name,
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    # приветствовать пользователя:
    await message.reply('Погода на данный момент в определенном городе.\nПример запроса:\nУчалы\nkazan\nalanya')
    # ...async def start_command(message: types.Message)


@dp.message_handler()
async def get_weather(message: types.Message):
    response_result=''
    try:
        req = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={open_weather_token}&units=metric&lang=ru"
            )
        data = req.json()
        # print(data)

        if data.get('cod') and data.get('cod') == '404':    # 'message': 'city not found'
            await message.reply(data.get('message'))
            response_result = data.get('message')
            # ...data.get('cod') and data.get('cod') == '404'
        elif data.get('coord'):     # все хорошо, данные получены
            # данные о городе:
            city = data['name']                 # название города (из ответа)
            country = data['sys']['country']    # страна
            lat, lon = data['coord']['lat'], data['coord']['lon']   # координаты города
            # timezone = data['timezone']         # timezone - часовой пояс. Все вермена даны в Гринвиче
            # время в городе - с поправкой на часовой пояс:
            dt = datetime.datetime.fromtimestamp(data['dt']+data['timezone']).strftime('%d.%m.%Y %H:%M')
            # время восхода и заката на сегодня в этом городе - с поправкой на часовой пояс:
            sunrise = datetime.datetime.fromtimestamp(data['sys']['sunrise']+data['timezone']).strftime('%H:%M')
            sunset  = datetime.datetime.fromtimestamp(data['sys']['sunset']+data['timezone']).strftime('%H:%M')
            # print(f"timezone={data['timezone']}\n sunrise={sunrise}, sunset={sunset}")
            length_of_day = datetime.datetime.fromtimestamp(data['sys']['sunset']) - datetime.datetime.fromtimestamp(data['sys']['sunrise'])
            # данные о погоде:
            temp     = data['main']['temp']             # температура
            pressure = str(int(data['main']['pressure'])-300)         # давление # pressure = data['main']['pressure']         # давление
            humidity = data['main']['humidity']         # влажность
            wind_deg = data['wind']['deg']      # направление ветра
            # wind_kompas =''
            if wind_deg < 31:
                wind_kompas = 'С' # wind_kompas = 'Северный'
            elif wind_deg > 30 and wind_deg < 61:
                wind_kompas = 'СВ' # wind_kompas = 'Северо-Восточный'
            elif wind_deg > 60 and wind_deg < 121:
                wind_kompas = 'В' # wind_kompas = 'Восточный'
            elif wind_deg > 120 and wind_deg < 151:
                wind_kompas = 'ЮВ' # wind_kompas = 'Юго-Восточный'
            elif wind_deg > 150 and wind_deg < 211:
                wind_kompas = 'Ю' # wind_kompas = 'Южный'
            elif wind_deg > 210 and wind_deg < 241:
                wind_kompas = 'ЮЗ' # wind_kompas = 'Юго-Западный'
            elif wind_deg > 240 and wind_deg < 301:
                wind_kompas = 'З' # wind_kompas = 'Западный'
            elif wind_deg > 300 and wind_deg < 331:
                wind_kompas = 'СЗ' # wind_kompas = 'Северо-Западный'
            else:
                wind_kompas = 'С' # wind_kompas = 'Северный'
            wind_speed = data['wind']['speed']  # скорость ветра
            await message.reply(f"Погода в <b>{city}</b> - {country} \n"
                f"(коорд: {lat},{lon})\n"
                f"по состоянию на {dt}\n"
                f"Температура: {temp} °С\n"
                f"Давление: {pressure} мм.рт.ст\n"
                f"Влажность: {humidity} %\n"
                f"Солнце:\n\tВосход - {sunrise}, Закат - {sunset}, Световой день - {length_of_day}\n\t"
                f"Ветер: {wind_kompas} ({wind_deg}°),  {wind_speed} м/с")

            response_result = f'{city} ({dt})'
            # ...elif data.get('coord')

        # занести в протокол:
        event_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')};" \
                    f"{message.from_user.id};" \
                    f"{message.from_user.first_name} {message.from_user.last_name};" \
                    f"message.text={message.text};" \
                    f"result={response_result}\n"
        protocol(event_msg)
        # запись в БД - и возвращение старых запросов этого пользователя:
        old_queries = db_insert_event((
            message.from_user.id,
            message.text,
            response_result[0:30],
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        # print(old_queries)
        # сформировать keyboard и представить пользователю
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*old_queries)
        await message.answer("Еще запрос?", reply_markup=keyboard)

    except Exception as ex:
        # Ошибку - тоже занести в протокол:
        event_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')};" \
                    f"{message.from_user.id};" \
                    f"{message.from_user.first_name} {message.from_user.last_name};" \
                    f"message.text={message.text};" \
                    f"Exception={ex}\n"
        protocol(event_msg)

        await message.reply('Ошибка при обращении к серверу данных:\n', ex)
    # ...async def get_weather(message: types.Message)


@dp.message_handler()
async def send_location(message: types.Message):
    pass
    # ...async def send_location()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)