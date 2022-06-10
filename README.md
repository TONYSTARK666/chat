# Описание
Каждый участник p2p сети выступает сервером, обязуется при подключении к нему новых участников передать всем имеющимся у него подключениям адрес сервера нового участника. При получении информации о новом подключении участники устанавливают подключение по указанному адресу.

Отдельный процесс следит за длительностью сессии клиента и периодически пишет в stdout текущую продолжительность.

# Запуск
(Про сеть)
При подключении к сети в качестве обратного адреса участник шлёт тот же адрес, что указан в аргументах(на котором слушаются подключения). Поэтому в аргументах стоит указывать не 0.0.0.0 и не localhost(т.к резолвинг DNS не предусмотрен), а конкретный адрес(127.0.0.1).

(Без подключения)
Запускается первым, когда ещё нет сети.

Первый аргумент - хост, на котором слушаются подключения, второй - порт. python main.py 127.0.0.1 9000. 

(С подключением к сети)
python main.py 127.0.0.1 9005 -c 127.0.0.1 9000.

Первый аргумент - хост, на котором слушаются подключения, второй - порт.

Первым аргументом после -c указывается хост любого из участников p2p сети, вторым - порт.
