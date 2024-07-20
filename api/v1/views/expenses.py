#!/usr/bin/python3
""" routes that handle all default RestFul API actions for expenses """
from models.expense import Expense
from decimal import Decimal
from models import storage
from models.user import User
from models.collection import Collection
from datetime import datetime
from api.v1.views import app_views
from flask import abort, jsonify, request
from flasgger.utils import swag_from
from models import storage
from flask import jsonify
from os import getenv


@app_views.route('/expenses', methods=['POST'], strict_slashes=False)
def post_expense():
    """ posts an expense to the database """
    data = request.get_json()
    if not request.get_json():
        abort(400, description="Not a JSON")
    name = data.get("name")
    purchase_date = data.get("purchase_date")
    price = data.get("price")
    user_id = data.get("user_id")
    collection_id = data.get("collection_id")

    if name is None:
        abort(400, description="Missing name")
    if purchase_date is None:
        abort(400, description="Missing purchase_date")
    if price is None:
        abort(400, description="Missing price")
    if user_id is None:
        abort(400, description="Missing user_id")
    if collection_id is None:
        abort(400, description="Missing collection_id")

    if purchase_date:
        try:
            datetime.strptime(purchase_date, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            abort(400, description="invalid date format")
    if type(price) not in [int, float]:
        abort(400, description="invalid currency input")
    else:
        try:
            price = Decimal(price)
            if price > Decimal('99999999.99'):
                abort(400, description='Price is too large')
            if price <= 0:
                abort(400, description='Price is too loo')
        except Exception as e:
            abort(400, description='invalid price')
    if type(user_id) not in [str]:
        abort(400, description="invalid user id input")
    if collection_id and type(collection_id) not in [str]:
        abort(400, description="invalid collection id input")

    user = storage.get(User, user_id)
    if not user:
        abort(400, description="user with that id does not exists")
    collection = storage.get(Collection, data["collection_id"])
    if not collection:
        abort(400, description="create a budget first")

    instance = Expense(**data)
    try:
        collection.amount_spent += Decimal(instance.price)
        collection.check_notifications()
    except Exception as e:
        print(e)
        abort(500, description=e)
    data = request.get_json()
    #expired collection may have been deleted at time of saving
    try:
        collection.save()
    except Exception as e:
        abort(400, description="{} no longer exists".format(collection.name))
    instance.save()
    return jsonify(instance.to_dict()), 201


@app_views.route('/<user_id>/expenses', methods=['GET'], strict_slashes=False)
def get_user_expenses(user_id):
    """ returns collections beloging to particular user"""
    storage.reload()
    user = storage.get(User, user_id)
    if user is None:
        print("no user found")
        abort(404)
    count = request.args.get('count', type=int)

    expenses = storage.user_all(user_id, Expense)
    if count and isinstance(count, int):
        expenses = expenses[:count]

    expenses_dict = [expense.to_dict() for expense in expenses]
    return jsonify(expenses_dict), 200


@app_views.route('/<user_id>/expenses/<expense_id>',
                 methods=['DELETE'],
                 strict_slashes=False)
def delete_expense(user_id, expense_id):
    """ deletes an expense belonging to particular user id given from storage """
    user = storage.get(User, user_id)
    if not user:
        abort(404)
    expense = storage.get(Expense, expense_id)
    if not expense:
        abort(404)
    if getenv("SPENDSMART_TYPE_STORAGE") == 'db':
        if expense.collection:
            expense.collection.amount_spent -= expense.price
    else:
        collection = storage.get(Collection, expense.collection_id)
        if collection:
            collection.amount_spent -= expense.price
            collection.save()
            collection.check_notifications()
    expense.delete()
    storage.save()
    return jsonify({"success": True}), 204


@app_views.route('/<user_id>/expenses/<expense_id>',
                 methods=['PUT'],
                 strict_slashes=False)
def update_expense(user_id, expense_id):
    """ updates the details of an expense """
    user = storage.get(User, user_id)
    if not user:
        abort(404)
    expense = storage.get(Expense, expense_id)
    initial_price = expense.price
    old_collection = storage.get(Collection, expense.collection_id)
    if not expense:
        abort(404)
    data = request.get_json()
    data["id"] = expense_id
    data["user_id"] = user_id
    for key, val in data.items():
        if hasattr(expense, key):
            setattr(expense, key, val)
    expense.save()
    new_collection = storage.get(Collection, expense.collection_id)
    if new_collection:
        if new_collection.id != old_collection.id:
            new_collection.amount_spent = new_collection.amount_spent + Decimal(
                expense.price)
            old_collection.amount_spent = old_collection.amount_spent - Decimal(
                initial_price)
        else:
            old_collection.amount_spent = (old_collection.amount_spent -
                                           Decimal(initial_price)) + Decimal(
                                               expense.price)
        old_collection.save()
        new_collection.save()
        new_collection.check_notifications()
        old_collection.check_notifications()

    return jsonify(expense.to_dict()), 200
