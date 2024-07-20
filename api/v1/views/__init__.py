#!/usr/bin/python3
""" Blueprint for API """
from flask import Blueprint

app_views = Blueprint('app_views', __name__, url_prefix='/api/v1')
from api.v1.views.collections import *
from api.v1.views.expenses import *
from api.v1.views.notifications import *
from api.v1.views.users import *
