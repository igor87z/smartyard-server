#!bin/python
import random, uuid, os, json, requests, binascii, secrets, datetime, pytz
from datetime import timedelta
from random import randint
from flask import Flask, jsonify, request, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.sql import exists
from dotenv import load_dotenv
from requests.exceptions import HTTPError
import logging, sys

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print('not loaded .env file')
    exit()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://" + os.getenv('PG_USER') + ":" + os.getenv('PG_PASS') + "@" + os.getenv("PG_HOST") + ":5432/" + os.getenv('PG_DBNAME')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

kannel_url = "http://%s:%d/cgi-bin/sendsms" % (os.getenv('KANNEL_HOST'), int(os.getenv('KANNEL_PORT')))
kannel_params = (('user', os.getenv('KANNEL_USER')), ('pass', os.getenv('KANNEL_PASS')), ('from', os.getenv('KANNEL_FROM')), ('coding', '2'))
billing_url=os.getenv('BILLING_URL')
expire=int(os.getenv('EXPIRE'))

class Temps(db.Model):
    __tablename__ = 'temps'

    userphone = db.Column(db.BigInteger, primary_key=True)
    smscode = db.Column(db.Integer, index=True, unique=True)

    def __init__(self, userphone, smscode):
        self.userphone = userphone
        self.smscode = smscode

    def __repr__(self):
        return f""

class Users(db.Model):
    __tablename__ = 'users'

    uuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    userphone = db.Column(db.BigInteger, index=True, unique=True)
    name = db.Column(db.String(24))
    patronymic = db.Column(db.String(24))
    email = db.Column(db.String(60))
    videotoken = db.Column(db.String(32))
    vttime = db.Column(db.DateTime(timezone=False))
    strims = db.Column(db.ARRAY(String(10)))

    def __init__(self, uuid, userphone, name, patronymic, email, videotoken, vttime, strims):
        self.uuid = uuid
        self.userphone = userphone
        self.name = name
        self.patronymic = patronymic
        self.email = email
        self.videotoken = videotoken
        self.vttime = vttime
        self.strims = strims

    def __repr__(self):
        return f""

def access_verification(key):
    global response
    if not key.get('Authorization'):
        response = {'code':422,'name':'Отсутствует токен авторизации','message':'Отсутствует токен авторизации'}
        abort (422)
    if not db.session.query(db.session.query(Users).filter_by(uuid=key.get('Authorization')[7:]).exists()).scalar():
        response = {'code':401,'name':'Не авторизован','message':'Не авторизован'}
        abort (401)
    return db.session.query(Users.userphone).filter_by(uuid=key.get('Authorization')[7:]).first()[0]

def json_verification(input_json):
    global response
    if not input_json:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)

def generate_video_token(userPhone,strims):
    videotoken = secrets.token_hex(16)
    db.session.query(Users).filter_by(userphone=int(userPhone)).update({'videotoken' : videotoken, 'vttime' : datetime.datetime.now(), 'strims' : strims})
    db.session.commit()
    return videotoken

@app.route('/api/')
def index():
    return "Hello, World!"

@app.route('/api/accessfl', methods=['GET'])
def accessfl():
    global response
    token = request.args.get('token')
    if not token or token == '':
        response = {'code':403,'name':'Forbidden','message':'Нет токена'}
        abort (403)
    name = request.args.get('name', 0)
    extime = datetime.datetime.now() - timedelta(minutes=expire)
    if db.session.query(db.exists().where(Users.videotoken==token)).scalar():
        vttime = db.session.query(Users.vttime).filter_by(videotoken = token).first()[0]
        strims = db.session.query(Users.strims).filter_by(videotoken = token).first()[0]
        if vttime >= extime and name in strims:
            response = app.response_class(status=200)
            return response
    response = {'code':403,'name':'Forbidden','message':'Не верный токен'}
    abort (403)

