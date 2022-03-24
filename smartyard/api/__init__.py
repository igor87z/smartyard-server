import json
from flask import Blueprint, Response

from .address import address_branch
from .cctv import cctv_branch
from .ext import ext_branch
from .frs import frs_branch
from .geo import geo_branch
from .inbox import inbox_branch
from .issues import issues_branch
from .pay import pay_branch
from .root import root_branch
from .sip import sip_branch
from .user import user_branch

__all__ = ["api"]

api = Blueprint("api", __name__, url_prefix="/api")

for branch in {
    root_branch,
    address_branch,
    cctv_branch,
    ext_branch,
    frs_branch,
    geo_branch,
    inbox_branch,
    issues_branch,
    pay_branch,
    sip_branch,
    user_branch,
}:
    api.register_blueprint(branch)


@api.errorhandler(401)
def unauthorized(error) -> Response:
    return Response(
        response=json.dumps(error.description),
        status=401,
        content_type="application/json",
    )


@api.errorhandler(403)
def forbidden(error):
    return Response(
        response=json.dumps(error.description),
        status=403,
        content_type="application/json",
    )


@api.errorhandler(404)
def not_found(error):
    return Response(
        response=json.dumps(error.description),
        status=404,
        content_type="application/json",
    )


@api.errorhandler(410)
def gone(error):
    return Response(
        response=json.dumps({"error": "авторизация отозвана"}),
        status=410,
        content_type="application/json",
    )


@api.errorhandler(422)
def unprocessable_entity(error):
    return Response(
        response=json.dumps(error.description),
        status=422,
        content_type="application/json",
    )


@api.errorhandler(424)
def failed_dependency(error):
    return Response(
        response=json.dumps({"error": "неверный токен"}),
        status=424,
        content_type="application/json",
    )


@api.errorhandler(429)
def too_many_requests(error):
    return Response(
        response=json.dumps(
            {
                "code": 429,
                "name": "Too Many Requests",
                "message": "Слишком много запросов",
            }
        ),
        status=429,
        content_type="application/json",
    )
