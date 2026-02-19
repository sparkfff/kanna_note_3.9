from io import BytesIO
import os
import asyncio
from .base import FetchUrl, FilePath
import brotli
from .util import download_stream
import httpx
from .database import cn_data, jp_data, tw_data
import logging

logger = logging.getLogger(__name__)

async def update_pcr_database():
    """更新PCR数据库文件 - 修复版本"""
    # 配置数据库更新参数
    db_configs = [
        (FetchUrl.cn_url.value, FilePath.cn_db.value, cn_data, "国服"),
        (FetchUrl.jp_url.value, FilePath.jp_db.value, jp_data, "日服"),
        (FetchUrl.tw_url.value, FilePath.tw_db.value, tw_data, "台服"),
    ]
    
    success_count = 0
    
    for url, path, db_instance, server_name in db_configs:
        logger.info(f"开始更新{server_name}数据库...")
        
        try:
            # 步骤1: 关闭数据库连接
            logger.info(f"关闭{server_name}数据库连接...")
            await db_instance.engine.dispose()
            
            # 等待连接释放
            await asyncio.sleep(2)
            
            # 步骤2: 下载新数据库到临时文件
            logger.info(f"下载{server_name}数据库文件...")
            decompressor = brotli.Decompressor()
            with open(FilePath.temp_db.value, "wb") as f:
                async for chunk in download_stream(url):
                    f.write(decompressor.process(chunk))
            
            # 步骤3: 安全替换文件
            logger.info(f"替换{server_name}数据库文件...")
            if os.path.exists(path):
                os.remove(path)
            os.rename(FilePath.temp_db.value, path)
            
            # 步骤4: 重新初始化数据库
            logger.info(f"重新初始化{server_name}数据库...")
            await db_instance.init()
            
            success_count += 1
            logger.info(f"{server_name}数据库更新成功")
            
        except PermissionError as e:
            logger.error(f"{server_name}数据库更新失败: 权限错误 - {e}")
            # 清理临时文件
            if os.path.exists(FilePath.temp_db.value):
                os.remove(FilePath.temp_db.value)
            continue
            
        except Exception as e:
            logger.error(f"{server_name}数据库更新失败: {e}")
            # 清理临时文件
            if os.path.exists(FilePath.temp_db.value):
                os.remove(FilePath.temp_db.value)
            continue
    
    logger.info(f"数据库更新完成，成功更新 {success_count}/{len(db_configs)} 个数据库")
    return success_count


def generate_pcr_fullcard(id_, star):
    return (
        f"{FetchUrl.fullcard_url.value}/{id_}{star}1.webp",
        FilePath.fullcard.value / f"fullcard_unit_{id_}{star}1.png",
    )


async def cache_download(url, save_path):
    temp = BytesIO()
    async for chunk in download_stream(url):
        temp.write(chunk)
    with open(save_path, "wb") as f:  # 写入文件,防止出错
        f.write(temp.getvalue())


async def get_pcr_fullcard(id_):
    url, save_path = generate_pcr_fullcard(id_, 6)
    if save_path.exists():
        return save_path
    try:
        await cache_download(url, save_path)
        return save_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            url, save_path = generate_pcr_fullcard(id_, 3)
            if save_path.exists():
                return save_path
            if not save_path.exists():
                try:
                    await cache_download(url, save_path)
                    return save_path
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise ValueError(f"暂无id为{id_}的全卡数据") from e


async def get_skill_icon(skill_icon_id):
    url = f"{FetchUrl.skill_icon_url.value}/{skill_icon_id}.webp"
    save_path = FilePath.skill_icon.value / f"{skill_icon_id}.png"
    if save_path.exists():
        return save_path
    try:
        await cache_download(url, save_path)
        return save_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"暂无id为{skill_icon_id}的技能图标") from e


async def get_equipment_icon(equipment_icon_id):
    url = f"{FetchUrl.equipment_url.value}/{equipment_icon_id}.webp"
    save_path = FilePath.equipment.value / f"{equipment_icon_id}.png"
    if save_path.exists():
        return save_path
    try:
        await cache_download(url, save_path)
        return save_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"暂无id为{equipment_icon_id}的装备图标") from e


async def get_enemy_icon(enemy_id):
    url = f"{FetchUrl.enemy_icon_url.value}/{enemy_id}.webp"
    save_path = FilePath.enemy.value / f"{enemy_id}.png"
    if save_path.exists():
        return save_path
    try:
        await cache_download(url, save_path)
        return save_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return FilePath.icon.value / "kailu.png"  # 默认图标


async def get_teaser_icon(teaser_id, type_):
    utl = f"{FetchUrl.teaser_url.value.format(type_)}/{teaser_id}.webp"
    save_path = FilePath.teaser.value / f"{teaser_id}.png"
    if save_path.exists():
        return save_path
    try:
        await cache_download(utl, save_path)
        return save_path
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"暂无id为{teaser_id}的预告图标") from e