@app.route('/api/address/access', methods=['POST'])
def address_access():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'guestPhone' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    guestPhone = request_data['guestPhone']
    if not 'flatId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    flatId = request_data['flatId']
    if not 'clientId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    clientId = request_data['clientId']
    if not 'expire' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    expire = request_data['expire']
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/address/getAddressList', methods=['POST'])
def address_getAddressList():
    global response
    response = requests.post(billing_url + "getaddresslist", headers={'Content-Type':'application/json'}, data=json.dumps({'phone': phone})).json()
    #response = {'code':200,'name':'OK','message':'Хорошо','data':[{'houseId':'19260','address':'Тамбов, ул. Верховая, дом 17','hasPlog':'t','doors':[{'domophoneId':'343','doorId':0,'entrance':'1','icon':'entrance','name':'Подъезд'},{'domophoneId':'70','doorId':0,'entrance':'1','icon':'entrance','name':'Подъезд 1'},{'domophoneId':'124','doorId':0,'icon':'entrance','name':'Подъезд 2'}],'cctv':2},{'houseId':'6694','address':'Тамбов, ул. Пионерская, дом 5\'б\'','hasPlog':'t','doors':[{'domophoneId':'79','doorId':0,'entrance':'3','icon':'entrance','name':'Подъезд'},{'domophoneId':'75','doorId':0,'icon':'wicket','name':'Калитка'},{'domophoneId':'297','doorId':0,'icon':'wicket','name':'Калитка доп'},{'domophoneId':'131','doorId':0,'icon':'gate','name':'Ворота'}],'cctv':14}]}
    return jsonify(response)

@app.route('/api/address/getSettingsList', methods=['POST'])
def address_getSettingsList():
    global response
    access_verification(request.headers)
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'hasPlog':'t','contractName':'ФЛ-85973\/20','clientId':'91052','contractOwner':'t','clientName':'Бивард-00011 (Чемодан 2)','services':['internet','cctv','domophone'],'lcab':'https:\/\/lc.lanta.me\/?auth=Zjg1OTczOmY5NzkzNTQzM2U5YmQ5ZThkYTJiZmU2MWMwNDlkZGMy','houseId':'19260','flatId':'136151','flatNumber':'1','flatOwner':'t','address':'Тамбов, ул. Верховая, дом 17, кв 1','hasGates':'f','roommates':[{'phone':'79051202936','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79106599009','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79156730435','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79641340000','expire':'3000-01-01 00:00:00','type':'inner'},{'phone':'79641340000','expire':'3001-01-01 00:00:00','type':'inner'}]},{'hasPlog':'t','services':['cctv','domophone'],'houseId':'19260','flatId':'136162','flatNumber':'12','flatOwner':'f','address':'Тамбов, ул. Верховая, дом 17, кв 12','hasGates':'f','roommates':[{'phone':'79176194895','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79202313789','expire':'3001-01-01 00:00:00','type':'inner'}]},{'hasPlog':'t','services':['cctv','domophone'],'houseId':'6694','flatId':'306','flatNumber':'69','flatOwner':'f','address':'Тамбов, ул. Пионерская, дом 5\'б\', кв 69','hasGates':'t','roommates':[{'phone':'79069202020','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79641349232','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79091215044','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79127600769','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79106500155','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79514470944','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79107567265','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79203409810','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79227063593','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79220144401','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79114688286','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79661840298','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79641340000','expire':'3001-01-01 00:00:00','type':'owner'},{'phone':'79275807272','expire':'3001-01-01 00:00:00','type':'inner'},{'phone':'79107567249','expire':'3001-01-01 00:00:00','type':'inner'}]},{'hasPlog':'t','services':['cctv','domophone'],'houseId':'6694','flatId':'307','flatNumber':'70','flatOwner':'f','address':'Тамбов, ул. Пионерская, дом 5\'б\', кв 70','hasGates':'t'}]}
    return jsonify(response)

@app.route('/api/address/intercom', methods=['POST'])
def address_intercom():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'flatId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    flatId = request_data['flatId']
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'allowDoorCode':'t','doorCode':'22438','CMS':'t','VoIP':'t','autoOpen':'2020-06-03 18:32:10','whiteRabbit':'0','FRSDisabled':'f'}}
    return jsonify(response)

