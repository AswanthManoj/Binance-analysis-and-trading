import exchanges
import config
import threading
from pprint import pprint
from pushbullet import Pushbullet


###################################################################'''Socket connection'''###################################################################



pb = Pushbullet(config.pushbulletToken)
#push = pb.push_note("This is the title", "This is the body")
#to_buy = ["avax", "sol", "link"]
#push = pb.push_list("Buy list", to_buy)
#push = pb.push_link("Cool site", "https://github.com")
config.symbol = 'avaxbusd'
config.timeFrame = '1m'

exchange = exchanges.cryptoExchange(config.Binance_API_Key, config.Binance_Secret_Key, testnet= False)

exchange.marketConfig(config.symbol, config.timeFrame)

print(exchange.symbol)

exchange.loadData()

exchange_stream = exchanges.exchangeStream(config.symbol, config.timeFrame, exchange)
exchange_stream.socketConnect()

#thread = threading.Thread(target=exchange_stream.socketConnect)

#thread.start()