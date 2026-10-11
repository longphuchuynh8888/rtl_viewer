# core/paths.py
"""Duong dan file du lieu, luon nam o goc project."""

import os

# core/paths.py -> len 1 cap la goc project
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data(name):
    return os.path.join(ROOT, name)


DEVICES = data("devices.json")
AWS_URLS = data("aws_urls.json")
APPS = data("managed_apps.json")
ACCOUNTS = data("google_accounts.json")
SCREENSHOTS = data("rtl_screenshots")
SCRIPTS = data("ui_scripts")