@app.route('/api/address/offices', methods=['POST'])
def address_offices():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'lat':52.730641,'lon':41.45234,'address':'Мичуринская улица, 2А','opening':'09:00-19:00 (без выходных)'},{'lat':52.767248,'lon':41.40488,'address':'улица Чичерина, 48А (ТЦ Апельсин)','opening':'09:00-19:00 (без выходных)'},{'lat':52.707399,'lon':41.397374,'address':'улица Сенько, 25А (Магнит)','opening':'09:00-19:00 (без выходных)'},{'lat':52.675463,'lon':41.465411,'address':'Астраханская улица, 189А (ТЦ МЖК)','opening':'09:00-19:00 (без выходных)'},{'lat':52.586785,'lon':41.497009,'address':'Октябрьская улица, 13 (ДК)','opening':'09:00-19:00 (вс, пн - выходной)'}]}
    return jsonify(response)

@app.route('/api/address/openDoor', methods=['POST'])
def address_openDoor():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'domophoneId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    domophoneId = request_data['domophoneId']
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/address/plog', methods=['POST'])
def address_plog():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'flatId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    flatId = request_data['flatId']
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'date':'2021-12-15 13:03:23','uuid':'4d5082d2-f8a1-48ac-819e-c16f1f81a1e0','image':'3f99bdf6-96ef-4300-b709-1f557806c65b','objectId':'79','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б п 3 [Подъезд]','event':'1','detail':'1','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/3\/f\/9\/9\/3f99bdf6-96ef-4300-b709-1f557806c65b.jpg','previewType':2,'detailX':{'opened':'f','face':{'left':'614','top':'38','width':'174','height':'209'},'flags':['canLike']}},{'date':'2021-12-15 00:16:20','uuid':'bc1671b4-e01b-487e-b175-745e82be0ca9','image':'86ddb8e1-1122-4946-8495-a251b6320b99','objectId':'75','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б [Калитка]','event':'4','detail':'89103523377','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/8\/6\/d\/d\/86ddb8e1-1122-4946-8495-a251b6320b99.jpg','previewType':1,'detailX':{'phone':'89103523377'}},{'date':'2021-12-15 00:14:21','uuid':'32fd7c27-0d35-4d98-ab29-2544c3d0b9a7','image':'ad14c83a-126a-4f09-a659-f412fb11007e','objectId':'75','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б [Калитка]','event':'4','detail':'89103523377','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/a\/d\/1\/4\/ad14c83a-126a-4f09-a659-f412fb11007e.jpg','previewType':1,'detailX':{'phone':'89103523377'}},{'date':'2021-12-15 00:03:56','uuid':'ff42c747-3216-4fa7-8b68-128207d1a9ab','image':'0b335948-864f-41d6-b9a7-465f88f20ef1','objectId':'75','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б [Калитка]','event':'4','detail':'89103523377','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/0\/b\/3\/3\/0b335948-864f-41d6-b9a7-465f88f20ef1.jpg','previewType':1,'detailX':{'phone':'89103523377'}},{'date':'2021-12-15 00:01:28','uuid':'0e57d2c7-9e73-4083-98bb-2b140622be93','image':'8fc3224e-ef46-4ec6-9d5d-04e249ec2e31','objectId':'75','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б [Калитка]','event':'4','detail':'89103523377','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/8\/f\/c\/3\/8fc3224e-ef46-4ec6-9d5d-04e249ec2e31.jpg','previewType':1,'detailX':{'phone':'89103523377'}},{'date':'2021-12-15 00:00:02','uuid':'3bcac0af-677b-49d8-ba65-c18c3bcc8668','image':'c28c7e58-7797-4143-a2b8-2c513e216bb8','objectId':'75','objectType':'0','objectMechanizma':'0','mechanizmaDescription':'Пионерская 5 б [Калитка]','event':'4','detail':'89103523377','preview':'https:\/\/static.dm.lanta.me\/2021-12-15\/c\/2\/8\/c\/c28c7e58-7797-4143-a2b8-2c513e216bb8.jpg','previewType':1,'detailX':{'phone':'89103523377'}}]}
    return jsonify(response)

