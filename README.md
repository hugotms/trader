# Trader

This algorithm has been created by Hugo TOMASI in order to be used with Bitpanda Pro API server. It is used to monitor your trades fluctuation and cancel them if necessary.

In any case would this program be allowed to buy stocks on your behalf.

## Requirements

For this to work, you must have a Bitpanda Pro account that have been verified and an API key (with at least `Read` and `Trade` scopes).

No active trade is necessarry to allow the program to run. If you have some running trade, this program will pick them and monitor them, until it (or you) cancel the active trade.

You will also need a computer with Docker (or Podman) installed in order to run the program. If you are aware of what you're doing, you could also run this program bare metal, on any computer that support Python 3.8. You will however have to manage dependencies yourself.

A running MongoDB instance is required for this program to work accordingly.

The server you will run this program on must be able to access outside world on port 443/TCP and 27017/TCP and must be able to resolve URLs (must have configured nameservers).

If you want to receive mail alert on action took by the bot, please make sure that outside world is also reachable on port defined for your SMTP server.

## Variables

| Variable      | Description       | Required | Default |
|---------------|-------------------|----------|---------|
| `EXCHANGE_API_KEY`       | Your Bitpanda Pro API token used to connect to the API            | yes      | None       |
| `MONGO_DB_HOST`       | The MongoDB hostname (FQDN or IP)            | yes      | None       |
| `MONGO_DB_PASSWORD`       | The MongoDB password            | yes      | None       |
| `MONGO_DB_NAME`       | The MongoDB database            | no      | trader       |
| `MONGO_DB_USER`       | The MongoDB username            | no      | trader       |
| `MONGO_DB_PORT`       | The MongoDB port            | no      | 27017       |
| `MIN_RECOVERED_RATE`       | The rate you want to get if stock goes down            | no      | 0.95       |
| `MIN_PROFIT_RATE`          | The rate from which you may take profit if considered dangerous        | no      | 1.05       |
| `MAX_DANGER`              | The maximum danger level an action can be running       | no         | 10        |
| `MINUTES_REFRESH_TIME`       | The number of minutes between two checks            | no      | 10       |
| `WATCHING_CRYPTOS`       | By default, the bot watches all crytos for which you have trades going on. You can, however, specify cryptos to look for and thus ignore the rest.            | no      | None       |
| `TAXE_RATE`          | The rate from which your country/state taxes profit (useful if you want a report of how much you really own)        | no      | 0.0      |
| `SEND_ALERT_MAIL`       | If set to `true`, allow the user to be alerted by mail on any action            | no      | False      |
| `SMTP_HOST`       | The SMTP server which you're going to use to send mail (required if `SEND_ALERT_MAIL="True"`)            | no      | None       |
| `SMTP_PORT`       | The port of the SMTP server which you're going to use to send mail (required if `SEND_ALERT_MAIL="True"`)            | no      | None       |
| `SMTP_AS`       | The sender name which you're going to use to send mail         | no      | None       |
| `SMTP_FROM`       | The email address which you're going to use to send mail (required if `SEND_ALERT_MAIL="True"`)            | no      | None       |
| `SMTP_KEY`       | The token used to connect to your account (required if `SEND_ALERT_MAIL="True"`)            | no      | None       |
| `SMTP_TO`       | The email addresses to whom you want to send the email separated by a comma (default to `SMTP_FROM`)            | no      | None       |

## Build

In order to build the image, you need to clone this repository then simply run (replace `docker` by `podman` if needed) :

```bash
docker build -t trader:2.0.0 https://raw.githubusercontent.com/hugotms/trader/v2.0.0/Dockerfile
```

## Deploy

### CLI

After the image has been built, you can now run it like so (add any non required extra environment variables you want to modify preceeded by a `-e`) :

```bash
docker run -d --name trader -e EXCHANGE_API_KEY=token -e MONGO_DB_HOST=hostname -e MONGO_DB_PASSWORD=secure trader:2.0.0
```

### Docker-compose

If you prefer the docker-compose solution, here is a simple example of a stack:

````yaml
version: '3.1'
services:
  trader:
    image: trader:2.0.0
    restart: unless-stopped
    depends_on: mongo_db
    environment:
      EXCHANGE_API_KEY: token
      MONGO_DB_HOST: mongo_db
      MONGO_DB_PASSWORD: secure
      # add here any non required variable

  mongo_db:
    image: mongo:5.0-focal
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: trader
      MONGO_INITDB_ROOT_PASSWORD: secure
````

## Disclaimer

Some variables can change this program comportement, response time and liability. Some required variables may be needed and will make the program fail if not properly defined.

However, some variables do have default value. They may, or may not suit your needs. Be sure to initialized them in a way that works for you.

This program is not guaranteed to be free of any bug. If you do find one, please, do not hesitate to propose a correction in a PR. Remember, be kind and respectful. No PR is guaranteed to be accepted and the author is not required to give any reason about that.

Please, note that the author of this code is not responsible of any loss you may endure and thus, can, in no case, be the target of legal proceedings. As for every financial placement, you should monitor it yourself and not blindly trust technology. Especially if you do not understand this code and what it's doing.
You are, at all time able to cancel an order the classical way (via Bitpanda Pro web interface or application).
