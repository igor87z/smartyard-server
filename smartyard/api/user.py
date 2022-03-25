import re

from flask import Blueprint, Response, abort, current_app, jsonify, request

from smartyard.exceptions import NotFoundCodeAndPhone, NotFoundCodesForPhone
from smartyard.logic.users_bank import UsersBank
from smartyard.proxy.billing import Billing
from smartyard.proxy.kannel import Kannel
from smartyard.utils import access_verification, json_verification

user_branch = Blueprint("user", __name__, url_prefix="/user")


@user_branch.route("/addMyPhone", methods=["POST"])
@access_verification
@json_verification(("login", "password"))
def add_my_phone() -> Response:
    request_data = request.get_json() or {}
    login = request_data.get("login")
    password = request_data.get("password")
    comment = request_data.get("comment", "")
    notification = request_data.get("notification", "")

    return Response(status=204, mimetype="application/json")


@user_branch.route("/appVersion", methods=["POST"])
@access_verification
@json_verification(("version", "platform"))
def app_version() -> Response:
    request_data = request.get_json() or {}
    version = request_data.get("version")
    platform = request_data.get("platform")

    if platform not in ("android", "ios"):
        abort(
            422,
            {
                "code": 422,
                "name": "Unprocessable Entity",
                "message": "Необрабатываемый экземпляр",
            },
        )
    return jsonify({"code": 200, "name": "OK", "message": "Хорошо", "data": "upgrade"})


@user_branch.route("/confirmCode", methods=["POST"])
@json_verification(("userPhone",))
def confirm_code() -> Response:
    request_data = request.get_json() or {}
    user_phone = request_data.get("userPhone", "")
    sms_code = request_data.get("smsCode", "")
    name = request_data.get("name")
    patronymic = request_data.get("patronymic")
    email = request_data.get("email")

    if not re.match(r"^\d{11}$", user_phone) or not re.match(r"^\d{4}$", sms_code):
        abort(
            422,
            {
                "code": 422,
                "name": "Unprocessable Entity",
                "message": "Необрабатываемый экземпляр",
            },
        )

    try:
        access_token = UsersBank.save_user(
            user_phone=int(user_phone),
            sms_code=int(sms_code),
            name=name,
            patronymic=patronymic,
            email=email,
        )
    except NotFoundCodesForPhone:
        abort(404, {"code": 404, "name": "Not Found", "message": "Не найдено"})
    except NotFoundCodeAndPhone:
        abort(
            403,
            {
                "code": 403,
                "name": "Пин-код введен неверно",
                "message": "Пин-код введен неверно",
            },
        )
    else:
        return jsonify(
            {
                "code": 200,
                "name": "OK",
                "message": "Хорошо",
                "data": {
                    "accessToken": access_token,
                    "names": {
                        "name": name,
                        "patronymic": patronymic,
                    },
                },
            }
        )


@user_branch.route("/getPaymentsList", methods=["POST"])
@access_verification
def get_payments_list():
    config = current_app.config["CONFIG"]
    return jsonify(Billing(config.BILLING_URL).get_list(request.environ["USER_PHONE"]))


@user_branch.route("/notification", methods=["POST"])
@access_verification
def notification():
    money = "t"
    enable = "t"
    return jsonify(
        {
            "code": 200,
            "name": "OK",
            "message": "Хорошо",
            "data": {"money": money, "enable": enable},
        }
    )


@user_branch.route("/ping", methods=["POST"])
@access_verification
def ping():
    return Response(status=204, mimetype="application/json")


@user_branch.route("/pushTokens", methods=["POST"])
@access_verification
def push_tokens():
    return jsonify(
        {
            "code": 200,
            "name": "OK",
            "message": "Хорошо",
            "data": {
                "pushToken": "fnTGJUfJTIC61WfSKWHP_N:APA91bGbnS3ck-cEWO0aj4kExZLsmGGmhziTu2lfyvjIpbmia5ahfL4WlJrr8DOjcDMUo517HUjxH4yZm0m5tF89CssdSsmO6IjcrS1U_YM3ue2187rc9ow9rS0xL8Q48vwz2e6j42l1",
                "voipToken": "off",
            },
        }
    )


@user_branch.route("/registerPushToken", methods=["POST"])
@access_verification
@json_verification(("platform",))
def register_push_token():
    request_data = request.get_json() or {}
    platform = request_data.get("platform")
    pushToken = request_data.get("pushToken")
    voipToken = request_data.get("voipToken")
    production = request_data.get("production")

    return Response(status=204, mimetype="application/json")


@user_branch.route("/requestCode", methods=["POST"])
@json_verification(("userPhone",))
def request_code():
    request_data = request.get_json() or {}
    user_phone = request_data.get("userPhone", "")
    if not re.match(r"^\d{11}$", user_phone):
        abort(
            422,
            {
                "code": 422,
                "name": "Unprocessable Entity",
                "message": "Необрабатываемый экземпляр",
            },
        )
    sms_code = UsersBank().generate_code(int(user_phone))
    Kannel(current_app.config["CONFIG"]).send_code(sms_code)

    return Response(status=204, mimetype="application/json")


@user_branch.route("/restore", methods=["POST"])
@access_verification
@json_verification(("contract",))
def restore():
    request_data = request.get_json() or {}
    contract = request_data.get("contract")
    comment = request_data.get("comment")
    notification = request_data.get("notification")
    contact_id = request_data.get("contactId")
    code = request_data.get("code")

    if not contact_id and not code:
        return jsonify(
            {
                "code": 200,
                "name": "OK",
                "message": "Хорошо",
                "data": [
                    {
                        "id": "bfe5bc9e5d2b2501767a7589ec3c485c",
                        "contact": "sb**@*********.ru",
                        "type": "email",
                    },
                    {
                        "id": "064601c186c73c5e47e8dedbab90dd11",
                        "contact": "8 (964) ***-*000",
                        "type": "phone",
                    },
                ],
            }
        )
    if contact_id and not code:
        print(f"Кто-то сделал POST запрос contactId и передал {contact_id}")
        return Response(status=204, mimetype="application/json")
    if not contact_id and code:
        if code == code:  # TODO: Проверить странное условие
            print(f"Кто-то сделал POST запрос code и передал {code}")
            return Response(status=204, mimetype="application/json")
        else:
            abort(403, {"code": 403, "name": "Forbidden", "message": "Запрещено"})
    # TODO: Нужен вариант по умлочанию: пока такой
    return Response(status=204, mimetype="application/json")


@user_branch.route("/sendName", methods=["POST"])
@access_verification
@json_verification(("name",))
def send_name():
    request_data = request.get_json() or {}
    name = request_data.get("name")
    patronymic = request_data.get("patronymic")
    return Response(status=204, mimetype="application/json")


@user_branch.route("/getBillingList", methods=["POST"])
@access_verification
def get_billing_list():
    config = current_app.config["CONFIG"]
    return jsonify(Billing(config.BILLING_URL).get_list(request.environ["USER_PHONE"]))
