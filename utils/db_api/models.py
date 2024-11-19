from sqlmodel import SQLModel, Field, Column, TEXT
from typing import Optional, List, Dict
from sqlalchemy import BigInteger
from datetime import datetime
from pytz import timezone
import logging
import json

# Logger konfiguratsiyasi
logging.basicConfig(level=logging.INFO)


# Xatoliklarni boshqarish uchun dekorator
def get_current_time() -> tuple:
    return Field(default_factory=lambda: datetime.now(timezone('Asia/Tashkent')).strftime("%H:%M:%S"),
                 description="Yaratilgan vaqt"), Field(
        default_factory=lambda: datetime.now(timezone('Asia/Tashkent')).strftime("%H:%M:%S"),
        description="Yaratilgan vaqt")


class BaseModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_date: str = Field(default_factory=lambda: datetime.now(timezone('Asia/Tashkent')).strftime("%d:%m:%y"), description="Yaratilgan vaqt")
    created_time: str = Field(default_factory=lambda: datetime.now(timezone('Asia/Tashkent')).strftime("%H:%M:%S"), description="Yaratilgan vaqt")
    updated_date: Optional[str] = Field(default=None, description="Yangilangan sana")
    updated_time: Optional[str] = Field(default=None, description="Yangilangan vaqt")

    def to_dict(self) -> dict:
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}

    # def update_timestamp(self):
    #     date, time = get_current_time()
    #     self.updated_date = date
    #     self.updated_time = time


class User(BaseModel, table=True):
    __tablename__ = 'users'
    user_id: int = Field(..., sa_column=Column(BigInteger, unique=True),
                         description="Foydalanuvchi ID")  # BigInt uchun sa_column qo'shildi
    name: str = Field(..., description="Foydalanuvchi ismi")
    username: str = Field(..., description="Foydalanuvchi nomi")
    phone_number: Optional[str] = Field(default=None, description="Telefon raqami")


class Subject(BaseModel, table=True):
    __tablename__ = 'subjects'
    name: str = Field(..., description="Fan nomi")
    subject_val: str = Field(..., description="Fan qiymati")


class Question(BaseModel, table=True):
    __tablename__ = 'questions'
    subject_id: int = Field(..., description="Fan ID")
    text: str = Field(..., description="Savol matni")
    option1: str = Field(..., description="Javob variantlari")
    option2: str = Field(..., description="Javob variantlari")
    option3: str = Field(..., description="Javob variantlari")
    option4: str = Field(..., description="Javob variantlari")
    correct_answer: str = Field(..., description="To'g'ri javob")

    def get_options(self) -> Dict[str, str]:
        return json.loads(self.options) if self.options else {}


class Result(BaseModel, table=True):
    __tablename__ = 'results'
    user_id: int = Field(..., sa_column=Column(BigInteger), description="Foydalanuvchi ID")
    subject_id: int = Field(..., description="Fan ID")
    question_ids: str = Field(sa_column=Column(TEXT), description="Savol ID larining ro'yxati JSON formatida")
    user_answers: str = Field(sa_column=Column(TEXT), description="Foydalanuvchi javoblari JSON formatida")
    correct_answers: int = Field(default=0, description="To'g'ri javoblar soni")
    wrong_answers: int = Field(default=0, description="Noto'g'ri javoblar soni")
    number: int = Field(default=0, description="Test holati uchun")
    status: bool = Field(default=False, description="Test holati")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def set_question_ids(self, ids: List[int]) -> None:
        """Savol ID larini JSON formatida saqlaydi."""
        self.question_ids = json.dumps(ids)

    def get_question_ids(self) -> List[int]:
        """Savol ID larini JSON formatidan ro‘yxatga aylantiradi."""
        return json.loads(self.question_ids) if self.question_ids else []

    def set_user_answers(self, answers: List[str]) -> None:
        """Foydalanuvchi javoblarini JSON formatida saqlaydi."""
        self.user_answers = json.dumps(answers)

    def get_user_answers(self) -> List[str]:
        """Foydalanuvchi javoblarini JSON formatidan ro‘yxatga aylantiradi."""
        return json.loads(self.user_answers) if self.user_answers else []

    def add_user_answer(self, question_id: int, answer: str) -> None:
        """
        Foydalanuvchi tomonidan berilgan javobni qo'shadi.
        Savolga javob qo'shish uchun, user_answers listiga yangi javobni kiritadi.
        """
        # Savol ID larini olish
        question_ids = self.get_question_ids()

        # Foydalanuvchi javoblarini olish
        user_answers = self.get_user_answers()

        # Agar savol ID mavjud bo'lsa, uni yangilaymiz
        if question_id not in question_ids:
            question_ids.append(question_id)
            user_answers.append(answer)
        else:
            # Agar savol allaqachon kiritilgan bo'lsa, javobni yangilaymiz
            index = question_ids.index(question_id)
            user_answers[index] = answer

        # Yangilangan ma'lumotlarni saqlaymiz
        self.set_question_ids(question_ids)
        self.set_user_answers(user_answers)

    def update_score(self, correct: int, wrong: int) -> None:
        """Natijalarni yangilaydi."""
        self.correct_answers += correct
        self.wrong_answers += wrong

    def accuracy(self) -> float:
        """To‘g‘ri javoblar foizini qaytaradi."""
        total_answers = self.correct_answers + self.wrong_answers
        return (self.correct_answers / total_answers) * 100 if total_answers > 0 else 0

    def is_passed(self) -> bool:
        """Testdan o‘tish holatini tekshiradi."""
        return self.accuracy() >= 50

    def to_summary(self) -> dict:
        """Natijalar haqida qisqacha ma'lumot."""
        return {
            "user_id": self.user_id,
            "test_id": self.id,
            "accuracy": self.accuracy(),
            "status": self.status,
            "created_date": self.created_date.isoformat()
        }
