# from utils.db_api.models import Question, User, Result
# from starlette.exceptions import HTTPException
# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm import sessionmaker
# from data.config import engine, Base
# from datetime import datetime
# from starlette import status
# from gzip import compress
#
# chunk_size = 262144
# FILE_SIZE = 5242880
#
#
# def create_file_chunk(image: bytes, file_uuid: str):
#     session = sessionmaker(bind=engine)()
#     try:
#         current_chunk = 0
#         done_reading = False
#         while not done_reading:
#             bfr = image[current_chunk * chunk_size: (current_chunk + 1) * chunk_size]
#             if not bfr:
#                 done_reading = True
#                 break
#             result = FileChunk(file_id=file_uuid, chunk=bytearray(bfr))
#             session.add(result)
#             session.commit()
#             session.refresh(result)
#             current_chunk += 1
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#
#
# def create_file(**kwargs):
#     session = sessionmaker(bind=engine)()
#     try:
#         print(kwargs, '123123123')
#         result = FileRepository(**kwargs)
#         session.add(result)
#         session.commit()
#         session.refresh(result)
#         session.close()
#         return result.file_id
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#         print('file yaratildi!!!')
#
#
# def create_file1(user_id: str, contract_number: str, image: bytes, content_type: str,
#                  file_uuid: str):
#     create_file_chunk(image=image, file_uuid=file_uuid)
#     return create_file(user_id=user_id, contract_number=contract_number,
#                        content_type=content_type, file_id=file_uuid, date=datetime.now().strftime("%Y-%m-%d"),
#                        time=datetime.now().strftime("%H:%M:%S"))
#
#
# async def file_create_(user_id, images):
#     zipped_files = []
#     for image in images:
#         zipped_files.append((compress(image[0].read()), "application/pdf"))
#         print(user_id[0], '-----------------------------')
#         if len(compress(image[0].read())) > FILE_SIZE: raise HTTPException(
#             status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
#     return {"data": [
#         create_file1(user_id=str(user_id[0]), image=image[0],
#                      contract_number=str(user_id[2]), content_type="application/pdf", file_uuid=str(user_id[1]))
#         for image in zipped_files]}
#
#
# def create_user_info(**kwargs):
#     session = sessionmaker(bind=engine)()
#     try:
#         print(kwargs)
#         print('-----------------------123132312231')
#         result = User(**kwargs)
#         session.add(result)
#         print(result)
#         session.commit()
#         session.refresh(result)
#         session.close()
#         return User.from_orm(result)
#     except Exception as e:
#         return e
#
#
# def get_user_info(passport: str):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(User).filter_by(passport=passport).first()
#         session.close()
#         return result
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#
#
# def check_user(user_id: int):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(User).filter_by(telegram_id=user_id).first()
#         session.close()
#         return result
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#
#
# def get_max_contract_number():
#     session = sessionmaker(bind=engine)()
#     try:
#         next_contract_number = f"{int(session.query(User).order_by(User.contract_number.desc()).first().contract_number) + 1:03d}"  # 3 xonalik raqamga o'tkazish
#         session.close()
#         return str(next_contract_number)
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#
#
# def get_user_by_id(passport: str):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(User).filter_by(passport=passport).first()
#         session.close()
#         return result
#     except Exception as e:
#         return e
#     finally:
#         session.close()
#
#
# def get_file(file_uuid: str, path_: str):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(FileChunk).filter_by(file_id=file_uuid).all()
#         session.close()
#         return result
#     except IntegrityError:
#         return "Malumot topilmadi!"
#     finally:
#         session.close()
#
#
# def get_files(user_id: int):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(FileRepository).filter_by(user_id=user_id).all()
#         session.close()
#         return result
#     except Exception as e:
#         return e
#
#
# def get_file_(file_uuid: str):
#     session = sessionmaker(bind=engine)()
#     try:
#         result = session.query(FileRepository).filter_by(file_id=file_uuid).first()
#         session.close()
#         return result
#     except Exception as e:
#         return e
#     finally:
#         session.close()
