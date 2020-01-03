# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, ConversationState, TurnContext, UserState, MessageFactory
from botbuilder.dialogs import Dialog
from botbuilder.schema import ChannelAccount
from helpers.dialog_helper import DialogHelper

import os
import urllib.parse
import urllib.request
import base64
import json

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext, CardFactory
from botbuilder.schema import (
    ChannelAccount,
    HeroCard,
    CardAction,
    ActivityTypes,
    Attachment,
    AttachmentData,
    Activity,
    ActionTypes,
)


class DialogBot(ActivityHandler):
    """
    This Bot implementation can run any type of Dialog. The use of type parameterization is to allows multiple
    different bots to be run at different endpoints within the same project. This can be achieved by defining distinct
    Controller types each with dependency on distinct Bot types. The ConversationState is used by the Dialog system. The
    UserState isn't, however, it might have been used in a Dialog implementation, and the requirement is that all
    BotState objects are saved at the end of a turn.
    """

    def __init__(
        self,
        conversation_state: ConversationState,
        user_state: UserState,
        dialog: Dialog,
    ):
        if conversation_state is None:
            raise TypeError(
                "[DialogBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[DialogBot]: Missing parameter. user_state is required but None was given"
            )
        if dialog is None:
            raise Exception("[DialogBot]: Missing parameter. dialog is required")

        self.conversation_state = conversation_state
        self.user_state = user_state
        self.dialog = dialog

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)

        # Save any state changes that might have ocurred during the turn.
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        if (
            turn_context.activity.attachments
            and len(turn_context.activity.attachments) > 0
        ):
            await self._handle_outgoing_attachment(turn_context)
        else:
            await DialogHelper.run_dialog(
                self.dialog,
                turn_context,
                self.conversation_state.create_property("DialogState"),
            )

    async def on_members_added_activity(
        self, members_added: ChannelAccount, turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                reply = MessageFactory.text(
                    "Welcome to TradeBot. "
                    + "This bot will try to show you the integration between BotBuilder and Recognizers-Text. "
                    + "Please type anything to get started."
                )
                await turn_context.send_activity(reply)

    # taken from AttachmentBot
    async def _handle_outgoing_attachment(self, turn_context: TurnContext):
        reply = Activity(type=ActivityTypes.message)
        # reply.text = "This is an inline attachment."
        reply.attachments = [self.get_inline_attachment()]

        await turn_context.send_activity(reply)

    def get_inline_attachment(self) -> Attachment:
        """
        Creates an inline attachment sent from the bot to the user using a base64 string.
        Using a base64 string to send an attachment will not work on all channels.
        Additionally, some channels will only allow certain file types to be sent this way.
        For example a .png file may work but a .pdf file may not on some channels.
        Please consult the channel documentation for specifics.
        :return: Attachment
        """
        file_path = os.path.join(os.getcwd(), "assets/architecture-resize.png")
        with open(file_path, "rb") as in_file:
            base64_image = base64.b64encode(in_file.read()).decode()

        return Attachment(
            name="architecture-resize.png",
            content_type="image/png",
            content_url=f"data:image/png;base64,{base64_image}",
        )
