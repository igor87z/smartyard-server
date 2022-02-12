Серверная часть, которая позволяет использовать SmartYard приложения для умных домофонов и видеонаблюдения

Описаны все используемые в API вызовы, но не все полностью реализованы, большинство ответов захардкодены. 
Так получилось, что на момент того, как мы подключились к проекту, у компании уже было приложение, которое работало с домофонами, и очень хорошее. Однако в нем не было функционала личного кабинета - просмотр баланса, детализация услуг и оплаты. А в проекте LanTa этот функционал есть. Именно поэтому мы начали с этого, и в данный момент этот функционал полностью реализован в серверной части. Обращаем внимание, что для работы требуется интеграция с биллинговой системой, так как именно в ней храниться эта информация. Это оказалось очень удобным в случае, если Вы подключаете допуслуги (с мобильным приложением) действующим клиентам, у которых уже есть запись в биллинге с указанным там номером мобильного телефона. В нашем биллинге есть возможность хранения нескольких номеров у каждого договора и один и тот же номер может быть указан в нескольких договорах. После подтверждения номера телефона пользователю Мобильного Приложения сразу становяться доступен функционал личного  кабинета, причем всех договоров, в которых указан этот номер. В нашем случае серверная часть обращается в апи биллинга, отправляя туда номер телефона клиента и получая в ответ json массив с необходимой информацией. 

ToDo:
Планируется использование supervisor для запуска и контроля основного процесса.

Инсталяцию предлагаем делать на CentOS 7. Предполагается, что репозиторий epel подключен, kannel для отправки смс-сообщений на шлюз по протоколу smpp установлен и настроен. Информации по этой теие в сети достаточно. 
Адептам Debian/Ubuntu и других популярных дистрибутивов. Не сомневаюсь, что ваш опыт и знания позволит самостоятельно адаптировать эту инструкцию под ваши нужды. 
Компания, в которой я работаю, CentOS очень давно является корпоративным стандартом. Имеется свой репозиторий, который решает вопрос
с необходимыми версиями ПО, так как CentOS настолько стабилизирован, что местами это окаменелые ф-лии мамонта.
Приступим. Необходимо выполнить следующие команды в терминале под рутом:

yum install -y python36-virtualenv postgresql-server nginx supervisor

#Стартуем и добавляем автозапуск postgresql-server nginx supervisor

cd /opt

mkdir smartyard

virtualenv-3.6 smartyard

smartyard/bin/pip install requests

smartyard/bin/pip install flask

smartyard/bin/pip install psycopg2-binary

smartyard/bin/pip install smartyard/bin/pip install

smartyard/bin/pip install Flask-Migrate

smartyard/bin/pip install python-dotenv

cd smartyard

mv example.env .env

su - postgres

psql

CREATE DATABASE smartyard WITH OWNER "smartyard" ENCODING 'UTF8';

CREATE USER smartyard WITH PASSWORD 'smartyardpass';

GRANT ALL PRIVILEGES ON DATABASE smartyard TO smartyard;

\q

exit

export FLASK_APP=app.py

bin/flask db init

bin/flask db migrate

bin/flask db upgrade

./app.py


Основные настройки, в т.ч. подключение к базе данных (PG_...) и серверу kannel (KANNEL_), а также имя отправителя смс (поддерживается не всеми смс-агрегаторами) и текстовая строка перед 4-х значным кодом подтверждения (текст смс) находятся в файле .env и интуитвно понятны. Кроме того, необходимо настроить nginx, добавив в конфиг следующие строчки:
 
 location /api {
 
    proxy_pass      http://127.0.0.1:5000;
    
    proxy_set_header HOST $host;
    
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_set_header X-Real-IP $remote_addr;
    
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_set_header X-Request-Id $request_id;
    
  }



Лицензия и условия использования

Авторские права на используемое API принаддежат ЛанТа, код АКСИОСТВ

Данный проект опубликован под стандартной общественной лицензией GNU GPLv3. Вы можете модифицировать и использовать наши наработки в своих проектах, в т.ч. коммерческих, при обязательном условии публикации их исходного кода. Также мы готовы рассмотреть ваши Pull requests, если вы хотите чтобы наш проект развивался с учётом ваших модификаций и доработок.