@app.route('/api/address/plogDays', methods=['POST'])
def address_plogDays():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'flatId' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    flatId = request_data['flatId']
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'day':'2021-12-15','events':'6'},{'day':'2021-12-13','events':'2'},{'day':'2021-12-11','events':'3'},{'day':'2021-12-09','events':'3'},{'day':'2021-12-07','events':'1'},{'day':'2021-12-06','events':'4'},{'day':'2021-12-05','events':'1'},{'day':'2021-12-04','events':'1'},{'day':'2021-11-30','events':'1'},{'day':'2021-11-29','events':'6'},{'day':'2021-11-27','events':'7'},{'day':'2021-11-26','events':'13'},{'day':'2021-11-25','events':'5'},{'day':'2021-11-23','events':'2'},{'day':'2021-11-22','events':'2'},{'day':'2021-11-20','events':'2'},{'day':'2021-11-17','events':'3'},{'day':'2021-11-16','events':'1'},{'day':'2021-11-15','events':'1'},{'day':'2021-11-13','events':'1'},{'day':'2021-11-12','events':'6'},{'day':'2021-11-11','events':'2'},{'day':'2021-11-09','events':'3'},{'day':'2021-11-05','events':'1'},{'day':'2021-10-30','events':'1'},{'day':'2021-10-29','events':'3'},{'day':'2021-10-28','events':'3'},{'day':'2021-10-27','events':'3'},{'day':'2021-10-26','events':'2'},{'day':'2021-10-23','events':'2'},{'day':'2021-10-22','events':'3'},{'day':'2021-10-21','events':'4'},{'day':'2021-10-19','events':'3'},{'day':'2021-10-18','events':'2'},{'day':'2021-10-16','events':'4'},{'day':'2021-10-15','events':'1'},{'day':'2021-10-14','events':'3'},{'day':'2021-10-09','events':'1'},{'day':'2021-10-08','events':'6'},{'day':'2021-10-07','events':'4'},{'day':'2021-10-06','events':'7'},{'day':'2021-10-05','events':'6'},{'day':'2021-10-03','events':'1'},{'day':'2021-10-02','events':'7'},{'day':'2021-10-01','events':'12'},{'day':'2021-09-30','events':'5'},{'day':'2021-09-29','events':'6'},{'day':'2021-09-28','events':'17'},{'day':'2021-09-27','events':'7'},{'day':'2021-09-25','events':'2'},{'day':'2021-09-22','events':'1'},{'day':'2021-09-20','events':'1'},{'day':'2021-09-18','events':'4'},{'day':'2021-09-17','events':'3'},{'day':'2021-09-16','events':'5'},{'day':'2021-09-15','events':'1'},{'day':'2021-09-13','events':'12'},{'day':'2021-09-11','events':'1'},{'day':'2021-09-06','events':'2'},{'day':'2021-09-05','events':'2'}]}
    return jsonify(response)

@app.route('/api/address/registerQR', methods=['POST'])
def address_registerQR():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'QR' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    QR = request_data['QR']
    QRcurrent = QR + "1"
    if QR == QRcurrent:
        response = {'code':520,'message':'Этот пользователь уже зарегистрирован в системе'}
        return jsonify(response)
    if QR != QR:
        response = {'code':520,'message':'Некорректный QR-код!'}
        return jsonify(response)
    if QR != QR:
        response = {'code':200,'name':'OK','message':'Хорошо','data':'QR-код не является кодом для доступа к квартире'}
        return jsonify(response)
    if QR == QR:
        response = {'code':200,'name':'OK','message':'Хорошо','data':'Ваш запрос принят и будет обработан в течение одной минуты, пожалуйста подождите'}
        return jsonify(response)

