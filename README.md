# Trader

This algorithm has been created by Hugo TOMASI in order to be used with Bitpanda Pro API server. It is used to monitor your assets fluctuation and sell them if necessary.

In any case would this program be allowed to buy any currency on your behalf, unless you specify it (see variables below).

## Requirements

For this to work, you must have a Bitpanda Pro account that have been verified and an API key (with at least the `Read` and `Trade` scopes).

No active order is necessarry to allow the program to run. If you have some running orders, this program will pick them and monitor them, until it (or you) cancel the active trade.

You will also need a computer with Docker (or Podman) installed in order to run the program. If you are aware of what you're doing, you could also run this program bare metal, on any computer that support Python 3.8. You will however have to manage dependencies yourself. Make sure that your container runtime is enabled as a service and that the container is set to always restart. This will make sure the service is started upon reboot.

A running MongoDB instance is required for this program to work accordingly.

The server you will run this program on must be able to access outside world on port 443/TCP and the  TCP port defined for MongoDB (default to 27017). It also needs to be able to resolve URLs (must have configured nameservers).

If you want to receive mail alert on action took by the bot, please make sure that outside world is also reachable on port defined for your SMTP server.

## Variables

### Envrionment variables only

| Variable      | Description       | Required | Default |
|---------------|-------------------|----------|---------|
| `EXCHANGE_API_KEY`       | Your Bitpanda Pro API token used to connect to the API            | yes      | None       |
| `MONGO_DB_HOST`       | The MongoDB hostname (FQDN or IP)            | yes      | None       |
| `MONGO_DB_PASSWORD`       | The MongoDB password            | yes      | None       |
| `MONGO_DB_NAME`       | The MongoDB database            | no      | trader       |
| `MONGO_DB_USER`       | The MongoDB username            | no      | trader       |
| `MONGO_DB_PORT`       | The MongoDB port            | no      | 27017       |

### Other variables

| Variable      | Description       | Required | Default |
|---------------|-------------------|----------|---------|
| `MIN_RECOVERED_RATE`       | The minimum rate you want to recover if currency goes down.            | no      | 0.95       |
| `SECURITY_MIN_RECOVERED_RATE`       | The minimum rate you want to recover if currency goes down and server is down (places a stop loss order).            | no      | 0.9       |
| `MIN_PROFIT_RATE`          | The rate from which you take profit. Must be greater than `1.0` to activate. | no      | 1.0       |
| `MAX_DANGER`              | The maximum danger level a currency can be bought.       | no         | 5        |
| `MINUTES_REFRESH_TIME`       | The number of minutes between two checks.            | no      | 10       |
| `MINUTES_WAIT_TIME`       | The number of minutes between a selling order and a buying order on the same currency.            | no      | 10       |
| `WATCHING_CURRENCIES`       | By default, the bot watches all currencies that you bought. You can, however, specify currencies to look for and thus ignore the rest.            | no      | None       |
| `IGNORE_CURRENCIES`       | By default, the bot watches ll currencies that you bought. You can, however, specify cryptos to ignore. Note that if both this variable and `WATCHING_CURRENCIES` are set, this one will take precedence.            | no      | None       |
| `TAXE_RATE`          | The rate from which your country/state taxes profit (useful if you want a report of how much you really own)        | no      | 0.0      |
| `MAKE_ORDER`          | Specify if the bot is allowed to place order.       | no      | False    |
| `CANDLESTICKS_TIMEFRAME`          | Specify the timeframe at which crypto stats are required.      | no      | DAYS     |
| `CANDLESTICKS_PERIOD`          | Specify the period of unit at which crypto stats are required (1, 5, 15 or 30)       | no      | 1     |
| `WINDOW_SIZE_FMA`          | Specify the number of units looked at to calculate fast exponential moving average (must be lower than `WINDOW_SIZE_SMA`)       | no      | 5     |
| `WINDOW_SIZE_SMA`          | Specify the number of units looked at to calculate slow exponential moving average       | no      | 50     |
| `RSI_PERIOD`          | Specify the number of units looked at to calculate RSI       | no      | 14     |
| `OVERSOLD_THRESHOLD`          | Specify the RSI level to define oversold zone (from 0 to value)       | no      | 30     |
| `OVERBOUGHT_THRESHOLD`          | Specify the RSI level to define overbought zone (from value to 100)       | no      | 70     |
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
docker build -t trader:5.0.0 https://raw.githubusercontent.com/hugotms/trader/v5.0.0/Dockerfile
```

## Deploy

### CLI

After the image has been built, you can now run it like so (add any non required extra environment variables you want to modify preceeded by a `-e`) :

```bash
docker run -d --name trader --restart unless-stopped -e EXCHANGE_API_KEY=token -e MONGO_DB_HOST=hostname -e MONGO_DB_PASSWORD=secure trader:5.0.0
```

### Docker-compose

If you prefer the docker-compose solution, here is a simple example of a stack:

````yaml
version: '3.1'
services:
  trader:
    image: trader:5.0.0
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

This program is for educational purposes only !

Some variables can change this program comportement, response time and liability. Some required variables may be needed and will make the program fail if not properly defined.

However, some variables do have default value. They may, or may not suit your needs. Be sure to initialized them in a way that works for you.

This program is not guaranteed to be free of any bug. If you do find one, please, do not hesitate to submit a correction in a pull request (please be careful with your commit messages and make sure to respect the conventionnal commit rules). Remember, be kind and respectful between contributors. No pull request is guaranteed to be accepted and the author is not required to give any reason about that.

By using this program, you understand that there is no support tied to it. You are, of course able to raise an issue. Please note that any work on those issues will be done in a "Best effort".

Please, note that the author of this code is not responsible of any loss you may endure and thus, can, in no case, be the target of legal proceedings. As for every financial placement, you should monitor it yourself and not blindly trust technology. Especially if you do not understand this code and what it's doing.
You are, at all time able to cancel an order the classical way (via Bitpanda Pro web interface or application).

You should never invest with money you do not own nor that you need.
