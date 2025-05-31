import os
import re
import shutil
from asyncio import sleep

from fastapi import UploadFile, HTTPException

from config.config import settings


def verify_file_type(filename: str, allowed_types: list):
    """根据文件名验证文件类型
    :param filename:
    :param allowed_types:
    :return:
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型. 允许的扩展名: {', '.join(allowed_types)}"
        )
    return ext


def read_text_file(file: UploadFile) -> str:
    """读取文本文件内容
    :param file:
    :return:
    """
    try:
        content = file.file.read().decode("utf-8")
        return content
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="文件无法以UTF-8解码，可能不是文本文件"
        )


async def process_str(text: str) -> str:
    """
    处理字符串
    :param text:
    :return:
    """
    if text == "" or text == " ":
        return text
    n: str = os.linesep
    normalized_content = re.sub(r"\\r\\n", n, text)
    normalized_content = re.sub(r"\\n", n, normalized_content)
    normalized_content = re.sub(r"(?<=^)```markdown", "", normalized_content)
    normalized_content = re.sub(r"```(?=$)", "", normalized_content)

    return normalized_content


async def save_file(file: UploadFile, user_id: str = "") -> str:
    """
    保存上传的文件
    :param file:
    :param user_id:
    :return: 保存后的文件路径
    """
    # 构建文件保存路径
    upload_dir, temp_dir, result_dir = await create_dir(user_id)
    file_path = os.path.join(upload_dir, file.filename)

    if os.path.exists(file_path):
        print(f"文件已存在，删除旧文件: {file_path}")
        os.remove(file_path)
        result_path = result_dir + "/" + os.path.splitext(file.filename)[0] + ".md"
        if os.path.exists(result_path):
            os.remove(result_path)
            print(f"删除旧文件: {result_path}")
    # 保存文件到本地
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()  # 读取文件内容
            buffer.write(content)  # 写入文件到本地
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传时文件保存失败: {str(e)}")
    await sleep(1)
    return file_path


async def create_dir(user_id: str):
    """
    创建用户文件夹
    :param user_id:
    :return:
    """
    user_dir, upload_dir, temp_dir, result_dir = get_dir(user_id)
    if not os.path.exists(f'{settings.UPLOAD_DIR}'):
        os.makedirs(f'{settings.UPLOAD_DIR}')
        print(f"创建文件夹 {settings.UPLOAD_DIR} 成功")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        print(f"创建 {user_id} 文件夹成功")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        print("创建 temp 文件夹成功")
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        print("创建 result 文件夹成功")
    # os.makedirs(upload_dir, exist_ok=True)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        print("创建 upload 文件夹成功")
    return upload_dir, temp_dir, result_dir


def get_dir(user_id: str):
    """
    获取用户文件夹
    :param user_id:
    :return:
    """
    upload_dir = f"{settings.UPLOAD_DIR}/{user_id}/upload"
    result_dir = f"{settings.UPLOAD_DIR}/{user_id}/result"
    temp_dir = f"{settings.UPLOAD_DIR}/{user_id}/temp"
    user_dir = f"{settings.UPLOAD_DIR}/{user_id}"

    return user_dir, upload_dir, temp_dir, result_dir


async def delete_dir(del_dir: str):
    """
    删除文件夹，递归删除整个文件夹及其内容
    :param del_dir:
    :return:
    """
    if not os.path.exists(del_dir):
        print(f"路径不存在: {del_dir}")
        return

    try:
        shutil.rmtree(del_dir)
        print(f"成功删除文件夹: {del_dir}")
    except Exception as e:
        print(f"删除文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件夹失败: {str(e)}")


async def read_md(file_name: str, user_id: str = ""):
    """
    读取md文件，不带后缀名
    :param file_name:
    :param user_id:
    :return:
    """
    user_dir, upload_dir, temp_dir, result_dir = get_dir(user_id)
    # read_dir = os.path.join(result_dir, file_name)
    # 文件名不带后缀名
    result_file = f"{result_dir}/{file_name}.md"
    if not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail=f"文件不存在或未清洗完成: {file_name}")
    with open(result_file, 'r', encoding='utf-8') as file:
        content = file.read()
    return "```markdown" + content + "```"
