import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiocryptopay import AioCryptoPay, Networks
import config2 as config
import random

from config2 import*

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

cryptopay = AioCryptoPay(config.CRYPTO_TOKEN, network=Networks.MAIN_NET)

def get_footer_links():
    return "\n\n<b><a href='t.me/c/3816722057/9'>Правила</a></b> | <b><a href='t.me/+-KpLp8Bvny43YzYy'>Новостной</a></b> | <b><a href='https://t.me/Spind_AD'>Поддержка</a></b> | <b><a href='https://t.me/SpindBet_Crypto_bot'>Бот</a></b>"

# Выплата чеков
async def pay_money(amount, id):
    try:
        check = await cryptopay.create_check(asset='USDT', amount=amount)
        
        keyboard = types.InlineKeyboardMarkup()
        prize = types.InlineKeyboardButton(text="🎁 Забрать выигрыш", url=check.bot_check_url)
        keyboard.add(prize)
        
        await bot.send_message(
            id, 
            f"<b>💸 Выплата:</b>\n\n<blockquote><b>🏆 Вы выиграли: {amount} USDT!</b></blockquote>\n"
            "✨ Удача уже улыбнулась вам! Сможете повторить успех? 💥",
            reply_markup=keyboard
        )
    except Exception as e:
        error_message = (
            f"<b>[⛔] Ошибка при создании выплаты!</b>\n\n"
            f"<b>😓 Не удалось отправить: {amount} USDT.</b>\n\n"
            "💬 Напишите @Spind_AD, и мы решим проблему как можно быстрее!"
        )
        await bot.send_message(id, error_message)
        for admin_id in config.ADMIN_IDS:
            await bot.send_message(
                admin_id, 
                f"<b>🚨 Ошибка при выплате!</b>\n\n"
                f"👤 <b>Пользователь:</b> {id}\n"
                f"💰 <b>Сумма:</b> {amount} USDT\n\n"
                f"⚠️ <b>Ошибка:</b> {e}"
            )
        logging.error(f"Ошибка при создании чека: {str(e)}", exc_info=True)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    make_bet_btn = types.InlineKeyboardButton(
        text="🎯 Сделать ставку",
        url=config.channel_link
    )

    how_to_bet_btn = types.InlineKeyboardButton(
        text="ℹ️ Как сделать ставку",
        callback_data="how_to_bet"
    )

    games_btn = types.InlineKeyboardButton(
        text="🎮 Игры в боте",
        url="https://t.me/SPIND_BET_BOT"  # ← если другой бот — поменяй
    )

    haart_btn = types.InlineKeyboardButton(
        text="Игровой канал",
        url="https://t.me/+v01pNqgHVYs0ZTEy"  # ← если другой бот — поменяй
    )


    keyboard.add(haart_btn)
    keyboard.add(how_to_bet_btn, games_btn)
    keyboard.add(make_bet_btn)

    await message.reply(
        "👋 <b>Добро пожаловать в SpindBet!</b> \n\n"
        "✨ Здесь сбываются мечты и случаются чудеса!\n"
        "🎯 Делайте ставку и испытайте удачу — возможно, именно вы сорвете следующий куш! 🤑",
        reply_markup=keyboard
    )

# Обработчик новых ставок
@dp.channel_post_handler(chat_id=config.PAY_ID)
async def handle_new_bet(message: types.Message):
    try:
        bet_usd = float(message.text.split("($")[1].split(").")[0].replace(',', ''))
        bet_comment = message.text.split("💬 ")[1].lower()
        player_name = message.text.split("отправил(а)")[0].strip()
        user = message.entities[0].user
        player_id = user.id
        
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(text="Сделать ставку", url=config.pinned_link)
        keyboard.add(url_button)

        player_link = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        bet_design = config.BET_TEMPLATE.format(player_link=player_link, bet_usd=bet_usd, bet_comment=bet_comment)
        await bot.send_message(
            chat_id=config.MAIN_ID,
            text=bet_design,
            reply_markup=keyboard
        )
        #await bot.send_photo(chat_id=config.MAIN_ID, photo=open("img/new_bet.png", "rb"), caption=bet_design, reply_markup=keyboard)
        
        # Сразу вызываем handle_game для обработки ставки
        await handle_game(message, bet_usd, bet_comment, player_id)
    except Exception as e:
        await bot.send_message(config.MAIN_ID, f"<b>[⛔] Произошла ошибка при обработке ставки: {str(e)}</b>")

# Обработчик ключевых слов
async def handle_game(message, bet_usd, bet_comment, player_id):
    if bet_comment in ["чет", "нечет", "больше", "меньше"]:
        await handle_dice(message, bet_usd, bet_comment, player_id)
    elif bet_comment.startswith("сектор"):
        await handle_sector(message, bet_usd, bet_comment, player_id)
    elif bet_comment in ["п1", "п2", "ничья"]:
        await handle_duel(message, bet_usd, bet_comment, player_id)
    else:
        await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Неверный формат ставки!\n\n📌 | Для возврата средств обратитесь к администратору.</b></blockquote>")

