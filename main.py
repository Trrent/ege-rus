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
        options = task.options.split('%')
        if task.rule:
            explanation = '\n'.join(task.rule.rule.split('\\n'))
        else:
            explanation = task.correct_option
        shuffle(options)
        await bot.send_poll(chat_id=user_id,
                            question=task.question,
                            options=options,
                            type='quiz',
                            explanation=explanation,
                            correct_option_id=options.index(task.correct_option),
                            is_anonymous=False)
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
    keyboard.row(types.KeyboardButton(task_buttons[4]), types.KeyboardButton(task_buttons[8]))
    await bot.send_message(chat_id=user_id, text='Выберете тип задания для тренировки\n\nДля остановки используйте /stop',
                           reply_markup=keyboard)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)