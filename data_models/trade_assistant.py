import json
from typing import List
import random
from datetime import datetime

from collections import deque


class Market:
    """ This class contains information about the available formal markets where stock trading is enabled """
    NASDAQ = ["NASDAQ", "National Association of Securities Dealers Automated Quotation"]
    NYSE = ["NYSE", "New York Security Exchange"]


class Stock:
    """ Represents a stock, an investment instrument.
    Stocks represents the right to collect a part of the earnings of a Company. """
    ticker: str
    company: str
    market: str
    last_closing_price: float
    daily_variation: float

    def __init__(self):
        """ Create a new stock """
        self.ticker = ""
        self.company = ""
        self.market = Market.NASDAQ[0]

    def __init__(self, ticker=""):
        """ Create a new stock with ticker """
        self.ticker = ticker
        self.market = Market.NASDAQ[0]

    def to_string(self):
        """ returns a nice and handy text representation of the object """
        return "{0} ({1})".format(self.ticker, self.company)

    @staticmethod
    def get_current_price(self) -> float:
        # TODO: Logic to get the current price.
        # randomized for now, should simulate a connection with the Broker
        # a factory pattern can help if we want to make it capable of transacting with different Brokers
        return round(random.uniform(Constants.min_variation, Constants.max_variation), Constants.max_decimals)


class Operation:
    stock: Stock
    type: str
    buy: bool
    sell: bool
    # TODO: replace buy, sell for type_of_operation
    quantity: int
    amount: float
    tax: float
    commission: float
    time_stamp: datetime
    # TODO: Better use a multi state status: new, in-process, done, cancelled
    is_processed: bool

    # The tax is the same everywhere (in a country)
    # The commission depends of the Broker, some are cheap, others are not.

    def __init__(self):
        """ Create a new operation """
        self.buy = False
        self.sell = False
        self.quantity = 0
        self.amount = 0
        self.stock = Stock()
        self.time_stamp = datetime.now()
        self.is_processed = False


class BuyOperation(Operation):
    """ after processing, this will have to update | create the Holding """

    def __init__(self):
        super().__init__()


class SellOperation(Operation):
    """ after processing, this will have to update | delete the Holding """

    def __init__(self):
        super().__init__()


class Holding:
    """ Contains details about the stocks owned by the user.
        A holding is an executed buy operation."""
    stock: Stock
    quantity: int
    quantity_compromised: int
    daily_variation: float
    last_price: float
    average_price: float

    def __init__(self):
        """ Create a new Holding """
        self.stock = Stock()
        self.daily_variation = self.stock.get_current_price(self)
        self.last_price = 150
        self.average_price = 140
        self.quantity = 0
        self.quantity_compromised = 0

    def to_string(self):
        """ returns a nice and handy text representation of the object """
        return "{0} {1}\t{2}\t{3}\t{4}\t{5}".format(self.stock.ticker.ljust(6, ' '),
                                                    self.stock.company.ljust(15, ' '),
                                                    str(self.quantity).ljust(8, ' '),
                                                    (str(self.daily_variation) + " %").ljust(8, " "),
                                                    ("$ " + str(self.last_price)).ljust(8, " "),
                                                    ("$ " + str(self.average_price)).ljust(14, " "))


class Broker:
    """ Represents an intermediary that executes buy and sell orders, among other tasks. """
    name = ""
    commission: float

    def __init__(self):
        """ Create a new Broker """
        self.name = "Fast Broker"
        self.commission = 0.005

    @staticmethod
    def execute(self, stock: Stock, operation: Operation):
        """ Handles a generic operation to buy or sell """
        # TODO: resolve if has to buy or sell using the Operation object
        # this is half baked.
        pass

    @staticmethod
    def buy(self, stock: Stock, quantity: int, price: float):
        """ buy stocks """
        # Dummy API invocation using HTTPS.
        pass

    @staticmethod
    def sell(self, holding: Holding, quantity: int, price: float):
        """ sell stocks """
        # Dummy API invocation using HTTPS.
        pass


data_file_url = "data/data.txt"


