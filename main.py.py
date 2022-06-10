from aioconsole import ainput, aprint
from json import dumps, loads
from os.path import abspath
from sys import executable
from time import sleep
from sys import argv
import logging
import asyncio
import socket

# Настраиваем формат логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Список активных подключений
connections = []

# Выводим в лог время продолжительности сессии раз в 1 минуту
def local_time():
    minutes = 0
    while True:
        sleep(60) # задержка 60 секунд
        minutes += 1
        logging.info(f'Session time: {minutes} {"minutes" if minutes > 1 else "minute"}')

# Запуск вывода времени в отдельном процессе
async def time_process():
	# Запускаем этот же скрипт, но с аргументом time. Соединяеся с stdout процесса через pipe
    proc = await asyncio.create_subprocess_exec(executable, abspath(__file__), 'time', stdout=asyncio.subprocess.PIPE)
    while True:
		# Считываем из stdout все, что выводит процесс
        data = await proc.stdout.readline()
		# Переводим в UTF-8
        line = data.decode('utf8').rstrip()
		# Печатаем в наш stdout
        await aprint(line)

# Отправка данных
async def send_to_client(client, data):
    loop = asyncio.get_event_loop()

    try:
        await asyncio.gather(loop.sock_sendall(client, data))
	# Если соеденение сброшено убираем из списка подключений
    except ConnectionResetError:
        if client in connections:
            connections.remove(client)

# Отправка данных конкретному клиенту(или всем)
async def send_message(data, client=None):
    data = bytes(dumps(data), encoding="utf-8")
    if client:
        await asyncio.gather(send_to_client(client, data))
    else:
        await asyncio.gather(*(send_to_client(connection, data) for connection in connections))

# Обработка полученного сообщения
async def process_request(request, connection):
    request = loads(request)
    response = {}

	# Если запрос на присоеденение к сети
    if request['type'] == 'join':
		# Пересылаем такой запрос единожды, чтобы избежать штормовой рассылки
        if 'forwarded' not in request:
            request['forwarded'] = True
			# Пересылаем это сообщение всем подключенным клиентам
            await send_message(request)
			# Сообщаем об успешном join и добавляем в список подключений
            response = {'type': 'response', 'message': 'Successful join'}
            connections.append(connection)
        else:
			# Получен пересланный запрос о подключении, соединяемся с новым клиентом
            newClient = await connect(request['host'], request['port'])
			# Посылаем запрос на connect
            await send_message({'type': 'connect'}, newClient)

        logging.info(f'Host {request["host"]}:{str(request["port"])} joined')
	# Получено уведомление о подключении, добавляем в список подключений
    elif request['type'] == 'connect':
        connections.append(connection)
	# Получен ответ, просто выводим в лог содержимое
    elif request['type'] == 'response':
        logging.info(f'Response received: {request["message"]}')
	# Получено сообщение, просто выводим в лог содержимое
    elif request['type'] == 'message':
        logging.info(f'Message received: {request["message"]}')
	# Неизвестный тип, предупреждение в лог
    else:
        logging.warning('Unknown request type')

    return response

# Обработка поступающих данных от клиента
async def handle_data(client):
    loop = asyncio.get_event_loop()

    while True:
        try:
			# Ждём данные и декодируем их в UTF-8
            data = (await loop.sock_recv(client, 255)).decode('utf8')
			# Обрабатываем полученные данные
            response = await process_request(data, client)
			# Если есть ответ, отправляем клиенту
            if response:
                await send_message(response, client)
		# Убираем из списка подключений, если соеденение поравалось
        except ConnectionResetError:
            if client in connections:
                connections.remove(client)
            break

# Запуск серверного функционала на адресе и порту из аргументов
async def run_server():
	# Создание TCP-сокета
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# Бинд сокета к адресу и порту
    server.bind((argv[1], int(argv[2])))
	# Начинаем слушать
    server.listen(10)
	# Включаем неблокирующий режим
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    logging.info(f'Listening on {argv[1]}:{argv[2]}')
	# Запуск бесконечного цикла ожидания новых подключений
    while True:
		# Новое подключение
        client, _ = await loop.sock_accept(server)
		# Ставим задачу на обробтку
        loop.create_task(handle_data(client))

# Подключение к серверу
async def connect(host, port):
	# Создание TCP-сокета
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# Включаем неблокирующий режим
    client.setblocking(False)

    loop = asyncio.get_event_loop()

	# Подключение
    await loop.sock_connect(client, (host, port))
    loop.create_task(handle_data(client))
	# Добавляем в список подключений
    connections.append(client)
    return client

# Процедура подсоединения к существующей сети
async def join():
	# Подключение
    client = await connect(argv[4], int(argv[5]))
	# Отправка join-сообщения
    await send_message({'type': 'join', 'host': argv[1], 'port': int(argv[2])}, client)

# Запускаем бесконечный цикл считывая сообщений из stdin с последующей отправкой
async def message_input():
    while True:
		# Считывание
        message = await ainput("Enter message: ")
        # Отправка 
		await send_message({'type': 'message', 'message': message})


if __name__ == "__main__":
	# Получаем цикл обработки событий
    loop_ = asyncio.get_event_loop()

	# Если передан аргумент time, запускаем процесс слежения за временем сессии
    if len(argv) == 2 and argv[1] == 'time':
        local_time()
        exit(0)
	# Запуск без подключения к сети
    elif len(argv) == 3:
        loop_.run_until_complete(asyncio.gather(
            time_process(),
            run_server(),
            message_input()
        ))
	# Запуск с подключением к сети
    elif len(argv) == 6:
        loop_.run_until_complete(asyncio.gather(
            time_process(),
            run_server(),
            join(),
            message_input()
        ))
	# Неверные параметры
    else:
        logging.error('Invalid parameters provided, see README')
        exit(1)