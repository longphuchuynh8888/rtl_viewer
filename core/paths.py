# core/paths.py
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def data(name):
    return os.path.join(ROOT, name)

DEVICES = data("devices.json")
AWS_URLS = data("aws_urls.json")
APPS = data("managed_apps.json")
ACCOUNTS = data("google_accounts.json")
SCREENSHOTS = data("rtl_screenshots")