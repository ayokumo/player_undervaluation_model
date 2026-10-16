# Live demo on AWS (Step 5)

Deployed on 2026-10-16 by hand from the AWS console, then `docker compose` on the server. Nothing here is automated.

## What is running
* One EC2 instance, `t3.small` (2 GiB memory), Ubuntu Server 26.04 LTS, region us-east-2 (Ohio), 20 GiB gp3 disk, 2 GiB swap file.
* The same `docker-compose.yml` as local use: a Postgres container with pgvector (loaded from `deploy/demo_db.sql.gz` on first start) and the app container. `APP_PORT=80` publishes the app on port 80.
* Address as of 2026-10-16: http://3.135.18.66 (plain HTTP, no domain, no HTTPS yet). The address is the instance's public IP and changes if the instance is stopped and started.
* Account: AWS free account plan, which runs for 6 months or until the credits are used.

## Firewall (security group)
* SSH (22) from one address only (the owner's home IP at launch time).
* HTTP (80) from anywhere.
* The database port is not published, so only the app container can reach Postgres.

## Cost and spend protection
* AWS Budgets zero spend alert emails the owner when spending passes one cent.
* App limits (set in the server `.env`): 300 characters per question, per IP and total questions per day. See `DAILY_LIMIT_PER_IP` and `DAILY_LIMIT_TOTAL`.
* The Anthropic API is paid by token. Set a monthly spend limit in the Anthropic console as the last line of defense.

## Problems met during the first deployment
* The first image build failed with "No space left on device": the instance had the default 8 GiB disk. Fix: grow the volume to 20 GiB in the console, then `growpart` and `resize2fs`.
* On the owner's laptop an old `ANTHROPIC_API_KEY` exported in the shell overrode the project `.env`. Docker Compose prefers shell values. Fix: `unset ANTHROPIC_API_KEY` before running compose.

## Steps (short version)
1. Launch the instance as above, with the key pair, then `ssh -i key.pem ubuntu@<ip>`.
2. `sudo apt-get install -y docker.io docker-compose-v2 git`, enable docker, add the user to the docker group, add a swap file.
3. `git clone https://github.com/ayokumo/player_undervaluation_model.git`, write `.env` with `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `APP_PORT=80`, and the two daily limits.
4. `docker compose up -d --build`, then check `docker compose ps` and `curl localhost/health`.

## Limits of this demo
* HTTP only, on a bare IP. A domain and HTTPS would be the next step.
* One small server, no autoscaling, no monitoring beyond the container health checks.
* The free plan ends after 6 months. Delete the instance, volume and address then, or upgrade, or the demo goes offline.
