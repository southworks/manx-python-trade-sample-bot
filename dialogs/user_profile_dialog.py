# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import matplotlib.pyplot as plt

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


from data_models import UserProfile

import recognizers_suite

from botbuilder.core import CardFactory, MessageFactory
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
)
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.schema import (
    ActionTypes,
    Attachment,
    AnimationCard,
    AudioCard,
    HeroCard,
    VideoCard,
    ReceiptCard,
    SigninCard,
    ThumbnailCard,
    MediaUrl,
    CardAction,
    CardImage,
    ThumbnailUrl,
    Fact,
    ReceiptItem,
)

from data_models.trade_assistant import Portfolio, Constants, Operation, Broker, Holding, BuyOperation, SellOperation, \
    Sets, OperationStatus

from helpers.activity_helper import create_activity_reply

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

        self.portfolio = Portfolio()
        self.broker = Broker()
        self.operation = Operation()

    portfolio: Portfolio
    broker: Broker
    operation: Operation

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

            await step_context.context.send_activity(
                MessageFactory.text(self.portfolio.show())
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

        # TODO: remove this notification, it is for demo purposes only.
        await step_context.context.send_activity(
            MessageFactory.text(f"[In this step, we will use Recognizers-Text to learn the user intention.]")
        )
        # -------------------------------------------------------------
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
        # in the init method, it should populate the holdings using the data text file
        self.portfolio = Portfolio()

        # test read file: ok - disabled, because the init method of Portfolio() already instantiates the collection
        # self.portfolio.read_json_data_from_file()

        # this represents a position taken with an investment instrument.
        # usually, there are many open at the same time.
        holding = Holding()

        # represents the intermediary broker
        self.broker = Broker()

        # for current operation (buy, sell)
        self.operation = Operation()

        self.operation.buy = True if ('buy' in user_input or 'Buy' in user_input) else False
        self.operation.sell = True if ('sell' in user_input or 'Sell' in user_input) else False

        if self.operation.buy:
            self.operation = BuyOperation()
            self.operation.buy = True
            self.operation.sell = False
            self.operation.type = 'buy'

        if self.operation.sell:
            self.operation = SellOperation()
            self.operation.buy = False
            self.operation.sell = True
            self.operation.type = 'sell'

        # TODO: we should have a dict or similar with [ticker, company_name]
        # refactor this for other companies
        holding.stock.ticker = 'MSFT' if (
                'MSFT' in user_input.upper() or 'microsoft' in user_input.lower()) else 'x'

        if holding.stock.ticker == 'MSFT':
            holding.stock.company = "Microsoft"

        if has_time_stamp:
            self.operation.time_stamp = list_datetime[0]

        if len(Sets.intersection(list_currency, list_number)) == 1:
            self.operation.price = Sets.intersection(list_currency, list_number)[0]
            holding.quantity = Sets.diff(list_number, list_currency)[0]

        if has_quantity and has_price:
            print("Quantity: " + str(holding.quantity))
            amount = int(holding.quantity) * float(self.operation.price)
            self.operation.amount = round(amount, Constants.max_decimals)

        print("Stock: " + holding.to_string())
        print("Price: $ " + str(self.operation.price))

        if has_time_stamp:
            print("TimeStamp: " + str(self.operation.time_stamp))

        if has_quantity and amount:
            print(Constants.separator)
            print("OPERATION DETAILS")
            print(Constants.separator)
            print("Operation type: " + self.operation.type)
            print("Amount: $ " + str(amount))
            self.operation.commission = round(amount * self.broker.commission, Constants.max_decimals)
            # tax, over the commission is 0.01 (10%)
            self.operation.tax = round(self.operation.commission * Constants.tax, Constants.max_decimals)
            print("Commission: $ " + str(self.operation.commission))
            print("TAX: $ " + str(self.operation.tax))
            print(Constants.separator)
            print("Total: $ " + str(amount + self.operation.commission + self.operation.tax))
            print(Constants.separator)
            self.operation.quantity = holding.quantity
            self.operation.stock.ticker = holding.stock.ticker
            self.operation.stock.company = holding.stock.company
            self.operation.stock.market = holding.stock.market

        str_quantity = str(holding.quantity)
        str_price = "$ " + str(self.operation.price)
        str_time_stamp = " on " + str(self.operation.time_stamp) if has_time_stamp else ""

        # TODO: Check if the ticker is in use.
        find_result = any(elem.stock.ticker == holding.stock.ticker for elem in self.portfolio.stocks_owned)

        if find_result:
            updated_holding = next((i for i in self.portfolio.stocks_owned if i.stock.ticker == holding.stock.ticker), None)
            a = int(updated_holding.quantity)
            b = int(holding.quantity)
            # TODO: Check if is a buy or sell, the arithmetic logic
            if self.operation.type == 'buy':
                updated_holding.quantity = str(a + b)
                # cash should be decreased by the total cost of the operation
            elif self.operation.type == 'sell':
                # in fact, this should alter the compromised quantity, until the order is executed. Its ok for now.
                updated_holding.quantity = str(a - b)
                # also, the cash should be incremented when selling
                # self.portfolio.cash =
        else:
            self.portfolio.stocks_owned.append(holding)
        # -------------------------------------------------------------

        # TODO: Test write the portfolio with new values
        self.portfolio.write_json_data_to_file()

        operation_details = ""
        if has_quantity and amount:
            commission = round(amount * self.broker.commission, Constants.max_decimals)
            tax = round(commission * Constants.tax, Constants.max_decimals)

            operation_details += Constants.separator + "\n"
            operation_details += "OPERATION DETAILS" + "\n"
            operation_details += Constants.separator + "\n"
            operation_details += "Operation type: " + self.operation.type + "\n"
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
        query = "Do you wish to " + self.operation.type + " " + str_quantity + " " + holding.stock.ticker + " stocks at " + str_price + str_time_stamp + "?"
        return await step_context.prompt(
            ConfirmPrompt.__name__,
            PromptOptions(
                prompt=MessageFactory.text(query)
            ),
        )

        # if we don't ask for confirmation, we terminate it:
        # return await step_context.end_dialog()

    @staticmethod
    def create_receipt_card(self, operation: Operation) -> Attachment:
        card = ReceiptCard(
            title="Operation: " + operation.type,
            facts=[
                Fact(key="Order #", value="123456"),
                Fact(key="Ticker", value=operation.stock.ticker),
            ],
            items=[
                ReceiptItem(
                    title=operation.type + " order",
                    subtitle=operation.stock.company,
                    price="$ " + str(operation.price),
                    quantity=str(operation.quantity),
                ),
                ReceiptItem(
                    title="Commission",
                    price="$ " + str(operation.commission),
                    quantity="1",
                    image=CardImage(
                        url="https://github.com/amido/azure-vector-icons/raw/master/"
                        "renders/cloud-service.png"
                    ),
                ),
            ],
            tax="$ " + str(operation.tax),
            total="$ " + str(operation.amount + operation.commission + operation.tax),
            buttons=[
                CardAction(
                    type=ActionTypes.open_url,
                    title="More Information",
                    value="https://github.com/southworks/manx-python-trade-sample-bot/",
                )
            ],
        )
        return CardFactory.receipt_card(card)

    async def check_is_info_ok(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """ This step ... """
        query = step_context.values["input"]

        if step_context.result:
            # User said "yes" so we can execute the operation.
            await step_context.context.send_activity(
                MessageFactory.text(f"Executing Operation.")
            )

            return_from_broker = ""
            text_return_from_broker = ""

            # TODO: Here we have to at least simulate the API call to the Broker
            if self.operation.type == 'buy':
                # TODO: Define the interface of the Broker API: buy
                return_from_broker = self.broker.buy(self, self.operation)

                if return_from_broker.status == OperationStatus.Success:
                    text_return_from_broker = "Operation OK!"

                    # TODO: Verify that the operation object has ALL the info needed.
                    card = self.create_receipt_card(self, self.operation)

                    response = create_activity_reply(
                        step_context.context.activity, "", "", [card]
                    )
                    await step_context.context.send_activity(response)

            elif self.operation.type == 'sell':
                a = 2
                # TODO: Define the interface of the Broker API: sell
                # self.broker.sell()

            await step_context.context.send_activity(
                MessageFactory.text(f"[Semi-Lie] Operation Executed. This is the details of the operation:")
            )
            await step_context.context.send_activity(
                MessageFactory.text(text_return_from_broker)
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

