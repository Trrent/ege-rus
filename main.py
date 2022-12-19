import os
from aiogram import Bot, types, Dispatcher, executor
from aiogram.dispatcher import filters
from random import choice, shuffle

from data.tasks import Task
from data.users import User
from data import db_session

TOKEN = os.environ.get('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
db_session.global_init("db/ege.db")

task_buttons = {4: '4️⃣',
                8: '8️⃣',
                '4️⃣': 4,
                '8️⃣': 8}


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(f'Привет, {message.from_user.first_name}')
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.user_id == message.from_user.id).first()
    if not user:
        user = User(user_id=message.from_user.id)
        db_sess.add(user)
        db_sess.commit()
    await send_menu(message)


@dp.message_handler(commands=['menu', 'stop'])
async def send_menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton(task_buttons[4]))
    keyboard.add(types.KeyboardButton(task_buttons[8]))
    await message.answer('Выберете тип задания для тренировки\n\nДля остановки используйте /stop',
                         reply_markup=keyboard)


@dp.poll_answer_handler()
async def poll_answer(poll_answer: types.PollAnswer):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.user_id == poll_answer.user.id).first()
    await send_poll(poll_answer.user.id, type=user.task_type)


@dp.message_handler(filters.Text(equals=task_buttons.values()))
async def poll(message: types.Message):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.user_id == message.from_user.id).first()
    user.task_type = task_buttons[message.text]
    db_sess.commit()
    await send_poll(message.from_user.id, type=task_buttons[message.text])


async def send_poll(user_id, type):
    session = db_session.create_session()
    tasks = session.query(Task).filter(Task.type == type).all()
    task = choice(tasks)
    options = task.options.split('%')
    shuffle(options)
    await bot.send_poll(chat_id=user_id,
                        question=task.question,
                        options=options,
                        type='quiz',
                        explanation=options[options.index(task.correct_option)],
                        correct_option_id=options.index(task.correct_option),
                        is_anonymous=False)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
