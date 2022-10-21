from aiogram import Bot, types, Dispatcher, executor

from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

tasks = [{
    'question': 'В одном из приведённых ниже предложений НЕВЕРНО употреблено выделенное слово. Исправьте лексическую ошибку, подобрав к выделенному слову пароним. Запишите подобранное слово.',
    'options': ['Отправляясь на охоту, он надел ветровку БОЛОТНОГО цвета.',
                'Зимой в ЛЕДЯНОМ дворце часто проходят соревнования по фигурному катанию.',
                'Петр — человек мягкий, тонкий, весьма ДИПЛОМАТИЧНЫЙ.', 'Вон уж в окно смотрит ВЫСОКИЙ месяц.',
                'Я непременно должен высказать своё ЛИЧНОЕ мнение по этому вопросу.'],
    'explanation': 'Ошибка допущена в предложении:\nЗимой в ЛЕДЯНОМ дворце часто проходят соревнования по фигурному катанию. Слово ЛЕДЯНОЙ следует заменить на ЛЕДОВЫЙ.\nОтвет: ледовом.',
    'correct_option_id': 1}]


# @dp.message_handler()
# async def echo(message: types.Message):
# await message.answer(message.text)

@dp.poll_answer_handler()
async def poll_answer(poll_answer: types.PollAnswer):
    print(poll_answer)
    user_id = poll_answer.user.id
    task = tasks[0]
    await bot.send_poll(chat_id=user_id, question=task['question'],
                        options=task['options'],
                        type='quiz',
                        explanation=task['explanation'],
                        correct_option_id=task['correct_option_id'],
                        is_anonymous=False)


@dp.message_handler()
async def poll(message: types.Message):
    await message.answer_poll(question='Your answer?',
                              options=['A)', 'B)', 'C'],
                              type='quiz',
                              explanation='explain',
                              correct_option_id=1,
                              is_anonymous=False)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
