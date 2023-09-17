# GitHub Release Alert Bot

The GitHub Release Alert Bot is a Python script that monitors multiple public GitHub repositories for new releases and sends alerts via Slack when new releases are detected. It also tracks downgrade releases and provides information about version changes.

## Features

- Monitor multiple public GitHub repositories for new releases.
- Send alerts to a Slack channel when a new release is detected.
- Track downgrade and upgrade releases and provide information about version changes to DevOps alert channels for operators.

## Prerequisites

Before you can use the GitHub Release Alert Bot, ensure you have the following prerequisites installed:

- Python 3.7
- Required Python packages (install using `pip`):
  - `requests`
  - `packaging`
  - `python-dotenv`
  - `prometheus-client`

## Setup
[0] Populate `.env`

[1] Ensure github `owner` and associated `repo` is in `repos-to-track.json`. Docker container will pull this `.json` config from github every poll interval for ease of updating. No need to login to the server hosting the docker container and editing configs, and restarting the container.

The format of `repos-to-track.json` is:
```
[
    {
        "github_repo_owner": "owner1",
        "github_repo_name": "repo1"
    },
    {
        "github_repo_owner": "owner2",
        "github_repo_name": "repo2"
    }
]
```
Replace `"owner1"` and `"repo1"`, etc.

[2] Clone github repo and start the docker container
```
sudo git clone https://github.com/Block-Farms/github-release-alert-bot.git && \
cd github-release-alert-bot/ && \
docker build -t githubalerter . && \
docker run \
  --restart always \
  -d \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=1 \
  --log-opt tag="{{.ImageName}}|{{.Name}}|{{.ImageFullID}}|{{.FullID}}" \
  -p 9999:9999 \
  --name github-alerter \
  githubalerter:latest && \
docker image prune -a -f && \
docker ps
```

[3] Ensure clean container start by reading Docker logs
```
docker logs --tail 100 github-alerter
```

[4] Verify Prometheus Endpoint to track container uptime to ensure DevOps operators always receieve alerts properly.
Can be modified but `.env.example` preset is port 9999.

http://localhost:9999/metrics
