import asyncio
import io
import os
import re

import fitz
from PIL import Image
from fastapi import APIRouter
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from config.config import settings
from core.file import pdf_ocr_service, get_status
from core.tools import verify_file_type, read_text_file, process_str, save_file, delete_dir, read_md
from schemas.util import ResponseModel
from services.db_token import db
from services.llm import chat_service

router = APIRouter()


@router.get("/init")
async def init(user_id: str = ""):
    """
    在进入数据清洗页面前初始化，清除用户缓存记录，避免脏数据污染 \n
    :param user_id: \n
    :return:
    """
    if not user_id or user_id == "" or user_id is None or user_id == " ":
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "用户ID错误",
                "data": " "
            }
        )
    try:
        # 清空用户缓存文件
        await delete_dir(f"{settings.UPLOAD_DIR}/{user_id}")
        # 清空token记录
        await db.delete_token_record(user_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": " "
            }
        )
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "init success",
        }
    )


@router.post("/upload", response_model=ResponseModel)
async def upload_file(file: UploadFile = File(...), user_id: str = ""):
    """
    上传文件 \n
    :param file: \n
    :param user_id: \n
    :return: \n
    script: \n
        更新：如果上传的文件名存在同名的，会删掉旧文件，并清除旧文件的清洗结果 \n
        因为状态码为2，表示清洗完成，为了避免出现问题，建议每次上传文件后都调用查状态接口，这样前面清洗完成了，再上传一个同名文件，就不会出现状态错误的问题
    """
    if not file:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "文件错误",
                "data": " "
            }
        )
    if not user_id or user_id == "" or user_id is None or user_id == " ":
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "用户ID错误",
                "data": " "
            }
        )
    # 验证文件类型
    try:
        type = verify_file_type(file.filename, settings.PDF)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": f"文件类型错误，支持格式：{settings.PDF}",
                "data": None
            }
        )
    try:
        # 保存文件
        file_path = await save_file(file, user_id)
        # 开启异步线程执行任务
        asyncio.create_task(pdf_ocr_service(file_path, user_id))
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "success",
            }
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "code": e.status_code,
                "message": e.detail,
                "data": " "
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": " "
            }
        )


@router.get("/status")
async def status(user_id: str = ""):
    """
    查询文件清洗状态 \n
    :param user_id: \n
    :return: \n
    script: \n
        更新：添加一个参数：status_type --> 0 未开始（没有该用户的缓存数据），1 进行中(有数据未清洗完成)，2 已完成（上传的文件已全部清洗完成）
    """
    if not user_id or user_id == "" or user_id is None or user_id == " ":
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "用户ID错误",
                "data": " "
            }
        )
    try:
        # 获取文件状态
        status_type, result = await get_status(user_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": " "
            }
        )
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "success",
            "data": {
                "user_id": user_id,
                "status_type": status_type,
                "status": result,
            }
            # "data": {"status": status}
        }
    )


@router.get("/token")
async def get_token(user_id: str = ""):
    """
    查询各文档消耗的token数 \n
    :param user_id: \n
    :return: \n
    返回示例：\n
        [ \n
            {"user_id": "user1", "file_name": "example.pdf", "total_tokens": 150},\n
            {"user_id": "user1", "file_name": "test.pdf", "total_tokens": 200}\n
        ]
    """
    if not user_id or user_id == "" or user_id is None or user_id == " ":
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "用户ID错误",
                "data": " "
            }
        )
    try:
        result = await db.list_user_records(user_id=user_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}"
            }
        )
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "success",
            "data": result
        }
    )

@router.get("/getfile")
async def get_md(user_id: str = "", file_name: str = ""):
    """
    获取文件内容，参数不能带文件后缀名 \n
    :param user_id: \n
    :param file_name: 不能携带文件后缀名 \n
    :return:
    """
    if not user_id or user_id == " " or user_id == "" or user_id is None:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "用户名错误",
                "data": " "
            }
        )
    if not file_name or file_name == " " or file_name == "" or file_name is None:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "文件错误",
                "data": " ",
                "tokens": 0
            }
        )
    # 读文件
    result = await read_md(file_name, user_id)
    tokens = await db.read_token_record(user_id, file_name)
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "success",
            "data": result,
            "tokens": tokens
        }
    )


@router.post("/download")
async def download(pdf_str: str = ""):
    """
    下载文件
    :param pdf_str:
    :return:
    """
    if not pdf_str or pdf_str == " " or pdf_str == "" or pdf_str is None:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "文件错误",
                "data": " "
            }
        )
    try:
        file_stream = io.BytesIO(pdf_str.encode("utf-8"))
        normalized_content = await process_str(pdf_str)
        return StreamingResponse(
            normalized_content,
            media_type="text/markdown; charset=utf-8",
            # media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=example.md",
                "Content-Type": "text/markdown; charset=utf-8"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": None
            }
        )
