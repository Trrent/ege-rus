import logging
import os
from aiogram import Bot, types, Dispatcher, executor
from aiogram.utils.executor import start_webhook
from aiogram.dispatcher import filters
from random import choice, shuffle, sample

from data.tasks import Task
from data.users import User
from data import db_session

TOKEN = os.environ.get('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
db_session.global_init("db/ege.db")

task_buttons = {4: '4️⃣',
                8: '8️⃣',
                9: '9️⃣',
                10: '🔟',
                11: '1️⃣1️⃣',
                12: '1️⃣2️⃣',
                '4️⃣': 4,
                '8️⃣': 8,
                '9️⃣': 9,
                '🔟': 10,
                '1️⃣1️⃣': 11,
                '1️⃣2️⃣': 12}

APP_NAME = os.getenv('APP_NAME')

WEBHOOK_HOST = f'https://{APP_NAME}.up.railway.app'
WEBHOOK_PATH = f'/webhook/{TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = os.getenv('PORT', default=8000)


MY_ID = os.environ.get('MY_ID')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(f'Привет, {message.from_user.first_name}')
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.user_id == message.from_user.id).first()
    if not user:
        user = User(user_id=message.from_user.id)
        db_sess.add(user)
        db_sess.commit()
    await send_menu(message=message)


@dp.poll_answer_handler()
async def poll_answer(poll_answer: types.PollAnswer):
    try:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.user_id == poll_answer.user.id).first()
        await send_poll(poll_answer.user.id, type=user.task_type)
    except Exception as e:
        await bot.send_message(chat_id=MY_ID, text=e)
        await send_menu(user_id=poll_answer.user.id)


@dp.message_handler(filters.Text(equals=task_buttons.values()))
async def poll(message: types.Message):
    try:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.user_id == message.from_user.id).first()
        user.task_type = task_buttons[message.text]
        db_sess.commit()
        await send_poll(message.from_user.id, type=task_buttons[message.text])
    except Exception as e:
        await bot.send_message(chat_id=MY_ID, text=e)
        await send_menu(user_id=message.from_user.id)


async def send_poll(user_id, type):
    try:
        session = db_session.create_session()
        tasks = session.query(Task).filter(Task.type == type).all()
        task = choice(tasks)
        if type in [9, 10, 11, 12]:
            correct_option = choice(task.correct_option.split('%'))
            options = sample(task.options.split('%'), 3)
            options.append(correct_option)
        else:
            options = task.options.split('%')
            correct_option = task.correct_option
        if task.rule:
            explanation = '\n'.join(task.rule.rule.split('\\n'))
        else:
            explanation = None
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
        await bot.send_message(chat_id=MY_ID, text=e)
        if task:
            await bot.send_message(chat_id=MY_ID, text=str(task))
        await send_menu(user_id=user_id.from_user.id)


@dp.message_handler(commands=['menu', 'stop'])
@dp.message_handler()
async def send_menu(message: types.Message = None, user_id=None):
    if not user_id:
        user_id = message.from_user.id
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row(types.KeyboardButton(task_buttons[4]), types.KeyboardButton(task_buttons[8]),
                 types.KeyboardButton(task_buttons[9]))
    keyboard.row(types.KeyboardButton(task_buttons[10]), types.KeyboardButton(task_buttons[11]),
                 types.KeyboardButton(task_buttons[12]))
    await bot.send_message(chat_id=user_id,
                           text='Выберите тип задания для тренировки\n\nДля остановки используйте /stop',
                           reply_markup=keyboard)


async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    session = db_session.create_session()
    users = session.query(User).all()
    for user in users:
        await bot.send_message(chat_id=user.user_id, text='Бот обновился!\nДля перезапуска напиши /start')


async def on_shutdown(dispatcher):
    await bot.delete_webhook()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