async def handle_dice(message, bet_usd, bet_comment, player_id):
    dice_value = (await bot.send_dice(chat_id=config.MAIN_ID)).dice.value
    bet_type = bet_comment.lower()

    win = False
    if bet_type in ["больше", "меньше"]:
        win = (bet_type == "больше" and dice_value > 3) or (bet_type == "меньше" and dice_value < 4)
        coefficient = config.GAME_COEFFICIENTS['dice']['high_low']
        result_text = "больше 3" if dice_value > 3 else "меньше 4"
    elif bet_type in ["чет", "четное", "нечет", "нечетное"]:
        win = (bet_type in ["чет", "четное"] and dice_value % 2 == 0) or (bet_type in ["нечет", "нечетное"] and dice_value % 2 != 0)
        coefficient = config.GAME_COEFFICIENTS['dice']['even_odd']
        result_text = "четное" if dice_value % 2 == 0 else "нечетное"

    result_image = config.DICE_RESULT_IMAGES[result_text]
    footer = get_footer_links()

    if win:
        win_amount = bet_usd * coefficient
        try:
            await pay_money(win_amount, player_id)
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(result_image, "rb"),
                caption=f"<b>🎲 Выпало число: {dice_value}</b>\n\n"
                        f"<b>🎉 Удача на вашей стороне! Вы выиграли {win_amount:.2f}$!</b>\n\n"
                        f"<blockquote><b>🚀 Ваш выигрыш уже летит к вам через @SpindBet_Crypto_bot</b></blockquote>{footer}"
            )
        except Exception as e:
            logging.error(f"Ошибка при выплате: {e}")
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(result_image, "rb"),
                caption=f"<b>🎲 Выпало число: {dice_value}</b>\n\n"
                        f"<blockquote><b>🎉 Поздравляем с выигрышем {win_amount:.2f}$! "
                        f"Для получения приза зарегистрируйтесь в боте: @SpindBet_Crypto_bot</b></blockquote>{footer}"
            )
    else:
        await bot.send_photo(
            chat_id=config.MAIN_ID,
            photo=open(result_image, "rb"),
            caption=f"<b>🎲 Выпало число: {dice_value}</b>\n\n"
                    "<blockquote><b>😔 Увы, удача отвернулась... "
                    f"Но не отчаивайтесь, в следующий раз обязательно повезет!</b></blockquote>{footer}"
        )

async def handle_sector(message, bet_usd, bet_comment, player_id):
    dice_value = (await bot.send_dice(chat_id=config.MAIN_ID)).dice.value
    bet_sector = int(bet_comment.split("сектор")[1])
    actual_sector = (dice_value + 1) // 2
    footer = get_footer_links()

    if bet_sector == actual_sector:
        win_amount = bet_usd * config.GAME_COEFFICIENTS['sector']
        try:
            await pay_money(win_amount, player_id)
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(config.SECTOR_IMAGES[actual_sector], "rb"),
                caption=f"<b>🎉 Браво! Вы угадали сектор и выиграли {win_amount}$!</b>\n\n"
                        f"<blockquote><b>🚀 Ваш выигрыш уже отправлен через @SpindBet_Crypto_bot</b></blockquote>{footer}"
            )
        except Exception as e:
            logging.error(f"Ошибка при выплате: {e}")
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(config.SECTOR_IMAGES[actual_sector], "rb"),
                caption=f"<blockquote><b>🎉 Поздравляем с выигрышем {win_amount}$! "
                        f"Для получения приза зарегистрируйтесь в боте: @SpindBet_Crypto_bot.</b></blockquote>{footer}"
            )
    else:
        await bot.send_photo(
            chat_id=config.MAIN_ID,
            photo=open(config.SECTOR_IMAGES[actual_sector], "rb"),
            caption=f"<blockquote><b>😮 Ой, не угадали... "
                    f"Но помните, в азарте главное - удовольствие от игры!</b></blockquote>{footer}"
        )

