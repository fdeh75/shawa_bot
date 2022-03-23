import logging

from telegram import LabeledPrice, ShippingOption, Update, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardMarkup, \
    InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PreCheckoutQueryHandler,
    ShippingQueryHandler,
    CallbackContext,
    CallbackQueryHandler)
import json
from config import API_TOKEN, PAYMENT_TOKEN, CREATE_ORDER, MANAGERS_IDS

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start_callback(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""

    keyboard = [[KeyboardButton(CREATE_ORDER)]]
    message = "**Добро пожаловать!** \n\n " \
              "Для заказа товаров нажмите на кнопку расположенную внизу и сделуйте инструкциям"

    reply_markup = ReplyKeyboardMarkup(keyboard)

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


def send_with_shipping_invoice(products_count: int, chat_id: int, context: CallbackContext) -> None:
    title = "Ваш заказ"
    # select a payload just for you to recognize its the donation from your bot
    payload = json.dumps({
        "type": 'shawa_bot_order',
        "itemsCount": int(products_count)
    })
    # payload = "Custom-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    provider_token = PAYMENT_TOKEN
    currency = "RUB"
    # price in dollars
    price = 200 * int(products_count)

    description = f"Шаверма: x{products_count}   {price} {currency}"
    # price * 100 so as to include 2 decimal points
    # check https://core.telegram.org/bots/payments#supported-currencies for more details
    prices = [LabeledPrice(description, price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        provider_token,
        currency,
        prices,
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=True,
    )


def start_without_shipping_callback(update: Update, context: CallbackContext) -> None:
    """Sends an invoice without shipping-payment."""
    chat_id = update.message.chat_id
    title = "Payment Example"
    description = "Payment Example using python-telegram-bot"
    # select a payload just for you to recognize its the donation from your bot
    payload = "Custom-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    provider_token = PAYMENT_TOKEN
    currency = "RUB"
    # price in rubles
    price = 200
    # price * 100 so as to include 2 decimal points
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )


def shipping_callback(update: Update, context: CallbackContext) -> None:
    """Answers the ShippingQuery with ShippingOptions"""
    query = update.shipping_query
    # check the payload, is this from your bot?

    invoice_type = None
    try:
        invoice_type = json.loads(query.invoice_payload)['type']
    except Exception as e:
        print(f"shipping_callback invoice_type detect err: {e}")

    if invoice_type != 'shawa_bot_order':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
        return

    # First option has a single LabeledPrice
    options = [
        ShippingOption('1', 'Доставка', [LabeledPrice('Доставка', 50000)]),
        ShippingOption('2', 'Без доставки', [LabeledPrice('Без доставки', 0)])
    ]
    query.answer(ok=True, shipping_options=options)


# after (optional) shipping, it's the pre-checkout
def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    invoice_type = None
    try:
        invoice_type = json.loads(query.invoice_payload)['type']
    except Exception as e:
        print(f"shipping_callback invoice_type detect err: {e}")

    if invoice_type != 'shawa_bot_order':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


# finally, after contacting the payment provider...
def successful_payment_callback(update: Update, context: CallbackContext) -> None:
    """Confirms the successful payment."""
    # do something after successfully receiving payment?
    update.message.reply_text("Спасибо за покупку, заходите к нам еще!")

    need_shipping = update.message.effective_attachment.shipping_option_id == '1'

    shipping_address = ""

    if need_shipping:
        shipping_address_obj = update.message.effective_attachment.order_info.shipping_address
        shipping_address_data = f"""
Страна: {shipping_address_obj.country_code}
Город: {shipping_address_obj.city}
Post code: {shipping_address_obj.post_code},
Улица 1: {shipping_address_obj.street_line1},
Улица 2: {shipping_address_obj.street_line2}
"""
        shipping_address = f"\nАдрес доставки: {shipping_address_data}"

    items_count = "Не определено в следсвии ошибки, свяжитесь с пользователем для уточнения"
    try:
        items_count = json.loads(update.message.effective_attachment.invoice_payload)['itemsCount']
    except Exception as e:
        print("get itemsCount error!", e)

    order_info = \
        f"""Новый заказ! 
Колличетсво шаверм: {items_count}
Тип доставки: { 'Доставка' if need_shipping else 'Самовывоз'}
Клиент: {update.message.effective_attachment.order_info.name}
Клиент telegram: @{update.message.chat.username} 
Клиент email: {update.message.effective_attachment.order_info.email}
Клиент телефон: +{update.message.effective_attachment.order_info.phone_number}{shipping_address}
"""

    for manager_id in MANAGERS_IDS:
        context.bot.send_message(manager_id, order_info)


def get_products_list(update: Update, context: CallbackContext) -> None:

    keyboard = [
        [
            InlineKeyboardButton("Одна шава", callback_data=1),
            InlineKeyboardButton("Две шавы", callback_data=2),
            InlineKeyboardButton("Три шавы", callback_data=3)
        ],
        [
            InlineKeyboardButton("Четыре шава", callback_data=4),
            InlineKeyboardButton("Пять шав", callback_data=5),
            InlineKeyboardButton("Шесть шав", callback_data=6)
        ]
    ]
    message = "Выберете то что Вам нужно из списка"

    reply_markup = InlineKeyboardMarkup(keyboard)

    # using one_time_keyboard to hide the keyboard
    update.effective_message.reply_text(
        message, reply_markup=reply_markup
    )


def button(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    query.answer()
    query.delete_message()

    send_with_shipping_invoice(products_count=query.data, chat_id=update.effective_message.chat_id, context=context)


def any_message(update: Update, context: CallbackContext) -> None:
    print(1234)


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # simple start function
    dispatcher.add_handler(CommandHandler("start", start_callback))

    # Add command handler to start the payment invoice
    # dispatcher.add_handler(CommandHandler("shipping", start_with_shipping_callback))
    dispatcher.add_handler(CommandHandler("noshipping", start_without_shipping_callback))

    # Optional handler if your product requires shipping
    dispatcher.add_handler(ShippingQueryHandler(shipping_callback))

    # Pre-checkout handler to final check
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    # Success! Notify your user!
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    dispatcher.add_handler(MessageHandler(Filters.text(CREATE_ORDER), get_products_list))
    dispatcher.add_handler(MessageHandler(Filters.text("*"), any_message))
    dispatcher.add_handler(MessageHandler(Filters.contact, any_message))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