@app.route('/api/address/resend', methods=['POST'])
def address_resend():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/address/resetCode', methods=['POST'])
def address_resetCode():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/cctv/all', methods=['POST'])
def cctv_all():
    global response
    phone = access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    strims = ['111111', '222222', '333333']
    videotoken = generate_video_token(phone,strims)
    #print(f'Generate videotoken  {videotoken}!')
    response = { "code": 200, "name": "OK", "message": "Хорошо", "data": [ { "id": 692, "name": "Пионерская 5б Вид сверху 2 - Тупик", "lat": "52.703267836456", "url": "https://vd.axiostv.ru/100001", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.4726675977" }, { "id": 693, "name": "Пионерская 5б Вид сверху 3 - двор", "lat": "52.703500236158", "url": "https://fl2.lanta.me:8443/91165", "token": "3f627a87d2664f3176c3585cb9561b5a", "lon": "41.473222207278" }, { "id": 723, "name": "Домофон Пионерская 5 б п 1", "lat": "52.703248663394", "url": "https:\/\/fl2.lanta.me:8443\/89318", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473443133291" }, { "id": 694, "name": "Пионерская 5б Вид сверху 4 - парковка у ТП", "lat": "52.703443771131", "url": "https:\/\/fl2.lanta.me:8443\/91171", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473441666458" }, { "id": 724, "name": "Домофон Пионерская 5 б п 2", "lat": "52.703204679595", "url": "https:\/\/fl2.lanta.me:8443\/91071", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473222898785" }, { "id": 695, "name": "Пионерская 5б Въезд в тупик для чтения номеров", "lat": "52.703021201666", "url": "https:\/\/fl3.lanta.me:8443\/91172", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.472768306267" }, { "id": 725, "name": "Домофон Пионерская 5 б п 3", "lat": "52.703178916547", "url": "https:\/\/fl2.lanta.me:8443\/91072", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.472994973883" }, { "id": 696, "name": "Пионерская 5б Въезд во двор для чтения номеров", "lat": "52.703308087163", "url": "https:\/\/fl2.lanta.me:8443\/91174", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473656725138" }, { "id": 726, "name": "Домофон Пионерская 5 б п 4", "lat": "52.703346026911", "url": "https:\/\/fl2.lanta.me:8443\/91073", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.472863964736" }, { "id": 697, "name": "Пионерская 5б Двор - вдоль проезда на север", "lat": "52.703443618763", "url": "https:\/\/fl2.lanta.me:8443\/91176", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.4730289625" }, { "id": 727, "name": "Домофон Пионерская 5 б п 5", "lat": "52.703531471559", "url": "https:\/\/fl2.lanta.me:8443\/91074", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.47279571509" }, { "id": 698, "name": "Пионерская 5б Двор - парковка у 5-го подъезда", "lat": "52.703597281681", "url": "https:\/\/fl2.lanta.me:8443\/91177", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.472968256567" }, { "id": 728, "name": "Домофон Пионерская 5 б Калитка", "lat": "52.703142017842", "url": "https:\/\/fl2.lanta.me:8443\/91078", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473720762879" }, { "id": 699, "name": "Пионерская 5б Вид сверху 1 - Пионерская", "lat": "52.703042139774", "url": "https:\/\/fl2.lanta.me:8443\/89312", "token": "a319639b20342a17c06aa51c12359f2a", "lon": "41.473282892257"}]}
    return jsonify(response)

@app.route('/api/cctv/camMap', methods=['POST'])
def cctv_camMap():
    global response
    access_verification(request.headers)
#    if not request.get_json():
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
#    request_data = request.get_json()
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'id':'70','url':'https://fl2.lanta.me:8443/91052','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'t'},{'id':'75','url':'https://fl2.lanta.me:8443/91078','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'t'},{'id':'79','url':'https://fl2.lanta.me:8443/91072','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'t'},{'id':'124','url':'https://fl2.lanta.me:8443/95594','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'t'},{'id':'131','url':'https://fl2.lanta.me:8443/91174','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'f'},{'id':'343','url':'https://fl2.lanta.me:8443/90753','token':'acd0c17657395ff3f69d68e74907bb3a','frs':'t'}]}
    return jsonify(response)

@app.route('/api/cctv/overview', methods=['POST'])
def cctv_overview():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/cctv/recDownload', methods=['POST'])
def cctv_recDownload():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/cctv/recPrepare', methods=['POST'])
def cctv_recPrepare():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/cctv/youtube', methods=['POST'])
def cctv_youtube():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/ext/ext', methods=['POST'])
def ext_ext():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/ext/list', methods=['POST'])
def ext_list():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/frs/disLike', methods=['POST'])
def frs_disLike():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/frs/like', methods=['POST'])
def frs_like():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/frs/listFaces', methods=['POST'])
def frs_listFaces():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/address', methods=['POST'])
def geo_address():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/coder', methods=['POST'])
def geo_coder():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/getAllLocations', methods=['POST'])
def geo_getAllLocations():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/getAllServices', methods=['POST'])
def geo_getAllServices():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/getHouses', methods=['POST'])
def geo_getHouses():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/getServices', methods=['POST'])
def geo_getServices():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/geo/getStreets', methods=['POST'])
def geo_getStreets():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/inbox/alert', methods=['POST'])
def inbox_alert():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/inbox/chatReaded', methods=['POST'])
def inbox_chatReaded():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/inbox/delivered', methods=['POST'])
def inbox_delivered():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/inbox/inbox', methods=['POST'])
def inbox_inbox():
    global response
    access_verification(request.headers)
    #if not request.get_json():
    #    response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
    #    abort (422)
    #request_data = request.get_json()
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'count':0,'chat':0}}
    return jsonify(response)

@app.route('/api/inbox/readed', methods=['POST'])
def inbox_readed():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/inbox/unreaded', methods=['POST'])
def inbox_unreaded():
    global response
    access_verification(request.headers)
#    if not request.get_json():
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
#    request_data = request.get_json()
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'count':0,'chat':0}}
    return jsonify(response)


