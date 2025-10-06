import asyncio
import csv
import logging
import os
from pathlib import Path
from random import choice, sample, shuffle
from typing import Optional, Union

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import (
    FSInputFile,
    KeyboardButton,
    Message,
    PollAnswer,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from dotenv import load_dotenv

from data import db_session
from data.tasks import Task
from data.users import User

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

TOKEN = os.getenv("TOKEN")
MY_ID = os.getenv("MY_ID")

if not TOKEN:
    raise RuntimeError("Environment variable TOKEN must be provided.")

MY_ID_INT = int(MY_ID) if MY_ID and MY_ID.isdigit() else None

TASK_BUTTONS = {
    4: "4️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
    11: "1️⃣1️⃣",
    12: "1️⃣2️⃣",
}
def init_database() -> None:
    db_path = BASE_DIR / "db" / "ege.db"
    db_session.global_init(str(db_path))


init_database()

BUTTON_TO_TASK = {emoji: task_type for task_type, emoji in TASK_BUTTONS.items()}

router = Router()

def build_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=TASK_BUTTONS[4]),
                KeyboardButton(text=TASK_BUTTONS[7]),
                KeyboardButton(text=TASK_BUTTONS[8]),
            ],
            [
                KeyboardButton(text=TASK_BUTTONS[9]),
                KeyboardButton(text=TASK_BUTTONS[10]),
                KeyboardButton(text=TASK_BUTTONS[11]),
            ],
            [KeyboardButton(text=TASK_BUTTONS[12])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

async def send_menu(bot: Bot, user_id: int) -> None:
    await bot.send_message(
        chat_id=user_id,
        text="Выберите тип задания для тренировки\n\nДля остановки используйте /stop",
        reply_markup=build_menu_keyboard(),
    )

async def send_poll(bot: Bot, user_id: int, task_type: int) -> None:
    session = db_session.create_session()
    task: Optional[Task] = None
    try:
        tasks = session.query(Task).filter(Task.type == task_type).all()
        if not tasks:
            raise ValueError(f"Нет заданий типа {task_type}.")

        task = choice(tasks)
        explanation: Optional[str] = None
        options_pool = task.options.split("%")
        correct_option: Optional[str] = None

        if task_type in {9, 10, 11, 12}:
            correct_option = choice(task.correct_option.split("%"))
            sample_size = min(3, len(options_pool))
            options = sample(options_pool, k=sample_size)
            if correct_option not in options:
                options.append(correct_option)
        elif task_type == 7:
            raw_correct = choice(task.correct_option.split("%"))
            if "(" in raw_correct:
                correct_option, explanation = raw_correct.split("(", maxsplit=1)
                explanation = explanation.rstrip(")")
            else:
                correct_option = raw_correct
            sample_size = min(4, len(options_pool))
            options = sample(options_pool, k=sample_size)
            if correct_option not in options:
                options.append(correct_option)
        else:
            correct_option = task.correct_option
            options = options_pool

        if task.rule and task.rule.rule:
            explanation = "\n".join(task.rule.rule.split("\\n"))

        shuffle(options)
        await bot.send_poll(
            chat_id=user_id,
            question=task.question,
            options=options,
            type="quiz",
            explanation=explanation,
            correct_option_id=options.index(correct_option),
            is_anonymous=False,
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as error:
        await exception_handler(bot, error, user_id, task)
    finally:
        session.close()

async def exception_handler(
    bot: Bot,
    error: Union[Exception, str],
    user_id: Optional[int],
    task: Optional[Task] = None,
) -> None:
    message = str(error)
    logging.exception("Exception while processing update: %s", message)
    if MY_ID_INT is None:
        return

    await bot.send_message(chat_id=MY_ID_INT, text=message)
    if task is not None:
        await bot.send_message(chat_id=MY_ID_INT, text=f"Task id: {task.id}")

@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    await message.answer(f"Привет, {message.from_user.first_name}")

    session = db_session.create_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id)
            session.add(user)
            session.commit()
            logging.info("New user: %s", user_id)
            if MY_ID_INT is not None:
                await bot.send_message(
                    chat_id=MY_ID_INT,
                    text=f"New user: @{message.from_user.username}\n{user_id}",
                )
    except Exception as error:
        await exception_handler(bot, error, user_id)
        return
    finally:
        session.close()

    await send_menu(bot, user_id)

@router.message(Command(commands=["menu", "stop", "help"]))
async def menu_handler(message: Message, bot: Bot) -> None:
    await send_menu(bot, message.from_user.id)

@router.message(F.text.in_(tuple(BUTTON_TO_TASK.keys())))
async def poll_handler(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    task_type = BUTTON_TO_TASK.get(message.text)
    if task_type is None:
        await send_menu(bot, user_id)
        return

    session = db_session.create_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        is_new_user = user is None

        if is_new_user:
            user = User(user_id=user_id, task_type=task_type)
            session.add(user)
        else:
            user.task_type = task_type

        session.commit()

        if is_new_user and MY_ID_INT is not None:
            logging.info("New user: %s", user_id)
            await bot.send_message(
                chat_id=MY_ID_INT,
                text=f"New user: @{message.from_user.username}\n{user_id}",
            )

        await send_poll(bot, user_id, task_type)
    except Exception as error:
        await exception_handler(bot, error, user_id)
    finally:
        session.close()

@router.poll_answer()
async def poll_answer_handler(poll_answer: PollAnswer, bot: Bot) -> None:
    user_id = poll_answer.user.id
    session = db_session.create_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user and user.task_type:
            await send_poll(bot, user_id, user.task_type)
        else:
            await send_menu(bot, user_id)
    except Exception as error:
        await exception_handler(bot, error, user_id)
    finally:
        session.close()

@router.message(Command("send_all"))
async def send_all_handler(
    message: Message,
    bot: Bot,
    command: CommandObject,
) -> None:
    user_id = message.from_user.id
    if MY_ID_INT is None or int(user_id) != MY_ID_INT:
        return

    if not command.args:
        await message.answer("Укажите текст рассылки после команды.")
        return

    session = db_session.create_session()
    try:
        users = session.query(User).all()
        for user in users:
            await bot.send_message(chat_id=user.user_id, text=command.args)
    except Exception as error:
        await exception_handler(bot, error, user_id)
    finally:
        session.close()

@router.message(Command("users"))
async def send_users_table_handler(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    if MY_ID_INT is None or int(user_id) != MY_ID_INT:
        return

    temp_path = BASE_DIR / "users.csv"
    session = db_session.create_session()
    try:
        with temp_path.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            records = session.query(User).all()
            for record in records:
                writer.writerow([getattr(record, column.name) for column in User.__mapper__.columns])

        document = FSInputFile(temp_path)
        await bot.send_document(chat_id=user_id, document=document)
    except Exception as error:
        await exception_handler(bot, error, user_id)
    finally:
        session.close()
        if temp_path.exists():
            temp_path.unlink()

async def process_update_event(update_data: dict) -> str:
    dispatcher = get_dispatcher()
    update = Update.model_validate(update_data)
    async with Bot(token=TOKEN) as bot:
        await dispatcher.feed_update(bot, update)
    return "ok"

def get_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher

async def run_bot() -> None:
    logging.basicConfig(level=logging.INFO)
    init_database()
    dispatcher = get_dispatcher()
    async with Bot(token=TOKEN) as bot:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)

def main() -> None:
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