class Portfolio:
    """ Helps to admin the stocks holdings owned by the user """
    stocks_owned: List[Holding]
    cash: float

    def __init__(self):
        """ Create a new Portfolio """
        self.stocks_owned = list()
        self.read_json_data_from_file()

    def show(self) -> str:
        result = ""
        # TODO: Remember to show how much free cash is there in the account.
        if len(self.stocks_owned) == 0:
            return "Portfolio Empty."

        # print headers first
        print(self.print_header(self))

        for holding in self.stocks_owned:
            result += holding.to_string() + Constants.crlf

        return result

    def write_json_data_to_file(self):
        import json

        data = {}
        data['holdings'] = []
        data['holdings'].append({
            'market': 'NASDAQ',
            'ticker': 'GOOG',
            'company': 'Google, Inc.',
            'last_price': '1359',
            'avg_price': '1359',
            'quantity': '30',
            'quantity_compromised': '0'
        })
        data['holdings'].append({
            'market': 'NASDAQ',
            'ticker': 'NFLX',
            'company': 'Netflix',
            'last_price': '301',
            'avg_price': '262',
            'quantity': '20',
            'quantity_compromised': '0'
        })
        data['holdings'].append({
            'market': 'NASDAQ',
            'ticker': 'FB',
            'company': 'Facebook, Inc.',
            'last_price': '198.8',
            'avg_price': '210.5',
            'quantity': '10',
            'quantity_compromised': '0'
        })

        with open(data_file_url, 'w') as outfile:
            json.dump(data, outfile, indent=4)

    def read_json_data_from_file(self):
        import json

        with open(data_file_url) as json_file:
            data = json.load(json_file)
            for p in data['holdings']:
                print('Market: ' + p['market'])
                print('Ticker: ' + p['ticker'])
                print('Company: ' + p['company'])
                print('')

                # TODO: instead of print, bind to our objects
                holding = Holding()
                holding.stock.ticker = p['ticker']
                holding.stock.market = p['market']
                holding.stock.company = p['company']
                holding.average_price = p['avg_price']
                holding.last_price = p['last_price']
                holding.quantity = p['quantity']
                holding.quantity_compromised = p['quantity_compromised']
                self.stocks_owned.append(holding)

    @staticmethod
    def print_header(self):
        """ utility function, used to show headers. """
        return "{0} {1}\t{2}\t{3}\t{4}\t{5}".format("ticker".ljust(6, ' '),
                                                    "company".ljust(15, ' '),
                                                    "quantity".ljust(8, ' '),
                                                    "variation".ljust(8, ' '),
                                                    "last price".ljust(8, ' '),
                                                    "avg buy price".ljust(14, ' '))

    @staticmethod
    def test_queue() -> str:
        print("Testing Queue")
        queue = Queue()
        queue.enqueue('1')
        queue.enqueue('2')
        queue.enqueue('3')
        queue.enqueue('4')
        print(queue.dequeue())  # 4
        print(queue.dequeue())  # 3
        print(queue.dequeue())  # 2
        print(queue.dequeue())  # 1
        return ""


class Sets:
    """ illustrate the intersection of two lists, simple way """

    @staticmethod
    def intersection(lst1, lst2):
        """ get intersection of two lists """
        lst3 = [value for value in lst1 if value in lst2]
        return lst3

    @staticmethod
    def diff(li1, li2):
        """ get difference of two lists """
        return list(set(li1) - set(li2))


class Constants:
    number_type_name = "number"
    datetime_type_name = "datetimeV2.datetime"
    date_type_name = "datetimeV2.date"
    currency_type_name = 'currency'
    crlf = '\r\n'
    separator = "----------------------------------"
    double_separator = "-------------------------------------------------------------------------------"
    max_decimals = 2
    max_variation = 10
    min_variation = -10
    tax = 0.01


class Queue:
    """
    Thread-safe, memory-efficient, maximally-sized queue supporting queueing and
    dequeueing in worst-case O(1) time.
    """

    def __init__(self, max_size=10):
        """
        Initialize this queue to the empty queue.

        Parameters
        ----------
        max_size : int
            Maximum number of items contained in this queue. Defaults to 10.
        """
        self._queue = deque(maxlen=max_size)

    def enqueue(self, item):
        """
        Queues the passed item (i.e., pushes this item onto the tail of this
        queue).

        If this queue is already full, the item at the head of this queue
        is silently removed from this queue *before* the passed item is
        queued.
        """

        self._queue.append(item)

    def dequeue(self):
        """
        Dequeues (i.e., removes) the item at the head of this queue *and*
        returns this item.

        Raises
        ----------
        IndexError
            If this queue is empty.
        """
        return self._queue.pop()
