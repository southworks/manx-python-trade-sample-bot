# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import (
    TextPrompt,
    NumberPrompt,
    ChoicePrompt,
    ConfirmPrompt,
    PromptOptions,
    PromptValidatorContext,
)
from botbuilder.dialogs.choices import Choice
from botbuilder.core import MessageFactory, UserState

import json
from typing import List
import recognizers_suite as Recognizers
from recognizers_suite import Culture, ModelResult

# import recognizers_suite as Recognizers
# from recognizers_suite import Culture, ModelResult

from datetime import datetime

from collections import deque

import random

from data_models import UserProfile

import recognizers_suite

DEFAULT_CULTURE = Culture.English


class UserProfileDialog(ComponentDialog):
    def __init__(self, user_state: UserState):
        super(UserProfileDialog, self).__init__(UserProfileDialog.__name__)

        self.user_profile_accessor = user_state.create_property("UserProfile")

        self.add_dialog(
            WaterfallDialog(
                WaterfallDialog.__name__,
                [
                    self.options_step,
                    self.portfolio_show_step,
                    self.next_step,
                    self.check_is_info_ok
                ],
            )
        )
        self.add_dialog(TextPrompt(TextPrompt.__name__))
        self.add_dialog(TextPrompt("text_prompt_input"))

        self.add_dialog(
            NumberPrompt(NumberPrompt.__name__, UserProfileDialog.age_prompt_validator)
        )
        self.add_dialog(ChoicePrompt(ChoicePrompt.__name__))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))

        self.add_dialog(ChoicePrompt("options_step"))

        self.initial_dialog_id = WaterfallDialog.__name__

    async def options_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """ working so far, this is a Choice select """
        return await step_context.prompt(
            ChoicePrompt.__name__,
            PromptOptions(
                prompt=MessageFactory.text("Welcome! What can I help you with?"),
                choices=[Choice("Portfolio"), Choice("Trade"), Choice("Help")],
            ),
        )

    @staticmethod
    async def age_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        """ This condition is our validation rule. You can also change the value at this point. """
        return (
            prompt_context.recognized.succeeded
            and 0 < prompt_context.recognized.value < 150
        )

    async def portfolio_show_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """ Step description:  """
        step_context.values["option_selected"] = step_context.result.value

        step_context.values["input"] = step_context.result

        if step_context.result:
            #  Get the current profile object from user state.  Changes to it
            # will saved during Bot.on_turn.
            user_profile = await self.user_profile_accessor.get(
                step_context.context, UserProfile
            )

            user_profile.transport = step_context.values["option_selected"]

        if step_context.result.value == 'Portfolio':
            await step_context.context.send_activity(
                MessageFactory.text(f"Very well, this is your portfolio.")
            )
            await step_context.context.send_activity(
                MessageFactory.text("We could and should use a Card here.")
            )

            portfolio = Portfolio()

            await step_context.context.send_activity(
                MessageFactory.text(portfolio.show())
            )

            # Here, the conversation could continue, or be terminated and reset
            return await step_context.end_dialog()

        elif step_context.result.value == 'Trade':
            await step_context.context.send_activity(
                MessageFactory.text(f"Ok, you want to trade.")
            )
            return await step_context.prompt(
                "text_prompt_input",
                PromptOptions(prompt=MessageFactory.text("What do you want to buy or sell?")),
            )
            # Here we wait for a TextPrompt input, that should contain the user intent,
            # like:
            # Buy 25 MSFT for $ 120

            # here, we can also have a Choice Prompt based on our current holdings.
            # that way, the user intent, is getting narrowed in a interactive fashion.

        elif step_context.result.value == 'Help':
            await step_context.context.send_activity(
                MessageFactory.text(f"Some day, when the sun is bright in the sky and all the backlog tasks are completed, I will be able to give you help. Sorry.")
            )
            return await step_context.end_dialog()

    async def next_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """ Using Recognizers-Text to detect user intention """
        step_context.values["input"] = step_context.result
        user_input = step_context.values["input"]

        await step_context.context.send_activity(
            MessageFactory.text(f"[In this step, we will use Recognizers-Text to learn the user intention.]")
        )
        # -------------------------------------------------------------
        # TODO: Integrate here Recognizers-Text
        results = parse_all(user_input, DEFAULT_CULTURE)
        # Flatten results
        results = [item for sublist in results for item in sublist]

        # ------------
        # parse results to find the data we need:
        has_time_stamp = False
        has_price = False
        has_quantity = False
        amount = None

        # temporary lists
        list_number = []
        list_currency = []
        list_datetime = []
        value_key = "value"

        for i in results:
            # in each pass, according to type_name, append to a list, or several.
            type_name = i.type_name
            if type_name == Constants.currency_type_name:
                has_price = True
                list_currency.append(i.resolution.get(value_key))
            if type_name == Constants.datetime_type_name or type_name == Constants.date_type_name:
                has_time_stamp = True
                list_datetime.append(i.resolution.get("values", "")[0][value_key])
            if type_name == Constants.number_type_name:
                if i.resolution.get(value_key):
                    has_quantity = True
                    value = i.resolution.get(value_key)
                else:
                    value = i.text
                    has_quantity = False

                list_number.append(value)

        # this contains the whole collection of stocks of the user.
        portfolio = Portfolio()

        # this represents a position taken with an investment instrument.
        # usually, there are many open at the same time.
        holding = Holding()

        # represents the intermediary broker
        broker = Broker()

        # for current operation (buy, sell)
        operation = Operation()

        operation.buy = True if ('buy' in user_input or 'Buy' in user_input) else False
        operation.sell = True if ('sell' in user_input or 'Sell' in user_input) else False

        if operation.buy:
            operation = BuyOperation()
            operation.buy = True
            operation.sell = False
            operation.type = 'buy'

        if operation.sell:
            operation = SellOperation()
            operation.buy = False
            operation.sell = True
            operation.type = 'sell'

        # TODO: we should have a dict or similar with [ticker, company_name]
        # refactor this for other companies
        holding.stock.ticker = 'MSFT' if (
                'MSFT' in user_input.upper() or 'microsoft' in user_input.lower()) else 'x'

        if holding.stock.ticker == 'MSFT':
            holding.stock.company = "Microsoft"

        if has_time_stamp:
            operation.time_stamp = list_datetime[0]

        if len(Sets.intersection(list_currency, list_number)) == 1:
            operation.price = Sets.intersection(list_currency, list_number)[0]
            holding.quantity = Sets.diff(list_number, list_currency)[0]

        if has_quantity and has_price:
            print("Quantity: " + str(holding.quantity))
            amount = int(holding.quantity) * float(operation.price)

        print("Stock: " + holding.to_string())
        print("Price: $ " + operation.price)

        if has_time_stamp:
            print("TimeStamp: " + str(operation.time_stamp))

        if has_quantity and amount:
            print(Constants.separator)
            print("OPERATION DETAILS")
            print(Constants.separator)
            print("Operation type: " + operation.type)
            print("Amount: $ " + str(amount))
            commission = round(amount * broker.commission, Constants.max_decimals)
            # tax, over the commission is 0.01 (10%)
            tax = round(commission * Constants.tax, Constants.max_decimals)
            print("Commission: $ " + str(commission))
            print("TAX: $ " + str(tax))
            print(Constants.separator)
            print("Total: $ " + str(amount + commission + tax))
            print(Constants.separator)

        str_quantity = str(holding.quantity)
        str_price = "$ " + str(operation.price)
        str_time_stamp = " on " + str(operation.time_stamp) if has_time_stamp else ""

        # populate Portfolio object
        portfolio.stocks_owned.append(holding)
        # -------------------------------------------------------------
        # Finally, we show the Portfolio now
        # await step_context.context.send_activity(
        #     MessageFactory.text("PORTFOLIO DISTRIBUTION")
        # )

        # await step_context.context.send_activity(
        #     MessageFactory.text(portfolio.show())
        # )

        operation_details = ""
        if has_quantity and amount:
            commission = round(amount * broker.commission, Constants.max_decimals)
            tax = round(commission * Constants.tax, Constants.max_decimals)

            operation_details += Constants.separator + "\n"
            operation_details += "OPERATION DETAILS" + "\n"
            operation_details += Constants.separator + "\n"
            operation_details += "Operation type: " + operation.type + "\n"
            operation_details += "Amount: $ " + str(amount) + "\n"
            operation_details += "Commission: $ " + str(commission) + "\n"
            operation_details += "TAX: $ " + str(tax) + "\n"
            operation_details += Constants.separator + "\n"
            operation_details += "Total: $ " + str(amount + commission + tax) + "\n"
            operation_details += Constants.separator + "\n"

        await step_context.context.send_activity(
            MessageFactory.text(operation_details)
        )

        # TODO: Here, we can show how much profit comes from the sale operation.
        query = "Do you wish to " + operation.type + " " + str_quantity + " " + holding.stock.ticker + " stocks at " + str_price + str_time_stamp + "?"
        return await step_context.prompt(
            ConfirmPrompt.__name__,
            PromptOptions(
                prompt=MessageFactory.text(query)
            ),
        )

        # if we don't ask for confirmation, we terminate it:
        # return await step_context.end_dialog()

    async def check_is_info_ok(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        query = step_context.values["input"]

        if step_context.result:
            # User said "yes" so we can execute the operation.
            await step_context.context.send_activity(
                MessageFactory.text(f"Executing Operation.")
            )

            await step_context.context.send_activity(
                MessageFactory.text(f"[Lie] Operation Executed. This is the details of the operation:")
            )
            await step_context.context.send_activity(
                MessageFactory.text(f"[CARD WITH TRANSACTION DETAILS]")
            )

            return await step_context.end_dialog()

        # User said "no"
        # so we will have to terminate for now
        # also we could reuse some of the previous steps.
        await step_context.context.send_activity(
            MessageFactory.text(f"I'm sorry I did not understand your order: '{query}'")
        )
        await step_context.context.send_activity(
            MessageFactory.text(f"I am still learning, you know?")
        )

        return await step_context.end_dialog()


def parse_all(user_input: str, culture: str) -> List[List[ModelResult]]:
    return [
        # Number recognizer - This function will find any number from the input
        # E.g "I have two apples" will return "2".
        Recognizers.recognize_number(user_input, culture),

        # Ordinal number recognizer - This function will find any ordinal number
        # E.g "eleventh" will return "11".
        Recognizers.recognize_ordinal(user_input, culture),

        # Percentage recognizer - This function will find any number presented as percentage
        # E.g "one hundred percents" will return "100%"
        Recognizers.recognize_percentage(user_input, culture),

        # Age recognizer - This function will find any age number presented
        # E.g "After ninety five years of age, perspectives change" will return
        # "95 Year"
        Recognizers.recognize_age(user_input, culture),

        # Currency recognizer - This function will find any currency presented
        # E.g "Interest expense in the 1988 third quarter was $ 75.3 million"
        # will return "75300000 Dollar"
        Recognizers.recognize_currency(user_input, culture),

        # Dimension recognizer - This function will find any dimension presented E.g "The six-mile trip to my airport
        # hotel that had taken 20 minutes earlier in the day took more than
        # three hours." will return "6 Mile"
        Recognizers.recognize_dimension(user_input, culture),

        # Temperature recognizer - This function will find any temperature presented
        # E.g "Set the temperature to 30 degrees celsius" will return "30 C"
        Recognizers.recognize_temperature(user_input, culture),

        # DateTime recognizer - This function will find any Date even if its write in colloquial language -
        # E.g "I'll go back 8pm today" will return "2017-10-04 20:00:00"
        Recognizers.recognize_datetime(user_input, culture),

        # PhoneNumber recognizer will find any phone number presented
        # E.g "My phone number is ( 19 ) 38294427."
        Recognizers.recognize_phone_number(user_input, culture),

        # Email recognizer will find any phone number presented
        # E.g "Please write to me at Dave@abc.com for more information on task
        # #A1"
        Recognizers.recognize_email(user_input, culture),
    ]



class Market:
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


class Portfolio:
    """ Helps to admin the stocks holdings owned by the user """
    stocks_owned: List[Holding]
    cash: float

    def __init__(self):
        """ Create a new Portfolio """
        self.stocks_owned = list()
        # TODO: Create a parametric constructor, for fast population.

        g: Holding = Holding()
        g.stock.market = Market.NASDAQ[0]
        g.stock.ticker = "GOOG"
        g.stock.company = "Google, Inc."
        g.average_price = 1210
        g.last_price = 1359
        g.quantity = 30
        g.quantity_compromised = 0
        self.stocks_owned.append(g)

        g: Holding = Holding()
        g.stock.ticker = "NFLX"
        g.stock.market = Market.NASDAQ[0]
        g.stock.company = "Netflix"
        g.average_price = 262
        g.last_price = 301
        g.quantity = 20
        g.quantity_compromised = 0
        self.stocks_owned.append(g)

        g: Holding = Holding()
        g.stock.ticker = "FB"
        g.stock.market = Market.NASDAQ[0]
        g.stock.company = "Facebook, Inc."
        g.average_price = 210.5
        g.last_price = 198.80
        g.quantity = 10
        g.quantity_compromised = 0
        self.stocks_owned.append(g)

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
        lst3 = [value for value in lst1 if value in lst2]
        return lst3

    """ get difference of two lists """

    @staticmethod
    def diff(li1, li2):
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

