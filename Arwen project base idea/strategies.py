import config, json, os
from pprint import pprint
import pandas as pd



class tradeStrategy():

    def __init__(self, exchange):

        self.test = config.isTest

        if self.test==True:
            self.testCapital = config.testCapital
            self.tradeCapital = config.testCapital
            self.testAccount = config.testAccount
            self.fees = config.trade_fee
            self.logfilename = config.symbol+"test_trade_log."+config.format
            config.filename = self.logfilename
            self.exchange = exchange
        
        else:
            self.Capital = config.Capital
            self.tradeCapital = config.Capital
            self.logfilename = config.symbol+"real_trade_log."+config.format
            config.filename = self.logfilename
            self.exchange = exchange

        self.orderData = {"buys":[], 
                          "sells":[], 
                          "average buy price":0, 
                          "average sell price":0, 
                          "total fees":0, 
                          "profit":0}

        with open(self.logfilename, "w") as file:
            data={
                    "orders": [],
                    "total profit": 0,
                    "total fees paid": 0
                }
            json.dump(data, file, indent=4)


    def logData(self, data: dict):

        f = open(self.logfilename, "r")
        content = f.read()
        f.close()

        # Write JSON string to a text file
        with open(self.logfilename, "w") as file:
                    
            content = json.loads(content)
            orders = list(content["orders"])                    
            orders.append(data)
            content["orders"] = orders
            content["total profit"] = sum([order["profit"] for order in orders])
            content["total fees paid"] = sum([order["total fees"] for order in orders])
            json.dump(content, file, indent=4)

            
    def buy(self, price, time):

        if self.test:

            if ((len(self.orderData["buys"]) != 0) and (price < self.orderData['average buy price'])) or (len(self.orderData["buys"]) == 0):
                
                if (self.testAccount-self.tradeCapital) < 0:
                    return "Lack of capital!"

                self.testAccount = self.testAccount - self.tradeCapital
                self.orderData["buys"].append({"price": price, 
                                       "amount": self.tradeCapital,
                                       "quantity": (self.tradeCapital * (1-self.fees)) / price, 
                                       "fees": self.tradeCapital * self.fees})
                buys = self.orderData["buys"]
                total_amount = sum([b["amount"] for b in buys])
                total_quantity = sum([b["quantity"] for b in buys])
                total_fees = sum([b["fees"] for b in buys])
                self.orderData["average buy price"] = total_amount/total_quantity
                self.orderData["total fees"] = total_fees
                self.tradeCapital = self.tradeCapital * 2

                print("Buy | price : {} | amount : {} | quantity : {} |".format(price, self.tradeCapital/2, self.orderData["buys"][-1]["quantity"]))

                return True

        else:

            if ((len(self.orderData["buys"]) != 0) and (price < self.orderData['average buy price'])) or (len(self.orderData["buys"]) == 0):

                exchange = self.exchange
                quoteCurrencyBalance = exchange.getAcBalance('quote')

                if (quoteCurrencyBalance-self.tradeCapital) < 0:
                    return "Lack of capital!"
                
                order = exchange.placeMarketOrder('buy', self.tradeCapital)
                price = order['price']
                amount = order['cummulativeQuoteQty']
                quantity = order['executedQty']
                fills = order['fills']
                self.orderData["buys"].append({"price": price, 
                                       "amount": amount,
                                       "quantity": quantity,
                                       "fees": sum([fill['commission'] for fill in fills])
                                       })
                buys = self.orderData["buys"]
                total_amount = sum([b["amount"] for b in buys])
                total_quantity = sum([b["quantity"] for b in buys])
                total_fees = sum([b["fees"] for b in buys])
                self.orderData["average buy price"] = total_amount/total_quantity
                self.orderData["total fees"] = total_fees
                self.tradeCapital = self.tradeCapital * 2


    def sell(self, price, time):

        if self.test:

            if len(self.orderData['buys'])>0:

                buys = self.orderData["buys"]
                total_amount = sum([b["amount"] for b in buys])
                total_quantity = sum([b["quantity"] for b in buys])
                total_fees = sum([b["fees"] for b in buys])
                fee = price * total_quantity * (self.fees)
                returns = (price * total_quantity) - (fee)
                profit = returns - total_amount
                total_fees = total_fees + fee
                self.orderData["sells"].append({"price": price, 
                                                "amount": returns, 
                                                "quantity": total_quantity, 
                                                "fees": fee})
                self.orderData["average sell price"] = price
                self.orderData["total fees"] = total_fees + fee
                self.orderData["profit"] = profit
                self.tradeCapital = self.testCapital
                self.testAccount = self.testAccount + returns

                print("\nSell | price : {} | amount : {} | quantity : {} | profit : {}\n".format(price, returns, total_quantity, profit))

                self.logData(self.orderData)

                self.resetOrderData()

                return True

        else:

            if len(self.orderData['buys'])>0:

                exchange = self.exchange
                buys = self.orderData["buys"]
                total_amount = sum([b["amount"] for b in buys])
                total_quantity = sum([b["quantity"] for b in buys])
                total_fees = sum([b["fees"] for b in buys])
                fee = price * total_quantity * (self.fees)
                returns = (price * total_quantity) - (fee)
                profit = returns - total_amount
                total_fees = total_fees + fee

                baseCurrencyBalance = exchange.getAcBalance('base')
                order = self.exchange.placeMarketOrder('sell', baseCurrencyBalance)
                price = order['price']
                amount = order['cummulativeQuoteQty']
                quantity = order['executedQty']
                fills = order['fills']
                fee = sum([fill['commission'] for fill in fills]) * price
                self.orderData["buys"].append({"price": price, 
                                       "amount": amount,
                                       "quantity": quantity,
                                       "fees": fee
                                       })

                self.orderData["average sell price"] = price
                self.orderData["total fees"] = total_fees + fee
                self.orderData["profit"] = profit
                self.tradeCapital = self.testCapital
                self.testAccount = self.testAccount + returns

                print("\nSell | price : {} | amount : {} | quantity : {} | profit : {}\n".format(price, returns, total_quantity, profit))

                self.logData(self.orderData)

                self.resetOrderData()

                return True

    
    def resetOrderData(self):

        self.orderData = {"buys":[], 
                          "sells":[], 
                          "average buy price":0, 
                          "average sell price":0, 
                          "total fees":0, 
                          "profit":0}

        self.tradeCapital = config.testCapital


    def getData(self):
        return self.orderData



