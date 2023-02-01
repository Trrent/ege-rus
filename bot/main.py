import logging
import os
from aiogram import Bot, types, Dispatcher
from aiogram.dispatcher import filters
from random import choice, shuffle, sample

from data.tasks import Task
from data.users import User
from data import db_session


task_buttons = {4: '4️⃣',
                7: '7️⃣',
                8: '8️⃣',
                9: '9️⃣',
                10: '🔟',
                11: '1️⃣1️⃣',
                12: '1️⃣2️⃣',
                '4️⃣': 4,
                '7️⃣': 7,
                '8️⃣': 8,
                '9️⃣': 9,
                '🔟': 10,
                '1️⃣1️⃣': 11,
                '1️⃣2️⃣': 12}

TOKEN = os.environ.get('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
MY_ID = os.environ.get('MY_ID')


async def start(message: types.Message):
    await message.answer(f'Привет, {message.from_user.first_name}')
    user_id = message.from_user.id
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db_sess.add(user)
        db_sess.commit()
        logging.info(f"New user: {user_id}")
        await bot.send_message(chat_id=MY_ID, text=f"New user: @{message.from_user.username}\n{user_id}")
    await send_menu(message=message)


async def poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    try:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.user_id == poll_answer.user.id).first()
        if user:
            if user.task_type:
                await send_poll(user_id, type=user.task_type)
            else:
                await send_menu(user_id=user_id)
        else:
            await send_menu(user_id=user_id)
    except Exception as e:
        await exception_handler(e, user_id)


async def poll(message: types.Message):
    user_id = message.from_user.id
    try:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.user_id == message.from_user.id).first()
        if not user:
            user = User(user_id=user_id, task_type=task_buttons[message.text])
            db_sess.add(user)
            db_sess.commit()
            logging.info(f"New user: {user_id}")
            await bot.send_message(chat_id=MY_ID, text=f"New user: @{message.from_user.username}\n{user_id}")
        else:
            user.task_type = task_buttons[message.text]
            db_sess.commit()
        await send_poll(user_id, type=task_buttons[message.text])
    except Exception as e:
        await exception_handler(e, user_id)


async def send_poll(user_id, type):
    task = None
    explanation = None
    try:
        session = db_session.create_session()
        tasks = session.query(Task).filter(Task.type == type).all()
        task = choice(tasks)
        if type in [9, 10, 11, 12]:
            correct_option = choice(task.correct_option.split('%'))
            options = sample(task.options.split('%'), 3)
            options.append(correct_option)
        elif type == 7:
            correct_option, explanation = choice(task.correct_option.split('%')).split('(')
            options = sample(task.options.split('%'), 4)
            options.append(correct_option)
        else:
            options = task.options.split('%')
            correct_option = task.correct_option
        if task.rule:
            explanation = '\n'.join(task.rule.rule.split('\\n'))
        shuffle(options)
        await bot.send_poll(chat_id=user_id,
                            question=task.question,
                            options=options,
                            type='quiz',
                            explanation=explanation,
                            correct_option_id=options.index(correct_option),
                            is_anonymous=False,
                            reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        await exception_handler(e, user_id, task)


async def send_menu(message: types.Message = None, user_id=None):
    if not user_id:
        user_id = message.from_user.id
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row(types.KeyboardButton(task_buttons[4]), types.KeyboardButton(task_buttons[7]),
                 types.KeyboardButton(task_buttons[8]))
    keyboard.row(types.KeyboardButton(task_buttons[9]), types.KeyboardButton(task_buttons[10]),
                 types.KeyboardButton(task_buttons[11]))
    keyboard.row(types.KeyboardButton(task_buttons[12]))
    await bot.send_message(chat_id=user_id,
                           text='Выберите тип задания для тренировки\n\nДля остановки используйте /stop',
                           reply_markup=keyboard)


async def send_all(message: types.Message):
    user_id = message.from_user.id
    try:
        if int(user_id) != int(MY_ID):
            return
        _, text = message.text.split(' ', maxsplit=1)
        if text:
            session = db_session.create_session()
            users = session.query(User).all()
            for user in users:
                await bot.send_message(chat_id=user.id, text=text)
    except Exception as e:
        await exception_handler(e, user_id)


async def send_users_table(message: types.Message):
    user_id = message.from_user.id
    try:
        if int(user_id) != int(MY_ID):
            return
        session = db_session.create_session()
        with open('users.csv', 'w', newline='') as outfile:
            file = csv.writer(outfile)
            records = session.query(User).all()
            for user in records:
                file.writerow([getattr(user, col.name) for col in User.__mapper__.columns])
        with open('users.csv', 'r') as outfile:
            await bot.send_document(chat_id=user_id, document=outfile)
        os.remove('users.csv')
    except Exception as e:
        await exception_handler(e, user_id)


async def exception_handler(exception_text, user_id, task=None):
    logging.error(f"Exception: {exception_text}")
    await bot.send_message(chat_id=MY_ID, text=exception_text)
    if task:
        await bot.send_message(chat_id=MY_ID, text=str(task.id))

# Selectel Lambda funcs
async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"])
    dp.register_message_handler(send_menu, commands=["menu"])
    dp.register_message_handler(send_menu, commands=["stop"])
    dp.register_message_handler(send_menu, commands=["help"])
    dp.register_message_handler(poll, filters.Text(equals=task_buttons.values()))
    dp.register_poll_answer_handler(poll_answer)


async def process_event(update, dp: Dispatcher):
    Bot.set_current(dp.bot)
    await dp.process_update(update)

# Selectel serverless entry point
async def main(**kwargs):
    db_session.global_init(os.sep.join([os.path.abspath(os.path.dirname(__file__)), "db", "ege.db"]))
    await register_handlers(dp)

    update = types.Update.to_object(kwargs)
    await process_event(update, dp)

    return 'ok'