__version__ = (1, 4, 8, 8)

# Author: @Timur2287g_orig
# meta developer: @Timur2287g_orig
# requires: aiohttp
# meta banner: https://x0.at/U8id.jpg
# meta pic: https://x0.at/U8id.jpg
#
# XActions
# Автоматическая публикация репостов X в Telegram.
#
# Для работы X необходимо установить twitter-cli:
# pipx install twitter-cli
#
# Авторизация X:
# AuthToken = cookie auth_token
# CT0       = cookie ct0
#
# Получить cookies:
# 1. Открой https://x.com и войди в свой аккаунт.
# 2. F12 -> Application -> Storage -> Cookies -> https://x.com
# 3. Найди:
#    auth_token
#    ct0
# 4. Скопируй их значения в конфиг модуля.
#
# Никому не передавай AuthToken и CT0.
# Эти cookies дают доступ к твоей X-сессии.


import asyncio
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
from urllib.parse import urlparse

from .. import loader, utils


@loader.tds
class XActions(loader.Module):
    """Автоматическая публикация репостов X в Telegram"""

    strings = {
        "name": "XActions",

        "info": (
            "<i>🪐 XActions</i>\n\n"
            "<blockquote>"
            "Автоматически отслеживает репосты указанного пользователя X "
            "и публикует оригинальные посты в Telegram.\n"
            "</blockquote>"
            "<blockquote expandable>"
            "<b>Команды:</b>\n"
            "▫️ <code>-xactions</code> — информация\n"
            "▫️ <code>-xcheck</code> — проверить X репосты\n"
            "▫️ <code>-xlogin</code> — проверить X и авторизацию через cookie\n"
            "▫️ <code>-xreset</code> — сбросить историю\n"
            "▫️ <code>-xstart</code> — запустить автопроверку (автоматический xcheck)\n"
            "▫️ <code>-xstop</code> — остановить автопроверку\n"
            "▫️ <code>-xstats</code> — статистика\n"
            "▫️ <code>-xtest</code> — проверить чат отправки на доступность\n\n"
            "<b>Автор:</b> @Timur2287g_orig"
            "</blockquote>"
        ),

        "checking": (
            "🔎 <b>Проверяю новые репосты X...</b>"
        ),

        "no_new": (
            "ℹ️ Новых репостов нет."
        ),

        "found": (
            "🔁 Найдено новых репостов: <b>{}</b>"
        ),

        "sent": (
            "✅ Опубликовано: <b>{}</b>"
        ),

        "base_created": (
            "✅ Создана базовая точка.\n"
            "Постов в текущей выборке: <b>{}</b>\n\n"
            "Старые репосты не отправлены."
        ),

        "reset": (
            "♻️ <b>История репостов сброшена.</b>\n"
            "Следующая проверка создаст новую базовую точку."
        ),

        "started": (
            "▶️ <b>Автопроверка запущена.</b>\n"
            "Интервал проверки: <code>{}</code> сек.\n"
            "Задержка перед публикацией: <code>{}</code> сек."
        ),

        "already_started": (
            "ℹ️ Автопроверка уже запущена."
        ),

        "stopped": (
            "⏹ <b>Автопроверка остановлена.</b>"
        ),

        "not_started": (
            "ℹ️ Автопроверка не запущена."
        ),

        "test_ok": (
            "✅ <b>Telegram-чат работает.</b>"
        ),

        "x_ok": (
            "✅ <b>X доступен.</b>\n"
            "📨 Получено постов: <code>{}</code>\n"
            "📡 twitter-cli успешно получил данные."
        ),

        "error": (
            "❌ <b>Ошибка:</b>\n"
            "<code>{}</code>"
        ),

        "stats": (
            "📊 <b>XActions</b>\n\n"
            "📨 Проверено репостов: <code>{}</code>\n"
            "✅ Опубликовано: <code>{}</code>\n"
            "❌ Ошибок: <code>{}</code>\n"
            "▶️ Автопроверка: <code>{}</code>\n"
            "⏱ Интервал: <code>{}</code> сек.\n"
            "⏳ Задержка: <code>{}</code> сек."
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(

            loader.ConfigValue(
                "Username",
                "",
                (
                    "Username X без @. "
                    "Укажи username аккаунта X, "
                    "репосты которого нужно отслеживать."
                ),
                validator=loader.validators.Hidden(
                    loader.validators.String()
                ),
            ),

            loader.ConfigValue(
                "AuthToken",
                "",
                (
                    "Cookie auth_token из x.com. "
                    "Получить: X -> F12 -> Application -> "
                    "Storage -> Cookies -> x.com -> auth_token."
                ),
                validator=loader.validators.Hidden(
                    loader.validators.String()
                ),
            ),

            loader.ConfigValue(
                "CT0",
                "",
                (
                    "Cookie ct0 из x.com. "
                    "Получить: X -> F12 -> Application -> "
                    "Storage -> Cookies -> x.com -> ct0."
                ),
                validator=loader.validators.Hidden(
                    loader.validators.String()
                ),
            ),

            loader.ConfigValue(
                "RepostsChat",
                "",
                (
                    "ID Telegram-чата, куда будут публиковаться "
                    "найденные репосты."
                ),
                validator=loader.validators.Hidden(
                    loader.validators.String()
                ),
            ),

            loader.ConfigValue(
                "CheckInterval",
                60,
                (
                    "Интервал автоматической проверки X "
                    "в секундах. Минимум 30 секунд."
                ),
                validator=loader.validators.Integer(
                    minimum=30
                ),
            ),

            loader.ConfigValue(
                "PostDelay",
                0,
                (
                    "Задержка перед каждой публикацией "
                    "в секундах. 0 = без задержки."
                ),
                validator=loader.validators.Integer(
                    minimum=0
                ),
            ),

            loader.ConfigValue(
                "InitialLoad",
                20,
                (
                    "Количество последних постов X, "
                    "запрашиваемых при одной проверке."
                ),
                validator=loader.validators.Integer(
                    minimum=1
                ),
            ),

            loader.ConfigValue(
                "DownloadMedia",
                True,
                (
                    "Скачивать изображения и видео "
                    "из оригинальных постов."
                ),
                validator=loader.validators.Boolean(),
            ),

            loader.ConfigValue(
                "SendTextWithoutMedia",
                True,
                (
                    "Отправлять текстовый пост, если "
                    "медиа отсутствует или не загрузилось."
                ),
                validator=loader.validators.Boolean(),
            ),

            loader.ConfigValue(
                "AddAuthorHashtag",
                True,
                (
                    "Добавлять #username автора оригинального "
                    "поста в начало публикации."
                ),
                validator=loader.validators.Boolean(),
            ),
        )

        self.client = None
        self.db = None

        self.task = None
        self.running = False

        self.checked = 0
        self.published = 0
        self.errors = 0

        self.check_lock = asyncio.Lock()

        self.temp_root = os.path.join(
            tempfile.gettempdir(),
            "xactions_media",
        )

    # =========================================================
    # READY
    # =========================================================

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        self.cleanup_temp_root()

    async def on_unload(self):
        await self.stop_loop()
        self.cleanup_temp_root()

    # =========================================================
    # TEMP FILES
    # =========================================================

    def cleanup_temp_root(self):
        try:
            if os.path.isdir(self.temp_root):
                shutil.rmtree(
                    self.temp_root,
                    ignore_errors=True,
                )
        except Exception:
            pass

    def create_temp_dir(self):
        os.makedirs(
            self.temp_root,
            exist_ok=True,
        )

        return tempfile.mkdtemp(
            prefix="post_",
            dir=self.temp_root,
        )

    def cleanup_temp_dir(self, path):
        if not path:
            return

        try:
            shutil.rmtree(
                path,
                ignore_errors=True,
            )
        except Exception:
            pass

    # =========================================================
    # DATABASE
    # =========================================================

    def get_seen(self):
        return set(
            self.db.get(
                self.name,
                "seen",
                [],
            )
        )

    def save_seen(self, values):
        values = list(values)

        if len(values) > 3000:
            values = values[-3000:]

        self.db.set(
            self.name,
            "seen",
            values,
        )

    def is_initialized(self):
        return self.db.get(
            self.name,
            "initialized",
            False,
        )

    def set_initialized(self, value=True):
        self.db.set(
            self.name,
            "initialized",
            value,
        )

    # =========================================================
    # CONFIG
    # =========================================================

    def get_username(self):
        return (
            str(
                self.config["Username"]
            )
            .strip()
            .lstrip("@")
        )

    def get_delay(self):
        return max(
            0,
            int(
                self.config["PostDelay"]
            ),
        )

    # =========================================================
    # TWITTER CLI
    # =========================================================

    def twitter_binary(self):
        binary = shutil.which("twitter")

        if binary:
            return binary

        virtual_env = os.environ.get(
            "VIRTUAL_ENV"
        )

        if virtual_env:
            candidate = os.path.join(
                virtual_env,
                "bin",
                "twitter",
            )

            if os.path.isfile(candidate):
                return candidate

        return "twitter"

    async def run_twitter(self, *args):
        username = self.get_username()

        if not username:
            raise RuntimeError(
                "Username не указан в конфигурации."
            )

        auth_token = str(
            self.config["AuthToken"]
        ).strip()

        ct0 = str(
            self.config["CT0"]
        ).strip()

        if not auth_token:
            raise RuntimeError(
                "AuthToken не указан в конфигурации."
            )

        if not ct0:
            raise RuntimeError(
                "CT0 не указан в конфигурации."
            )

        command = [
            self.twitter_binary(),
            *args,
        ]

        env = os.environ.copy()

        env["TWITTER_AUTH_TOKEN"] = auth_token
        env["TWITTER_CT0"] = ct0

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode(
            "utf-8",
            errors="replace",
        )

        stderr_text = stderr.decode(
            "utf-8",
            errors="replace",
        )

        if process.returncode != 0:
            error_text = (
                stderr_text.strip()
                or stdout_text.strip()
                or "twitter-cli завершился с ошибкой."
            )

            raise RuntimeError(
                self.hide_secrets(error_text)
            )

        return stdout_text, stderr_text

    def hide_secrets(self, text):
        if not text:
            return text

        for key in (
            "AuthToken",
            "CT0",
            "Username",
            "RepostsChat",
        ):
            try:
                value = str(
                    self.config[key]
                ).strip()

                if value:
                    text = text.replace(
                        value,
                        "***",
                    )
            except Exception:
                pass

        text = re.sub(
            r"(auth_token=)[^;\s]+",
            r"\1***",
            text,
            flags=re.I,
        )

        text = re.sub(
            r"(ct0=)[^;\s]+",
            r"\1***",
            text,
            flags=re.I,
        )

        return text

    async def get_posts(self):
        maximum = max(
            1,
            int(
                self.config["InitialLoad"]
            ),
        )

        stdout, _ = await self.run_twitter(
            "user-posts",
            self.get_username(),
            "--max",
            str(maximum),
            "--json",
        )

        try:
            result = json.loads(stdout)
        except Exception as e:
            raise RuntimeError(
                "twitter-cli вернул некорректный JSON: "
                + str(e)
            )

        if not isinstance(
            result,
            dict,
        ):
            raise RuntimeError(
                "twitter-cli вернул неизвестный формат данных."
            )

        if result.get("ok") is False:
            raise RuntimeError(
                str(
                    result.get(
                        "error",
                        "twitter-cli сообщил об ошибке.",
                    )
                )
            )

        posts = result.get(
            "data",
            [],
        )

        if not isinstance(
            posts,
            list,
        ):
            posts = []

        return posts

    # =========================================================
    # TEXT
    # =========================================================

    def clean_text(self, text):
        if not text:
            return ""

        text = str(text)

        text = re.sub(
            r"https?://t\.co/\S+",
            "",
            text,
        )

        text = re.sub(
            r"[ \t]+\n",
            "\n",
            text,
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    def make_caption(self, tweet):
        text = self.clean_text(
            tweet.get(
                "text",
                "",
            )
        )

        author = tweet.get(
            "author",
            {},
        )

        if not isinstance(
            author,
            dict,
        ):
            author = {}

        author_name = (
            author.get(
                "screenName"
            )
            or author.get(
                "username"
            )
            or "unknown"
        )

        lines = []

        if self.config[
            "AddAuthorHashtag"
        ]:
            tag = re.sub(
                r"[^A-Za-z0-9_]",
                "",
                str(author_name),
            )

            if tag:
                lines.append(
                    f"#{tag}"
                )

        if text:
            lines.append(
                "<blockquote expandable>"
                + html.escape(
                    text,
                    quote=False,
                )
                + "</blockquote>"
            )

        tweet_id = tweet.get(
            "id"
        )

        if tweet_id:
            source = (
                "https://x.com/"
                + str(author_name)
                + "/status/"
                + str(tweet_id)
            )

            lines.append(
                "▎<a href=\""
                + html.escape(
                    source,
                    quote=True,
                )
                + "\">Source</a>"
            )

        return "\n".join(lines)

    # =========================================================
    # MEDIA
    # =========================================================

    def get_media(self, tweet):
        media = tweet.get(
            "media",
            [],
        )

        if not isinstance(
            media,
            list,
        ):
            return []

        result = []

        for item in media:
            if not isinstance(
                item,
                dict,
            ):
                continue

            media_type = item.get(
                "type"
            )

            url = item.get(
                "url"
            )

            if not url:
                continue

            if media_type == "photo":
                result.append(
                    (
                        "photo",
                        url,
                    )
                )

            elif media_type == "video":
                result.append(
                    (
                        "video",
                        url,
                    )
                )

        return result

    # =========================================================
    # MEDIA EXTENSION
    # =========================================================

    def extension_from_content_type(
        self,
        content_type,
        url,
        media_type=None,
    ):
        content_type = (
            str(
                content_type or ""
            )
            .split(";")[0]
            .strip()
            .lower()
        )

        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
        }

        if content_type in mapping:
            return mapping[
                content_type
            ]

        path = urlparse(url).path

        extension = os.path.splitext(
            path
        )[1].lower()

        allowed = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".mp4",
            ".webm",
            ".mov",
        }

        if extension in allowed:
            if extension == ".jpeg":
                return ".jpg"

            return extension

        if media_type == "video":
            return ".mp4"

        return ".jpg"

    # =========================================================
    # DOWNLOAD
    # =========================================================

    async def download_media(
        self,
        url,
        media_type=None,
        directory=None,
        index=0,
    ):
        import aiohttp

        if not directory:
            raise RuntimeError(
                "Не указан временный каталог для media."
            )

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        ) as session:

            async with session.get(
                url,
                allow_redirects=True,
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        f"Media HTTP {response.status}"
                    )

                data = await response.read()

                if not data:
                    raise RuntimeError(
                        "Пустой media response."
                    )

                content_type = response.headers.get(
                    "Content-Type",
                    "",
                )

                extension = (
                    self.extension_from_content_type(
                        content_type,
                        str(response.url),
                        media_type,
                    )
                )

                filename = (
                    f"media_{index}"
                    + extension
                )

                path = os.path.join(
                    directory,
                    filename,
                )

                with open(
                    path,
                    "wb",
                ) as file:
                    file.write(data)

                return path, extension

    # =========================================================
    # TELEGRAM
    # =========================================================

    async def send_post(self, tweet):
        raw_chat_id = str(
            self.config[
                "RepostsChat"
            ]
        ).strip()

        if not raw_chat_id:
            raise RuntimeError(
                "RepostsChat не указан."
            )

        try:
            chat_id = int(
                raw_chat_id
            )
        except ValueError:
            raise RuntimeError(
                "RepostsChat должен содержать числовой ID чата."
            )

        caption = self.make_caption(
            tweet
        )

        media = []

        if self.config[
            "DownloadMedia"
        ]:
            media = self.get_media(
                tweet
            )

        temp_dir = None

        downloaded = []

        try:
            if media:
                temp_dir = self.create_temp_dir()

            for index, (
                media_type,
                url,
            ) in enumerate(media):

                try:
                    path, extension = (
                        await self.download_media(
                            url,
                            media_type,
                            temp_dir,
                            index,
                        )
                    )

                    downloaded.append(
                        (
                            media_type,
                            path,
                            extension,
                        )
                    )

                except Exception:
                    self.errors += 1

            if not downloaded:
                if not self.config[
                    "SendTextWithoutMedia"
                ]:
                    return False

                await self.client.send_message(
                    chat_id,
                    caption or "Source",
                    parse_mode="html",
                )

                return True

            if len(downloaded) == 1:
                media_type, path, extension = (
                    downloaded[0]
                )

                await self.client.send_file(
                    chat_id,
                    path,
                    caption=caption,
                    parse_mode="html",
                    force_document=False,
                )

                return True

            for index, (
                media_type,
                path,
                extension,
            ) in enumerate(downloaded):

                await self.client.send_file(
                    chat_id,
                    path,
                    caption=(
                        caption
                        if index == 0
                        else None
                    ),
                    parse_mode=(
                        "html"
                        if index == 0
                        else None
                    ),
                    force_document=False,
                )

            return True

        finally:
            self.cleanup_temp_dir(
                temp_dir
            )

    # =========================================================
    # CHECK
    # =========================================================

    async def check(self):
        async with self.check_lock:

            posts = await self.get_posts()

            if not posts:
                return {
                    "total": 0,
                    "found": 0,
                    "sent": 0,
                    "base": False,
                }

            reposts = {}

            for post in posts:

                if not isinstance(
                    post,
                    dict,
                ):
                    continue

                if not post.get(
                    "isRetweet",
                    False,
                ):
                    continue

                post_id = post.get(
                    "id"
                )

                if not post_id:
                    continue

                post_id = str(
                    post_id
                )

                # =============================================
                # Создаём fingerprint поста
                # =============================================

                author = post.get(
                    "author",
                    {},
                )

                if not isinstance(
                    author,
                    dict,
                ):
                    author = {}

                author_id = str(
                    author.get(
                        "id",
                        "",
                    )
                )

                created_at = str(
                    post.get(
                        "createdAtISO",
                        post.get(
                            "createdAt",
                            "",
                        ),
                    )
                )

                text = str(
                    post.get(
                        "text",
                        "",
                    )
                )

                media = post.get(
                    "media",
                    [],
                )

                media_urls = []

                if isinstance(
                    media,
                    list,
                ):
                    for item in media:

                        if not isinstance(
                            item,
                            dict,
                        ):
                            continue

                        url = item.get(
                            "url"
                        )

                        if url:
                            media_urls.append(
                                str(url)
                            )

                fingerprint_source = (
                    author_id
                    + "|"
                    + created_at
                    + "|"
                    + text
                    + "|"
                    + "|".join(
                        media_urls
                    )
                )

                fingerprint = (
                    "fp:"
                    + hashlib.sha256(
                        fingerprint_source.encode(
                            "utf-8"
                        )
                    ).hexdigest()
                )

                reposts[
                    post_id
                ] = {
                    "post": post,
                    "fingerprint": fingerprint,
                }

            current = set(
                reposts.keys()
            )

            seen = self.get_seen()

            seen_fingerprints = {
                str(value)
                for value in seen
                if str(value).startswith(
                    "fp:"
                )
            }

            # =============================================
            # ПЕРВЫЙ ЗАПУСК
            # =============================================

            if not self.is_initialized():

                baseline = set()

                for post_id in current:

                    baseline.add(
                        post_id
                    )

                    baseline.add(
                        reposts[
                            post_id
                        ]["fingerprint"]
                    )

                self.save_seen(
                    baseline
                )

                self.set_initialized(
                    True
                )

                self.checked += len(
                    current
                )

                return {
                    "total": len(posts),
                    "found": 0,
                    "sent": 0,
                    "base": True,
                }

            # =============================================
            # ПОИСК НОВЫХ
            # =============================================

            new_ids = []

            for post_id in current:

                # Уже видели этот ID.
                if post_id in seen:
                    continue

                fingerprint = reposts[
                    post_id
                ]["fingerprint"]

                # Уже видели точно такой же пост,
                # даже если X/twitter-cli дал ему другой ID.
                if fingerprint in seen_fingerprints:
                    continue

                new_ids.append(
                    post_id
                )

            new_ids.reverse()

            # =============================================
            # ОТПРАВКА
            # =============================================

            sent = 0

            successfully_processed = set()

            for post_id in new_ids:

                self.checked += 1

                try:
                    delay = self.get_delay()

                    if delay > 0:
                        await asyncio.sleep(
                            delay
                        )

                    ok = await self.send_post(
                        reposts[
                            post_id
                        ]["post"]
                    )

                    if ok:
                        sent += 1
                        self.published += 1

                        # Сохраняем и ID,
                        # и fingerprint.
                        successfully_processed.add(
                            post_id
                        )

                        successfully_processed.add(
                            reposts[
                                post_id
                            ]["fingerprint"]
                        )

                except Exception:
                    self.errors += 1

                await asyncio.sleep(
                    0.5
                )

            # =============================================
            # СОХРАНЕНИЕ ИСТОРИИ
            # =============================================

            self.save_seen(
                seen
                | successfully_processed
            )

            return {
                "total": len(posts),
                "found": len(new_ids),
                "sent": sent,
                "base": False,
            }

    # =========================================================
    # AUTO LOOP
    # =========================================================

    async def auto_loop(self):

        while self.running:

            try:
                await self.check()

            except asyncio.CancelledError:
                break

            except Exception:
                self.errors += 1

            try:
                await asyncio.sleep(
                    max(
                        30,
                        int(
                            self.config[
                                "CheckInterval"
                            ]
                        ),
                    )
                )

            except asyncio.CancelledError:
                break

    async def start_loop(self):

        if self.running:
            return False

        self.running = True

        self.task = asyncio.create_task(
            self.auto_loop()
        )

        return True

    async def stop_loop(self):

        self.running = False

        task = self.task
        self.task = None

        if task:
            task.cancel()

            try:
                await task

            except asyncio.CancelledError:
                pass

            except Exception:
                pass

        self.cleanup_temp_root()

        return True

    # =========================================================
    # COMMAND: XActions
    # =========================================================

    @loader.command(
        ru_doc="— информация о модуле"
    )
    async def xactions(self, message):
        """— информация"""

        await utils.answer(
            message,
            self.strings[
                "info"
            ],
        )

    # =========================================================
    # COMMAND: XCHECK
    # =========================================================

    @loader.command(
        ru_doc="— проверить X репосты"
    )
    async def xcheck(self, message):
        """— проверить X репосты"""

        await utils.answer(
            message,
            self.strings[
                "checking"
            ],
        )

        try:

            result = await self.check()

            if result["base"]:

                await utils.answer(
                    message,
                    self.strings[
                        "base_created"
                    ].format(
                        result["total"]
                    ),
                )

                return

            if result["found"] == 0:

                await utils.answer(
                    message,
                    self.strings[
                        "no_new"
                    ],
                )

                return

            await utils.answer(
                message,
                self.strings[
                    "found"
                ].format(
                    result["found"]
                )
                + "\n"
                + self.strings[
                    "sent"
                ].format(
                    result["sent"]
                ),
            )

        except Exception as e:

            await utils.answer(
                message,
                self.strings[
                    "error"
                ].format(
                    self.hide_secrets(
                        f"{type(e).__name__}: {e}"
                    )
                ),
            )

    # =========================================================
    # COMMAND: XLOGIN
    # =========================================================

    @loader.command(
        ru_doc="— проверить X и авторизацию"
    )
    async def xlogin(self, message):
        """— проверить X"""

        try:

            posts = await self.get_posts()

            await utils.answer(
                message,
                self.strings[
                    "x_ok"
                ].format(
                    len(posts)
                ),
            )

        except Exception as e:

            await utils.answer(
                message,
                self.strings[
                    "error"
                ].format(
                    self.hide_secrets(
                        f"{type(e).__name__}: {e}"
                    )
                ),
            )

    # =========================================================
    # COMMAND: XRESET
    # =========================================================

    @loader.command(
        ru_doc="— сбросить историю"
    )
    async def xreset(self, message):
        """— сбросить историю"""

        async with self.check_lock:

            self.db.set(
                self.name,
                "seen",
                [],
            )

            self.db.set(
                self.name,
                "initialized",
                False,
            )

        await utils.answer(
            message,
            self.strings[
                "reset"
            ],
        )

    # =========================================================
    # COMMAND: XSTART
    # =========================================================

    @loader.command(
        ru_doc="— запустить автопроверку"
    )
    async def xstart(self, message):
        """— запустить автопроверку"""

        if self.running:

            await utils.answer(
                message,
                self.strings[
                    "already_started"
                ],
            )

            return

        if not self.is_initialized():

            try:

                result = await self.check()

                if result["base"]:
                    pass

            except Exception as e:

                await utils.answer(
                    message,
                    self.strings[
                        "error"
                    ].format(
                        self.hide_secrets(
                            f"{type(e).__name__}: {e}"
                        )
                    ),
                )

                return

        interval = max(
            30,
            int(
                self.config[
                    "CheckInterval"
                ]
            ),
        )

        delay = self.get_delay()

        await self.start_loop()

        await utils.answer(
            message,
            self.strings[
                "started"
            ].format(
                interval,
                delay,
            ),
        )

    # =========================================================
    # COMMAND: XSTOP
    # =========================================================

    @loader.command(
        ru_doc="— остановить автопроверку"
    )
    async def xstop(self, message):
        """— остановить автопроверку"""

        if not self.running:

            await utils.answer(
                message,
                self.strings[
                    "not_started"
                ],
            )

            return

        await self.stop_loop()

        await utils.answer(
            message,
            self.strings[
                "stopped"
            ],
        )

    # =========================================================
    # COMMAND: XSTATS
    # =========================================================

    @loader.command(
        ru_doc="— статистика"
    )
    async def xstats(self, message):
        """— статистика"""

        await utils.answer(
            message,
            self.strings[
                "stats"
            ].format(
                self.checked,
                self.published,
                self.errors,
                "ДА"
                if self.running
                else "НЕТ",
                max(
                    30,
                    int(
                        self.config[
                            "CheckInterval"
                        ]
                    ),
                ),
                self.get_delay(),
            ),
        )

    # =========================================================
    # COMMAND: XTEST
    # =========================================================

    @loader.command(
        ru_doc="— проверить Telegram-чат"
    )
    async def xtest(self, message):
        """— проверить чат отправки"""

        raw_chat_id = str(
            self.config[
                "RepostsChat"
            ]
        ).strip()

        if not raw_chat_id:

            await utils.answer(
                message,
                "❌ <b>RepostsChat не указан.</b>",
            )

            return

        try:

            chat_id = int(
                raw_chat_id
            )

            await self.client.send_message(
                chat_id,
                "🧪 <b>XActions</b>\n"
                "Telegram connection OK.",
                parse_mode="html",
            )

            await utils.answer(
                message,
                self.strings[
                    "test_ok"
                ],
            )

        except Exception as e:

            await utils.answer(
                message,
                self.strings[
                    "error"
                ].format(
                    self.hide_secrets(
                        f"{type(e).__name__}: {e}"
                    )
                ),
            )