@app.route('/api/issues/action', methods=['POST'])
def issues_action():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/issues/comment', methods=['POST'])
def issues_comment():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/issues/create', methods=['POST'])
def issues_create():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/issues/listConnect', methods=['POST'])
def issues_listConnect():
    global response
    access_verification(request.headers)
#    if not request.get_json():
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
#    request_data = request.get_json()
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/pay/prepare', methods=['POST'])
def pay_prepare():
    global response
    phone = access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logging.debug(repr(request_data['clientId']))
    logging.debug(repr(request_data['amount']))
    response = requests.post(billing_url + "createinvoice", headers={'Content-Type':'application/json'}, data=json.dumps({'login': request_data['clientId'], 'amount' : request_data['amount'], 'phone' : phone})).json()
    #response = {'code':200,'name':'OK','message':'Хорошо','data':'12350'}
    return jsonify(response)

@app.route('/api/pay/process', methods=['POST'])
def pay_process():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logging.debug(repr(request_data['paymentId']))
    logging.debug(repr(request_data['sbId']))
    response = {'code':200,'name':'OK','message':'Хорошо','data':'Платеж в обработке'}
    return jsonify(response)

@app.route('/api/sip/helpMe', methods=['POST'])
def sip_helpMe():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    return "Hello, World!"

@app.route('/api/user/addMyPhone', methods=['POST'])
def user_addMyPhone():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'login' in request_data or not 'password' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    login = request_data['login']
    password = request_data['password']
    if 'comment' in request_data:
        comment = request_data['comment']
    if 'notification' in request_data:
        notification = request_data['notification']
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/user/appVersion', methods=['POST'])
def user_appVersion():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'version' in request_data or not 'platform' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    version = request_data['version']
    platform = request_data['platform']
    if  version != None and (platform == 'android' or platform == 'ios'):
        response = {'code':200,'name':'OK','message':'Хорошо','data':'upgrade'}
        return jsonify(response)
    else:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)

@app.route('/api/user/confirmCode', methods=['POST'])
def user_confirmCode():
    global response
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort(422)
    request_data = request.get_json()
    if (not 'userPhone' in request_data) or len(request_data['userPhone'])!=11 or (not 'smsCode' in request_data) or len(request_data['smsCode'])!=4:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort(422)
    userPhone = request_data['userPhone']
    if not db.session.query(db.session.query(Temps).filter_by(userphone=int(userPhone)).exists()).scalar():
        response = {"code":404,"name":"Not Found","message":"Не найдено"}
        abort(404)
    smsCode = request_data['smsCode']
    if not db.session.query(db.exists().where(Temps.userphone==int(userPhone) and Temps.smscode == int(smsCode))).scalar():
        response = {"code":403,"name":"Пин-код введен неверно","message":"Пин-код введен неверно"}
        abort(403)
    accessToken = str(uuid.uuid4())
    if not 'name' in request_data:
        request_data['name'] = None
    if not 'patronymic' in request_data:
        request_data['patronymic'] = None
    if not 'email' in request_data:
        request_data['email'] = None
    if db.session.query(db.session.query(Users).filter_by(userphone=int(userPhone)).exists()).scalar():
        db.session.query(Users).filter_by(userphone=int(userPhone)).update({'uuid' : accessToken})
    else:
        new_user = Users(uuid = accessToken, userphone = int(request_data['userPhone']), name = request_data['name'], patronymic = request_data['patronymic'], email = request_data['email'])
        db.session.add(new_user)
    db.session.query(Temps).filter_by(userphone=int(userPhone)).delete()
    db.session.commit()
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'accessToken':accessToken,'names':{'name':request_data['name'],'patronymic':request_data['patronymic']}}}
    return jsonify(response)

