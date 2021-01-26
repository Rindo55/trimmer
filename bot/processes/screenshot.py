import os
import io
import time
import math
import shutil
import logging
import datetime

from pyrogram.types import InputMediaPhoto, InputMediaDocument

from bot.config import Config
from bot.utils import Utilities
from bot.messages import Messages as ms
from bot.database import Database
from .base import BaseProcess


log = logging.getLogger(__name__)
db = Database()


class ScreenshotsProcessFailure(Exception):
    def __init__(self, for_user, for_admin, extra_details=None):
        self.for_user = for_user
        self.for_admin = for_admin
        self.extra_details = extra_details


class ScreenshotsProcess(BaseProcess):
    async def _get_media_message(self):
        message = await self.client.get_messages(
            self.chat_id, self.input_message.reply_to_message.message_id
        )
        await self.input_message.reply_to_message.delete()
        return message.reply_to_message

    async def process(self):
        _, num_screenshots = self.input_message.data.split("+")
        num_screenshots = int(num_screenshots)
        output_folder = Config.SCREENSHOTS_FOLDER.joinpath(self.process_id)
        os.makedirs(output_folder, exist_ok=True)
        await self.reply_message.edit_text(ms.PROCESSING_REQUEST, quote=True)
        try:
            if self.media_msg.empty:
                raise ScreenshotsProcessFailure(
                    for_user=ms.MEDIA_MESSAGE_DELETED,
                    for_admin=ms.MEDIA_MESSAGE_DELETED,
                )

            await self.track_user_activity()
            start_time = time.time()
            await self.input_message.edit_message_text(ms.SCREENSHOTS_START)
            duration = await Utilities.get_duration(self.file_link)
            if isinstance(duration, str):
                raise ScreenshotsProcessFailure(
                    for_user=ms.CANNOT_OPEN_FILE,
                    for_admin=ms.SCREENSHOTS_OPEN_ERROR.format(
                        file_link=self.file_link,
                        num_screenshots=num_screenshots,
                        duration=duration,
                    ),
                )

            log.info(
                "Generating %s screenshots from location: %s for %s",
                num_screenshots,
                self.file_link,
                self.chat_id,
            )

            reduced_sec = duration - int(duration * 2 / 100)
            screenshots = []
            watermark = await db.get_watermark_text(self.chat_id)
            as_file = await db.is_as_file(self.chat_id)
            screenshot_mode = await db.get_screenshot_mode(self.chat_id)
            ffmpeg_errors = ""
            watermark_options = "scale=1280:-1"
            if watermark:
                watermark_color_code = await db.get_watermark_color(self.chat_id)
                watermark_color = Config.COLORS[watermark_color_code]
                watermark_position = await db.get_watermark_position(self.chat_id)
                font_size = await db.get_font_size(self.chat_id)
                width, height = await Utilities.get_dimentions(self.file_link)
                fontsize = int(
                    (math.sqrt(width ** 2 + height ** 2) / 1388.0)
                    * Config.FONT_SIZES[font_size]
                )
                x_pos, y_pos = Utilities.get_watermark_coordinates(
                    watermark_position, width, height
                )
                watermark_options = (
                    f"drawtext=fontcolor={watermark_color}:fontsize={fontsize}:x={x_pos}:"
                    f"y={y_pos}:text={watermark}, scale=1280:-1"
                )

            ffmpeg_cmd = [
                "ffmpeg",
                "-headers",
                f"IAM:{Config.IAM_HEADER}",
                "-hide_banner",
                "-ss",
                "",  # To be replaced in loop
                "-i",
                self.file_link,
                "-vf",
                watermark_options,
                "-y",
                "-vframes",
                "1",
                "",  # To be replaced in loop
            ]

            if screenshot_mode == 0:
                screenshot_secs = [
                    int(reduced_sec / num_screenshots) * i
                    for i in range(1, 1 + num_screenshots)
                ]
            else:
                screenshot_secs = [
                    Utilities.get_random_start_at(reduced_sec)
                    for i in range(1, 1 + num_screenshots)
                ]

            for i, sec in enumerate(screenshot_secs):
                thumbnail_template = output_folder.joinpath(f"{i+1}.png")
                ffmpeg_cmd[5] = str(sec)
                ffmpeg_cmd[-1] = str(thumbnail_template)
                log.debug(ffmpeg_cmd)
                output = await Utilities.run_subprocess(ffmpeg_cmd)
                log.debug(output)
                await self.input_message.edit_message_text(
                    ms.SCREENSHOTS_PROGRESS.format(current=i + 1, total=num_screenshots)
                )
                if thumbnail_template.exists():
                    if as_file:
                        InputMediaDocument(
                            str(thumbnail_template),
                            caption=ms.SCREENSHOT_AT.format(
                                time=datetime.timedelta(seconds=sec)
                            ),
                        )
                    else:
                        screenshots.append(
                            InputMediaPhoto(
                                str(thumbnail_template),
                                caption=ms.SCREENSHOT_AT.format(
                                    time=datetime.timedelta(seconds=sec)
                                ),
                            )
                        )
                    continue

                ffmpeg_errors += output[0].decode() + "\n" + output[1].decode() + "\n\n"

            if not screenshots:
                error_file = None
                if ffmpeg_errors:
                    error_file = io.BytesIO()
                    error_file.name = f"{self.process_id}-errors.txt"
                    error_file.write(ffmpeg_errors.encode())
                raise ScreenshotsProcessFailure(
                    for_user=ms.SCREENSHOT_PROCESS_FAILED,
                    for_admin=ms.SCREENSHOTS_FAILED_GENERATION.format(
                        file_link=self.file_link, num_screenshots=num_screenshots
                    ),
                    extra_details=error_file,
                )

            await self.reply_message.edit_text(
                text=ms.SCREENSHOT_PROCESS_SUCCESS.format(
                    count=num_screenshots, total_count=len(screenshots)
                )
            )
            await self.media_msg.reply_chat_action("upload_photo")
            await self.media_msg.reply_media_group(screenshots, True)
            await self.reply_message.edit_text(
                ms.PROCESS_UPLOAD_CONFIRM.format(
                    total_process_duration=datetime.timedelta(
                        seconds=int(time.time() - start_time)
                    )
                )
            )
        except ScreenshotsProcessFailure as e:
            log.error(e)
            await self.reply_message.edit_text(e.for_user)
            log_msg = await self.media_msg.forward(Config.LOG_CHANNEL)
            if e.extra_details:
                await log_msg.reply_document(
                    document=e.extra_details, quote=True, caption=e.for_admin
                )
            else:
                await log_msg.reply_text(
                    text=e.for_admin,
                    quote=True,
                )
        finally:
            shutil.rmtree(output_folder, ignore_errors=True)