async def handle_duel(message, bet_usd, bet_comment, player_id):
    dice1 = (await bot.send_dice(chat_id=config.MAIN_ID)).dice.value
    dice2 = (await bot.send_dice(chat_id=config.MAIN_ID)).dice.value
    result = "п1" if dice1 > dice2 else "п2" if dice2 > dice1 else "ничья"
    footer = get_footer_links()
    
    if bet_comment == result:
        win_amount = bet_usd * (config.GAME_COEFFICIENTS['duel']['draw'] if result == "ничья" else config.GAME_COEFFICIENTS['duel']['win'])
        try:
            await pay_money(win_amount, player_id)
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(config.DUEL_IMAGES[result], "rb"),
                caption=f"<b>🎲 Результат дуэли: {dice1}:{dice2}</b>\n\n"
                        f"<b>🎉 Великолепно! Вы предугадали исход дуэли и выиграли {win_amount}$!</b>\n\n"
                        f"<blockquote><b>🚀 Ваш выигрыш уже мчится к вам через @SpindBet_Crypto_bot</b></blockquote>{footer}"
            )
        except Exception as e:
            logging.error(f"Ошибка при выплате: {e}")
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open(config.DUEL_IMAGES[result], "rb"),
                caption=f"<b>🎲 Результат дуэли: {dice1}:{dice2}</b>\n\n"
                        f"<blockquote><b>🎉 Поздравляем с выигрышем {win_amount}$! "
                        f"Для получения приза зарегистрируйтесь в боте: @SpindBet_Crypto_bot.</b></blockquote>{footer}"
            )
    else:
        await bot.send_photo(
            chat_id=config.MAIN_ID,
            photo=open(config.DUEL_IMAGES[result], "rb"),
            caption=f"<b>🎲 Результат дуэли: {dice1}:{dice2}</b>\n\n"
                    "<blockquote><b>😕 Эх, не угадали... "
                    f"Но не расстраивайтесь, в следующий раз фортуна обязательно улыбнется вам!</b></blockquote>{footer}"
        )