@app.route('/api/user/getPaymentsList', methods=['POST'])
def user_getPaymentsList():
    global response
    phone = access_verification(request.headers)
    response = requests.post(billing_url + "getlist", headers={'Content-Type':'application/json'}, data=json.dumps({'phone': phone})).json()
    #response = {'code':200,'name':'OK','message':'Хорошо','data':[{'houseId':'19260','flatId':'136151','address':'Тамбов, ул. Верховая, дом 17, кв 1','accounts':[{'clientId':'91052','clientName':'Бивард-00011 (Чемодан 2)','contractName':'ФЛ-85973/20','blocked':'f','balance':0,'bonus':0,'contractPayName':'85973','lcab':'https:\/\/lc.lanta.me\/?auth=Zjg1OTczOmY5NzkzNTQzM2U5YmQ5ZThkYTJiZmU2MWMwNDlkZGMy','lcabPay':'https:\/\/lc.lanta.me\/?auth=Zjg1OTczOmY5NzkzNTQzM2U5YmQ5ZThkYTJiZmU2MWMwNDlkZGMy','services':['internet','cctv','domophone']}]}]}
    return jsonify(response)

@app.route('/api/user/notification', methods=['POST'])
def user_notification():
    global response
    access_verification(request.headers)
#    if not request.get_json():
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
#    request_data = request.get_json()
#    if not 'money' in request_data and not 'enable' in request_data:
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
#    money = request_data['money']
#    enable = request_data['enable']
#    if (money == 't' or money == 'f') and (enable == 't' or enable == 'f'):
#        response = {'code':200,'name':'OK','message':'Хорошо','data':{'money':money,'enable':enable}}
#        return jsonify(response)
#    else:
#        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
#        abort (422)
    money = 't'
    enable = 't'
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'money':money,'enable':enable}}
    return jsonify(response)

@app.route('/api/user/ping', methods=['POST'])
def user_ping():
    global response
    access_verification(request.headers)
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/user/pushTokens', methods=['POST'])
def user_pushTokens():
    global response
    access_verification(request.headers)
    response = {'code':200,'name':'OK','message':'Хорошо','data':{'pushToken':'fnTGJUfJTIC61WfSKWHP_N:APA91bGbnS3ck-cEWO0aj4kExZLsmGGmhziTu2lfyvjIpbmia5ahfL4WlJrr8DOjcDMUo517HUjxH4yZm0m5tF89CssdSsmO6IjcrS1U_YM3ue2187rc9ow9rS0xL8Q48vwz2e6j42l1','voipToken':'off'}}
    return jsonify(response)

@app.route('/api/user/registerPushToken', methods=['POST'])
def user_registerPushToken():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'platform' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    platform = request_data['platform']
    if 'pushToken' in request_data:
        pushToken = request_data['pushToken']
    if 'voipToken' in request_data:
        voipToken = request_data['voipToken']
    if 'production' in request_data:
        production = request_data['production']
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/user/requestCode', methods=['POST'])
def user_requestCode():
    global response
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if (not 'userPhone' in request_data) or len(request_data['userPhone'])!=11:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    sms_code = int(str(randint(1, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9)))
    sms_text = os.getenv('KANNEL_TEXT') + str(sms_code)
    user_phone = int(request_data['userPhone'])
    temp_user = Temps(userphone=user_phone, smscode=sms_code)
    db.session.query(Temps).filter_by(userphone=int(user_phone)).delete()#перед этим добавить проверку на время и ответ ошибкой!
    db.session.add(temp_user)
    db.session.commit()
    kannel_params2 = (('to', user_phone), ('text', sms_text.encode('utf-16-be').decode('utf-8').upper()))
    try:
        response = requests.get(url=kannel_url, params=kannel_params + kannel_params2)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print(f'Success send sms to {user_phone} and text {sms_text}!')
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/user/restore', methods=['POST'])
def user_restore():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'contract' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    contract = request_data['contract']
    if (not 'contactId' in request_data) and (not 'code' in request_data):
        response = {'code':200,'name':'OK','message':'Хорошо','data':[{'id':'bfe5bc9e5d2b2501767a7589ec3c485c','contact':'sb**@*********.ru','type':'email'},{'id':'064601c186c73c5e47e8dedbab90dd11','contact':'8 (964) ***-*000','type':'phone'}]}
        return jsonify(response)
    if 'contactId' in request_data and (not 'code' in request_data):
        contactId = request_data['contactId']
        print(f"Кто-то сделал POST запрос contactId и передал {contactId}")
        response = app.response_class(status=204, mimetype='application/json')
        return response
    if (not 'contactId' in request_data) and 'code' in request_data:
        code = request_data['code']
        if code ==  code:
            print(f"Кто-то сделал POST запрос code и передал {code}")
            response = app.response_class(status=204, mimetype='application/json')
            return response
        else:
            response = {'code':403,'name':'Forbidden','message':'Запрещено'}
            abort (403)
    if 'comment' in request_data:
        comment = request_data['comment']
    if 'notification' in request_data:
        notification = request_data['notification']

