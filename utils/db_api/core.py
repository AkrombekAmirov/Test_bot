from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from LoggerService import LoggerService
from .models import User, Subject, Question, Result
from sqlmodel import SQLModel, Field, select
from sqlalchemy.exc import OperationalError
from typing import Optional, List, Type
from datetime import datetime
from json import dumps
from asyncio import sleep
from data import DATABASE_URL

class DatabaseService:
    MAX_RETRIES = 5  # Katta yuklanish uchun qayta urinishlar soni oshirilgan
    RETRY_DELAY = 2  # Qayta urinishning boshlang'ich kechikishi; eksponensial orqaga qaytish bilan qo'llaniladi
    ENGINE: Optional[AsyncEngine] = None  # Barcha uchun umumiy havza ulanish (pooling) konfiguratsiyasi

    def __init__(self):
        """Baza ulanishini havza orqali yaratish."""
        self.engine = self.get_engine()
        self.logging = LoggerService().get_logger()

    @classmethod
    def get_engine(cls):
        """Async engine ulanishi havza yordamida sozlanadi."""
        if cls.ENGINE is None:
            cls.ENGINE = create_async_engine(
                DATABASE_URL,
                echo=False,
                pool_size=20,  # Yuqori yuklanish uchun sozlangan
                max_overflow=10,
            )
        return cls.ENGINE

    async def _add(self, instance: SQLModel):
        """Helper method to add an instance with retries in case of connection issues."""
        retries = 0
        while retries < self.MAX_RETRIES:
            async with AsyncSession(self.engine) as session:
                try:
                    async with session.begin():
                        session.add(instance)
                    await session.refresh(instance)
                    self.logging.info(f"Added: {instance}")
                    return instance.id
                except OperationalError as e:
                    self.logging.error(f"Database connection error on add attempt {retries + 1}: {e}")
                    retries += 1
                    await sleep(self.RETRY_DELAY)
                except Exception as e:
                    self.logging.error(f"Error adding instance: {e}")
                    break
        return None

    async def _update(self, instance: SQLModel):
        """Helper method to update an instance with retry logic."""
        retries = 0
        while retries < self.MAX_RETRIES:
            async with AsyncSession(self.engine) as session:
                try:
                    async with session.begin():
                        await session.merge(instance)
                    await session.refresh(instance)
                    self.logging.info(f"Updated: {instance}")
                    return instance.id
                except OperationalError as e:
                    self.logging.error(f"Database connection error on update attempt {retries + 1}: {e}")
                    retries += 1
                    await sleep(self.RETRY_DELAY)
                except Exception as e:
                    self.logging.error(f"Error updating instance: {e}")
                    break
        return None

    async def get(self, model: Type[SQLModel], filter_by: Optional[dict] = None, limit: Optional[int] = None) -> \
            Optional[List[SQLModel]]:
        """
        Ma'lumotlar bazasidan model asosida yozuvlarni olish uchun umumiy get funksiyasi.

        :param model: SQLModel turidagi model (jadval).
        :param filter_by: Filtlash shartlari (masalan, {"id": 1, "name": "John"}).
        :param limit: Qaytariladigan yozuvlar soni cheklovchi parametr.
        :return: Model yozuvlari ro'yxati yoki bo'sh ro'yxat.
        """
        retries = 0
        while retries < self.MAX_RETRIES:
            async with AsyncSession(self.engine) as session:
                try:
                    query = select(model)

                    # Filtrlash shartlarini qo'shish
                    if filter_by:
                        for key, value in filter_by.items():
                            if hasattr(model, key):  # Kalit mavjudligini tekshirish
                                query = query.where(getattr(model, key) == value)
                            else:
                                self.logging.warning(f"Invalid filter key: {key} for model {model.__name__}")

                    # Limit qo'llash
                    if limit:
                        query = query.limit(limit)

                    result = await session.execute(query)
                    records = result.scalars().all()
                    return records if records else []

                except OperationalError as e:
                    self.logging.error(f"Database connection error on get attempt {retries + 1}: {e}")
                    retries += 1
                    await sleep(self.RETRY_DELAY)
                except Exception as e:
                    self.logging.error(f"Error retrieving data from {model.__name__}: {e}")
                    break
        return None

    async def update_user(self, user_id: str, updates: dict):
        """Update user information based on a dictionary of updates."""
        async with AsyncSession(self.engine) as session:
            user = await session.get(User, user_id)
            if user:
                # Diktan yangilanishlarni qo'llash
                for key, value in updates.items():
                    if value is not None:
                        setattr(user, key, value)

                # Foydalanuvchining yangilangan versiyasini bazaga saqlash
                return await self._update(user)
            else:
                self.logging.error(f"User with id {user_id} not found")
                return None

    async def result_update(self, result_id: int, updates: dict):
        async with AsyncSession(self.engine) as session:
            async with session.begin():  # Sessiyani boshlash
                result = await session.get(Result, result_id)  # Obyektni sessiyadan olish
                if result:
                    for key, value in updates.items():
                        if value is not None:
                            setattr(result, key, value)  # Xususiyatlarni yangilash
                    self.logging.info(f"Result with ID {result_id} updated successfully")
                    return result.id
                else:
                    self.logging.error(f"Result with id {result_id} not found")
                    return None

    async def add_user(self, user_id: int, name: str, username: str, phone_number: Optional[str] = None):
        return await self._add(User(user_id=user_id, name=name, username=username, phone_number=phone_number))

    async def add_subject(self, name: str, subject_val: int):
        return await self._add(Subject(name=name, subject_val=subject_val))

    async def add_question(self, subject_id: int, question: str, option1: str, option2: str, option3: str,
                           option4: str):
        return await self._add(
            Question(subject_id=subject_id, text=question, option1=option1, option2=option2, option3=option3,
                     option4=option4, correct_answer=option1))

    async def add_result(self, user_id: int, subject_id: int, question_ids):
        return await self._add(Result(
            user_id=user_id,
            subject_id=subject_id,
            question_ids=question_ids,  # Savol IDlarini JSON formatiga o‘tkazish
            status=True
        ))

    async def get_user_by_id(self, user_id: int) -> Optional[SQLModel]:
        """ID orqali foydalanuvchini olish."""
        self.logging.info(f"Foydalanuvchini ID orqali qidirish: {user_id}")
        user = await self.get(User, filter_by={"user_id": user_id}, limit=1)
        return user[0] if user else None

    async def get_user(self, user_id: int) -> Optional[User]:
        user = await self.get(User, filter_by={"user_id": user_id}, limit=1)
        return user[0] if user else None

    async def get_questioin_by_id(self, question_id: int) -> Optional[SQLModel]:
        question = await self.get(Question, filter_by={"id": question_id}, limit=1)
        self.logging.info(f"Savolni ID orqali qidirish: {question_id}")
        return question[0] if question else None

    async def get_question(self, subject_id: int, text: str) -> Optional[Question]:
        filters = {"subject_id": subject_id, "text": text}
        questions = await self.get(Question, filter_by=filters, limit=1)
        self.logging.info(f"Questions with subject_id={subject_id} and text={text} retrieved successfully")
        return questions[0] if questions else None

    async def get_subject(self, name: str) -> Optional[Subject]:
        """subject_id va name bo'yicha bitta subjectni olish."""
        self.logging.info(f"Retrieving subject with name: {name}")
        subject = await self.get(Subject, filter_by={"name": name}, limit=1)
        return subject[0] if subject else None

    async def get_result_id(self, result_id: int) -> Optional[SQLModel]:
        """
        result_id asosida natijani olish uchun yordamchi funksiya.

        :param result_id: Result jadvalidagi qatorning ID raqami.
        :return: Result obyekt yoki None agar topilmasa.
        """
        result = await self.get(model=Result, filter_by={"id": result_id}, limit=1)
        self.logging.info(f"Result with ID {result_id} retrieved successfully")
        return result[0] if result else None

    async def get_active_result(self, user_id: int):
        # Foydalanuvchining barcha test natijalarini olish
        results = await self.get(model=Result, filter_by={"user_id": user_id})

        if results:
            for result in results:
                # Agar test yakunlanmagan bo'lsa (number < 25), faqat bunday testni qaytaramiz
                if result.number < 25:
                    return {
                        "result_id": result.id,
                        "number": result.number,
                        "subject_id": result.subject_id,
                    }
                self.logging.info(f"Result with ID {result.id} is complete")

        # Agar faol test topilmasa, None qaytaramiz
        return None

    async def get_result(self, user_id: int, subject_id: int):
        self.logging.info(f"Result with user_id={user_id} and subject_id={subject_id} retrieved successfully")
        return await self.get(model=Result, filter_by={"user_id": user_id, "subject_id": subject_id}, limit=1)

    async def user_update_test_id(self, user_id: str, test_id: str):
        async with AsyncSession(self.engine) as session:
            try:
                statement = select(User).where(User.user_id == user_id)
                result = await session.execute(statement)
                user = result.scalar_one_or_none()
                if user is None:
                    self.logging.warning(f"User not found: user_id={user_id}")
                    return None
                user.test_id = test_id
                await session.commit()
                await session.refresh(user)
                self.logging.info(f"Updated test_id for user_id={user_id}: {user.test_id}")
                return user.id
            except OperationalError as e:
                self.logging.error(f"Database connection error on user_update_test_id: {e}")
                return None
            except Exception as e:
                self.logging.error(f"Error updating test_id for user: {e}")
                return None

    # boshqa usullar ham xuddi shu tarzda qayta ishlanishi mumkin
