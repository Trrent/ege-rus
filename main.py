from aiogram import Bot, types, Dispatcher, executor
from random import choice, shuffle

from data.tasks import Task

from config import TOKEN
from data import db_session

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
db_session.global_init("db/ege.db")

tasks = [{
    'question': 'В одном из приведённых ниже предложений НЕВЕРНО употреблено выделенное слово. Исправьте лексическую ошибку, подобрав к выделенному слову пароним. Запишите подобранное слово.',
    'options': ['Отправляясь на охоту, он надел ветровку БОЛОТНОГО цвета.',
                'Зимой в ЛЕДЯНОМ дворце часто проходят соревнования по фигурному катанию.',
                'Петр — человек мягкий, тонкий, весьма ДИПЛОМАТИЧНЫЙ.', 'Вон уж в окно смотрит ВЫСОКИЙ месяц.',
                'Я непременно должен высказать своё ЛИЧНОЕ мнение по этому вопросу.'],
    'explanation': 'Ошибка допущена в предложении:\nЗимой в ЛЕДЯНОМ дворце часто проходят соревнования по фигурному катанию. Слово ЛЕДЯНОЙ следует заменить на ЛЕДОВЫЙ.\nОтвет: ледовом.',
    'correct_option_id': 1}]


@dp.poll_answer_handler()
async def poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    await send_poll(user_id)


@dp.message_handler()
async def poll(message: types.Message):
    await send_poll(message.from_user.id)


async def send_poll(user_id, type=4):
    session = db_session.create_session()
    tasks = session.query(Task).filter(Task.type == type).all()
    task = choice(tasks)
    options = task.options.split('%')
    shuffle(options)
    await bot.send_poll(chat_id=user_id,
                        question=task.question,
                        options=options,
                        type='quiz',
                        explanation=task.explanation,
                        correct_option_id=options.index(task.correct_option),
                        is_anonymous=False)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