@app.route('/api/user/sendName', methods=['POST'])
def user_sendName():
    global response
    access_verification(request.headers)
    if not request.get_json():
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    request_data = request.get_json()
    if not 'name' in request_data:
        response = {'code':422,'name':'Unprocessable Entity','message':'Необрабатываемый экземпляр'}
        abort (422)
    name = request_data['name']
    if not 'patronymic' in request_data:
        request_data['patronymic'] = None
    response = app.response_class(status=204, mimetype='application/json')
    return response

@app.route('/api/user/getBillingList', methods=['POST'])
def user_getBillingList():
    global response
    phone = access_verification(request.headers)
    response = requests.post(billing_url + "getlist", headers={'Content-Type':'application/json'}, data=json.dumps({'phone': phone})).json()
    return jsonify(response)

@app.route('/api/address/getHcsList', methods=['POST'])
def address_getHcsList():
    global response
    access_verification(request.headers)
    response = {'code':200,'name':'OK','message':'Хорошо','data':[{'houseId':'19260','address':'Липецк, ул. Катукова, дом 36 кв 18'},{'houseId':'6694','address':'Липецк, ул. Московская, дом 145 кв 3'}]}
    #phone = "89103523377"
    #logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    #logging.debug(repr(phone))
    #sub_sub_response = {'login':'00001','address':'Липецк, ул. Московская, дом 151 кв 63'}
    #sub_response2 = requests.post(billing_url, headers={'Content-Type':'application/json'}, data=json.dumps({'login': '00421'})).json()
    #sub_sub_response2 = {'login':'00421','address':'Липецк, ул. Катукова, дом 36 кв 138'}
    #response = {'code':200,'name':'OK','message':'Хорошо','data':[dict(list(sub_response.items()) + list(sub_sub_response.items())),dict(list(sub_response2.items()) + list(sub_sub_response2.items()))]}
    #response = {'code':200,'name':'OK','message':'Хорошо','data':[{'login':'00001','address':'Липецк, ул. Катукова, дом 36 кв 138'},{'login':'00421','address':'Липецк, ул. Московская, дом 151 кв 63'}]}
    ###response = {'code':204,'name':'OK','message':'Хорошо','data':[]}
#    response = {'code':200,'name':'OK','message':'Хорошо',}
    return jsonify(response)

@app.errorhandler(401)
def not_found(error):
    return make_response(jsonify(response), 401)

@app.errorhandler(403)
def not_found(error):
    return make_response(jsonify(response), 403)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'пользователь не найден'}), 404)

@app.errorhandler(410)
def not_found(error):
    return make_response(jsonify({'error': 'авторизация отозвана'}), 410)

@app.errorhandler(422)
def not_found(error):
    return make_response(jsonify(response), 422)

@app.errorhandler(424)
def not_found(error):
    return make_response(jsonify({'error': 'неверный токен'}), 424)

@app.errorhandler(429)
def not_found(error):
    return make_response(jsonify({'code':429,'name':'Too Many Requests','message':'Слишком много запросов'}), 429)

if __name__ == '__main__':
    app.run(debug=True)
