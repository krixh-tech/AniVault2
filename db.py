import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, AUTO_DELETE_DEFAULT

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = None
        self.db     = None

    async def connect(self):
        if not MONGO_URI:
            logger.warning("No MONGO_URI set – running without persistence.")
            return
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db     = self.client[DB_NAME]
        # Ensure indexes
        await self.db.users.create_index("user_id", unique=True)
        await self.db.tracked.create_index([("user_id", 1), ("anime_id", 1)], unique=True)
        logger.info("✅ MongoDB connected.")

    async def close(self):
        if self.client:
            self.client.close()

    def _ok(self):
        return self.db is not None

    # ── Users ─────────────────────────────────────────────────────────────────
    async def add_user(self, user_id: int, name: str = "", username: str = ""):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "name": name,
                "username": username,
                "banned": False,
                "is_admin": False,
                "auto_del": AUTO_DELETE_DEFAULT,
                "downloads": 0,
            }},
            upsert=True,
        )

    async def get_user(self, user_id: int):
        if not self._ok():
            return None
        return await self.db.users.find_one({"user_id": user_id})

    async def get_all_user_ids(self) -> list[int]:
        if not self._ok():
            return []
        cursor = self.db.users.find({}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor]

    async def total_users(self) -> int:
        if not self._ok():
            return 0
        return await self.db.users.count_documents({})

    async def is_banned(self, user_id: int) -> bool:
        doc = await self.get_user(user_id)
        return doc.get("banned", False) if doc else False

    async def ban_user(self, user_id: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"banned": True}}, upsert=True
        )

    async def unban_user(self, user_id: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"banned": False}}
        )

    async def is_admin(self, user_id: int) -> bool:
        doc = await self.get_user(user_id)
        return doc.get("is_admin", False) if doc else False

    async def add_admin(self, user_id: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"is_admin": True}}, upsert=True
        )

    async def remove_admin(self, user_id: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"is_admin": False}}
        )

    async def get_all_admins(self) -> list[int]:
        if not self._ok():
            return []
        cursor = self.db.users.find({"is_admin": True}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor]

    async def set_auto_del(self, user_id: int, seconds: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"auto_del": seconds}}, upsert=True
        )

    async def get_auto_del(self, user_id: int) -> int:
        doc = await self.get_user(user_id)
        return doc.get("auto_del", AUTO_DELETE_DEFAULT) if doc else AUTO_DELETE_DEFAULT

    async def increment_downloads(self, user_id: int):
        if not self._ok():
            return
        await self.db.users.update_one(
            {"user_id": user_id}, {"$inc": {"downloads": 1}}
        )

    async def total_downloads(self) -> int:
        if not self._ok():
            return 0
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$downloads"}}}]
        result = await self.db.users.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0

    # ── Tracking ──────────────────────────────────────────────────────────────
    async def track_anime(self, user_id: int, anime_id: str, anime_name: str):
        if not self._ok():
            return
        await self.db.tracked.update_one(
            {"user_id": user_id, "anime_id": anime_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "anime_id": anime_id,
                "anime_name": anime_name,
                "last_ep": 0,
            }},
            upsert=True,
        )

    async def untrack_anime(self, user_id: int, anime_id: str):
        if not self._ok():
            return
        await self.db.tracked.delete_one({"user_id": user_id, "anime_id": anime_id})

    async def get_tracked(self, user_id: int) -> list:
        if not self._ok():
            return []
        cursor = self.db.tracked.find({"user_id": user_id})
        return await cursor.to_list(None)

    async def get_all_tracked(self) -> list:
        if not self._ok():
            return []
        cursor = self.db.tracked.find({})
        return await cursor.to_list(None)

    async def update_last_ep(self, user_id: int, anime_id: str, ep: int):
        if not self._ok():
            return
        await self.db.tracked.update_one(
            {"user_id": user_id, "anime_id": anime_id},
            {"$set": {"last_ep": ep}},
        )

    # ── Settings (global) ─────────────────────────────────────────────────────
    async def get_setting(self, key: str, default=None):
        if not self._ok():
            return default
        doc = await self.db.settings.find_one({"key": key})
        return doc["value"] if doc else default

    async def set_setting(self, key: str, value):
        if not self._ok():
            return
        await self.db.settings.update_one(
            {"key": key}, {"$set": {"value": value}}, upsert=True
        )


# Global singleton
_db_instance = Database()


def get_db() -> Database:
    return _db_instance
