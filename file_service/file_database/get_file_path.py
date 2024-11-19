from os.path import join, dirname

async def get_path(file_name):
    return join(dirname(__file__), file_name)

async def join_file(file_name):
    return join('file_service/file_database', file_name)