# Обработчик инвойсов
@dp.message_handler(commands=['check_payments'])
async def check_payments(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("<b>[⛔️] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>")
        return

    try:
        invoices = await cryptopay.get_invoices(status='paid')
        if not invoices:
            await message.reply("Нет оплаченных инвойсов.")
            return

        for invoice in invoices:
            # Создаем клавиатуру для каждого инвойса
            inline_kb = InlineKeyboardMarkup()
            inline_kb.add(InlineKeyboardButton(f"Подробнее о {invoice.invoice_id}", callback_data=f"invoice_details:{invoice.invoice_id}"))

            response = f"ID: {invoice.invoice_id}, Сумма: {invoice.amount} {invoice.asset}, Статус: {invoice.status}\n"
            await message.reply(response, reply_markup=inline_kb) # Отправляем сообщение с клавиатурой

    except Exception as e:
        await message.reply(f"Произошла ошибка при проверке платежей: {str(e)}")


# Обработчик нажатия на кнопку
@dp.callback_query_handler(lambda c: c.data.startswith('invoice_details:'))
async def process_invoice_details(callback_query: types.CallbackQuery):
    invoice_id = callback_query.data.split(':')[1]
    # Здесь получаем подробную информацию об инвойсе по invoice_id
    # Например:
    invoice_details = await cryptopay.get_invoice(invoice_id)

    # Отправляем пользователю подробную информацию
    await bot.send_message(callback_query.from_user.id, f"Подробная информация об инвойсе {invoice_id}:\n...")
    await callback_query.answer() # Закрываем всплывающее уведомление у кнопки
    
# Создание чеков
@dp.message_handler(commands=['create_invoice'])
async def create_invoice(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>")
        return

    try:
        amount = float(message.text.split()[1])
        invoice = await cryptopay.create_invoice(asset='USDT', amount=amount)
        
        # Проверяем наличие атрибута pay_url
        if hasattr(invoice, 'pay_url'):
            payment_url = invoice.pay_url
        elif hasattr(invoice, 'bot_invoice_url'):
            payment_url = invoice.bot_invoice_url
        else:
            # Если нет ни pay_url, ни bot_invoice_url, используем ID инвойса
            payment_url = f"https://pay.crypt.bot/{invoice.invoice_id}"
        
        keyboard = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_url)
        keyboard.add(pay_button)
        
        await message.reply(
            f"Создан счет для пополнения казны на сумму {amount} USDT:\n"
            f"ID инвойса: {invoice.invoice_id}\n"
            f"Статус: {invoice.status}\n"
            f"Для оплаты нажмите кнопку ниже:", 
            reply_markup=keyboard
        )
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /create_invoice <сумма>")
    except Exception as e:
        logging.error(f"Ошибка при создании инвойса: {str(e)}", exc_info=True)
        await message.reply(f"Произошла ошибка при создании счета: {str(e)}")

# Удаление чеков
@dp.message_handler(commands=['del_checks'])
async def delete_all_invoices(message: types.Message):
    checks = await cryptopay.get_checks(status='active')
    if message.from_user.id in config.ADMIN_IDS:
        await message.reply(checks)
    else:
        await message.reply("<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>")

@dp.message_handler(commands=['delete_check'])
async def delete_check(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        check_id = message.text.split('/delete_check ')[1]
        await cryptopay.delete_check(check_id)
        await message.answer(f'Чек {check_id} удален.')
    except IndexError:
        await message.reply("Используйте: /delete_check <ID чека>")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['list_checks'])
async def list_active_checks(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        checks = await cryptopay.get_checks(status='active')
        if not checks:
            await message.reply("Нет активных чеков.")
            return

        response = "Активные чеки:\n\n"
        for check in checks:
            response += f"ID: {check.check_id}, Сумма: {check.amount} {check.asset}\n"
        
        await message.reply(response)
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['delete_all_checks'])
async def delete_all_checks(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        checks = await cryptopay.get_checks(status='active')
        if not checks:
            await message.reply("Нет активных чеков.")
            return

        deleted_count = 0
        for check in checks:
            await cryptopay.delete_check(check.check_id)
            deleted_count += 1

        await message.reply(f"Удалено {deleted_count} чеков.")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['list_invoices'])
async def list_active_invoices(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        invoices = await cryptopay.get_invoices(status='active')
        if not invoices:
            await message.reply("Нет активных инвойсов.")
            return

        response = "Активные инвойсы:\n\n"
        for invoice in invoices:
            response += f"ID: {invoice.invoice_id}, Сумма: {invoice.amount} {invoice.asset}\n"
        
        await message.reply(response)
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['delete_invoice'])
async def delete_invoice(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        invoice_id = message.text.split('/delete_invoice ')[1]
        await cryptopay.delete_invoice(invoice_id)
        await message.answer(f'Инвойс {invoice_id} удален.')
    except IndexError:
        await message.reply("Используйте: /delete_invoice <ID инвойса>")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['delete_all_invoices'])
async def delete_all_invoices(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply("Вы не админ!")
        return

    try:
        invoices = await cryptopay.get_invoices(status='active')
        if not invoices:
            await message.reply("Нет активных инвойсов.")
            return

        deleted_count = 0
        for invoice in invoices:
            await cryptopay.delete_invoice(invoice.invoice_id)
            deleted_count += 1

        await message.reply(f"Удалено {deleted_count} инвойсов.")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@dp.callback_query_handler(text="how_to_bet")
async def how_to_bet_callback(call: types.CallbackQuery):
    await call.answer()
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = InlineKeyboardMarkup()
    back_button = InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    keyboard.add(back_button)
    
    await call.message.answer(
        config.HOW_TO_BET_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.callback_query_handler(text="back_to_main")
async def back_to_main_callback(call: types.CallbackQuery):
    await call.answer()
    
    # Создаем главное меню (аналогично /start)
    keyboard = InlineKeyboardMarkup(row_width=2)

    make_bet_btn = types.InlineKeyboardButton(
        text="🎯 Сделать ставку",
        url=config.channel_link
    )

    how_to_bet_btn = types.InlineKeyboardButton(
        text="ℹ️ Как сделать ставку",
        callback_data="how_to_bet"
    )

    games_btn = types.InlineKeyboardButton(
        text="🎮 Игры в боте",
        url="https://t.me/SPIND_BET_BOT"  # ← если другой бот — поменяй
    )

    haart_btn = types.InlineKeyboardButton(
        text="Игровой канал",
        url="https://t.me/+v01pNqgHVYs0ZTEy"  # ← если другой бот — поменяй
    )


    keyboard.add(haart_btn)
    keyboard.add(how_to_bet_btn, games_btn)
    keyboard.add(make_bet_btn)
    
    # Редактируем сообщение с инструкцией или отправляем новое
    try:
        await call.message.edit_text(
            "👋 <b>Добро пожаловать в SpindBet!</b> \n\n"
            "✨ Здесь сбываются мечты и случаются чудеса!\n"
            "🎯 Делайте ставку и испытайте удачу — возможно, именно вы сорвете следующий куш! 🤑",
            reply_markup=keyboard
        )
    except:
        # Если не удалось отредактировать (например, сообщение слишком старое)
        await call.message.answer(
            "👋 <b>Добро пожаловать в SpindBet!</b> \n\n"
            "✨ Здесь сбываются мечты и случаются чудеса!\n"
            "🎯 Делайте ставку и испытайте удачу — возможно, именно вы сорвете следующий куш! 🤑",
            reply_markup=keyboard
        )

# Обработчик /balance
@dp.message_handler(commands=['balance'])
async def check_balance(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        balance = await cryptopay.get_balance()
        await message.answer(balance)
    else:
        message.reply("пошел нахуй малыш")

# Обработчик /pay_money
@dp.message_handler(commands=['pay_money'])
async def cmd_paymoney(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        amount = float(message.text.split(" ")[2])
        id = int(message.text.split(" ")[1])
        await pay_money(amount, id)
        await message.reply("Средства успешно переведены")
    else:
        await message.reply("<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
