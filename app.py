#!/usr/bin/env python3
import os
import dotenv
import json
import requests
import base64
from packaging import version as packaging_version

import time
from datetime import datetime, timedelta

from prometheus_client import start_http_server

def load_env_vars():
    dotenv.load_dotenv(dotenv.find_dotenv('.env'))

    global poll_interval_min
    poll_interval_min = float(os.getenv('poll_interval_min'))

    global prometheus_port
    prometheus_port = os.getenv('prometheus_port')

    global github_config_enabled, github_user, github_token, github_repo
    github_config_enabled = bool(os.getenv('github_config_enabled'))
    github_user = os.getenv('github_user')
    github_token = os.getenv('github_token')
    github_repo = os.getenv('github_repo')

    global telegram_enabled, telegram_key, telegram_chat_id
    telegram_enabled = bool(os.getenv('telegram_enabled'))
    telegram_key = os.getenv('telegram_key')
    telegram_chat_id = os.getenv('telegram_chat_id')

    global slack_enabled, slack_webhook_url
    slack_enabled = bool(os.getenv('slack_enabled'))
    slack_webhook_url = os.getenv('slack_webhook')

def prometheus_metrics():
    """ Export various Prometheus metrics """

    start_http_server(int(prometheus_port))
    print(f'{datetime.now()} [INFO] Prometheus Metrics exporting on port: {str(prometheus_port)}')
    return

def send_operator_alert(message):
    if telegram_enabled:
        send_telegram_alert(message)
    if slack_enabled:
        send_slack_alert(message)

def send_telegram_alert(message):
    response = requests.post(f'https://api.telegram.org/bot{telegram_key}/sendMessage?chat_id={telegram_chat_id}&disable_web_page_preview=true&parse_mode=HTML&text={message}')
    if response.status_code == 200:
        print(f'{datetime.now()} [INFO] Message sent to Telegram successfully')
    else:
        print(f'{datetime.now()} [INFO] Failed to send message to Telegram. Status code: {response.status_code}')

def send_slack_alert(message):
    """ Function to send a message to Slack """
    payload = {
        'text': message
    }
    response = requests.post(slack_webhook_url, json.dumps(payload))
    if response.status_code == 200:
        print(f'{datetime.now()} [INFO] Message sent to Slack successfully')
    else:
        print(f'{datetime.now()} [INFO] Failed to send message to Slack. Status code: {response.status_code}')

def fetch_github_config():
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {github_token}'
    }
    github_config_url = f'https://api.github.com/repos/{github_user}/{github_repo}/contents/repos-to-track.json'
    response = requests.get(github_config_url, headers=headers)
    if response.status_code == 200:
        github_config = json.loads(base64.b64decode(response.json()["content"]).decode("utf-8"))
        return github_config
    else:
        print(f'{datetime.now()} [INFO] Failed to fetch GitHub config with status code {response.status_code}')
        return None

def check_for_new_or_downgrade_release():
    """ Function to check for new releases and downgrade releases """

    # Load configurations from the github repo JSON file
    if github_config_enabled:
        github_repo_configs = fetch_github_config()
    else:
        with open('repos-to-track.json', 'r') as config_file:
            github_repo_configs = json.load(config_file)

    if github_repo_configs is None:
        return

    # Loop through each owner/repo combination in the configurations
    for config in github_repo_configs:
        github_repo_owner = config.get('github_repo_owner', 'N/A')
        github_repo_name = config.get('github_repo_name', 'N/A')

        url = f'https://api.github.com/repos/{github_repo_owner}/{github_repo_name}/releases/latest'
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            release_info = response.json()

            repo_name = f'{github_repo_owner}/{github_repo_name}'
            tag_name = release_info.get('tag_name', 'N/A')
            html_url = release_info.get('html_url', 'N/A')

            print(f'{datetime.now()} [INFO] Repo: {repo_name}')
            print(f'{datetime.now()} [INFO] Current Release: {tag_name}')
            print(f'{datetime.now()} [INFO] URL: {html_url}')

            # Create the "targets" subfolder if it doesn't exist
            targets_folder = 'targets'
            if not os.path.exists(targets_folder):
                os.makedirs(targets_folder)

            previous_release_filename = os.path.join(targets_folder, f'{github_repo_owner}_{github_repo_name}.json')

            # Check if the release is different from the previous one
            if os.path.exists(previous_release_filename):
                with open(previous_release_filename, 'r') as file:
                    previous_release_info = json.load(file)

                old_version_str = previous_release_info.get('tag_name', 'N/A')
                new_version_str = release_info.get('tag_name', 'N/A')

                print(f'{datetime.now()} [INFO] Old Version String: {old_version_str}')
                print(f'{datetime.now()} [INFO] New Version String: {new_version_str}')

                if new_version_str != 'N/A' and old_version_str != 'N/A':
                    old_version = packaging_version.parse(old_version_str)
                    new_version = packaging_version.parse(new_version_str)

                    # Compare versions as integers
                    if old_version < new_version:
                        print(f'{datetime.now()} [INFO] Upgrade release for {github_repo_owner}/{github_repo_name} | Old version: {old_version_str} | New version: {new_version_str} | {release_info["html_url"]}')
                        message = f'Upgrade release for {github_repo_owner}/{github_repo_name}:\nOld version: {old_version_str}\nNew version: {new_version_str}\n{release_info["html_url"]}'
                        send_operator_alert(message)
                    elif old_version > new_version:
                        print(f'{datetime.now()} [INFO] Downgrade release for {github_repo_owner}/{github_repo_name} | Old version: {old_version_str} | New version: {new_version_str} | {release_info["html_url"]}')
                        message = f'Downgrade release for {github_repo_owner}/{github_repo_name}:\nOld version: {old_version_str}\nNew version: {new_version_str}\n{release_info["html_url"]}'
                        send_operator_alert(message)
                else:
                    print(f'{datetime.now()} [ERROR] Invalid version strings. Skipping alert message.')

            with open(previous_release_filename, 'w') as file:
                json.dump(release_info, file, indent = 4)  # Update the owner_repo.json

        except requests.exceptions.RequestException as e:
            print(f'{datetime.now()} [ERROR]: {e}')
        except json.JSONDecodeError as e:
            print(f'{datetime.now()} [ERROR]: Error decoding JSON: {e}')

def main():
    load_env_vars()
    # Check for new releases periodically
    while True:
        check_for_new_or_downgrade_release()
        print(f'{datetime.now()} [INFO] Waiting {poll_interval_min} minutes for next poll.')
        time.sleep(60 * poll_interval_min)

if __name__ == '__main__':
    main()
